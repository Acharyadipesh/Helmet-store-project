import json
import requests
import base64
import hmac
import hashlib
import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.crypto import get_random_string
from django.conf import settings
from django.db import transaction, IntegrityError
from django.views.decorators.cache import never_cache
from store.models import Cart
from .models import Order, OrderItem


# ==================== CHECKOUT ====================
@login_required
def checkout_view(request):
    try:
        cart = Cart.objects.get(user=request.user)
    except Cart.DoesNotExist:
        messages.error(request, 'Your cart is empty.')
        return redirect('store:cart_detail')

    if not cart.items.exists():
        messages.error(request, 'Your cart is empty.')
        return redirect('store:cart_detail')

    if request.method == 'POST':
        payment_method = request.POST.get('payment_method', 'cod')

        try:
            with transaction.atomic():
                # ✅ Re-fetch items with select_for_update to prevent race conditions
                cart_items = list(
                    cart.items.select_related('helmet').select_for_update()
                )

                # ✅ Step 1: Validate stock for ALL items
                for item in cart_items:
                    if item.quantity > item.helmet.stock:
                        messages.error(
                            request,
                            f'Sorry, only {item.helmet.stock} unit(s) of "{item.helmet.name}" are available.'
                        )
                        return redirect('store:cart_detail')

                # ✅ Step 2: Create the order
                order = Order.objects.create(
                    user=request.user,
                    order_id=get_random_string(10).upper(),
                    payment_method=payment_method,
                    full_name=request.POST.get('full_name'),
                    email=request.POST.get('email'),
                    phone=request.POST.get('phone'),
                    address=request.POST.get('address'),
                    city=request.POST.get('city'),
                    province=request.POST.get('province'),
                    total_amount=cart.get_total(),
                )

                # ✅ Step 3: Create order items AND reduce stock
                #    This runs for COD and online payments the SAME way.
                for item in cart_items:
                    OrderItem.objects.create(
                        order=order,
                        helmet=item.helmet,
                        quantity=item.quantity,
                        price=item.helmet.get_price(),
                    )

                    # Reduce stock
                    helmet = item.helmet
                    old_stock = helmet.stock
                    helmet.stock = old_stock - item.quantity
                    helmet.save(update_fields=['stock'])

                    # 🔍 DEBUG: See this in the terminal
                    print(f"\n🛒 STOCK UPDATE | {helmet.name}")
                    print(f"   Before: {old_stock} → After: {helmet.stock} (qty: {item.quantity})")
                    print(f"   Payment: {payment_method}\n")

                # ✅ Step 4: Clear the cart
                cart.items.all().delete()

        except IntegrityError as e:
            print(f"❌ IntegrityError during checkout: {e}")
            messages.error(request, 'Stock error occurred. Please try again.')
            return redirect('store:cart_detail')

        # ==================== ROUTE BY PAYMENT METHOD ====================
        if payment_method == 'cod':
            messages.success(
                request,
                f'Order placed! Pay NRs {order.total_amount} on delivery. Order ID: {order.order_id}'
            )
            return redirect('orders:order_detail', order_id=order.order_id)
        else:
            return redirect('orders:initiate_payment', order_id=order.order_id)

    return render(request, 'orders/checkout.html', {'cart': cart})


# ==================== ORDER DETAIL ====================
@login_required
def order_detail_view(request, order_id):
    order = get_object_or_404(Order, order_id=order_id, user=request.user)

    reviewed_helmet_ids = set(
        order.reviews.values_list('helmet_id', flat=True)
    )

    return render(request, 'orders/order_detail.html', {
        'order': order,
        'reviewed_helmet_ids': reviewed_helmet_ids,
    })


# ==================== PAYMENT ROUTER ====================
@login_required
@never_cache
def initiate_payment_view(request, order_id):
    order = get_object_or_404(Order, order_id=order_id, user=request.user)

    if order.is_paid:
        messages.warning(request, 'This order is already paid.')
        return redirect('orders:order_detail', order_id=order.order_id)

    if order.payment_method == 'esewa':
        return initiate_esewa_payment_form(request, order)
    elif order.payment_method == 'khalti':
        return initiate_khalti_payment(request, order)
    else:
        messages.error(request, 'Invalid payment method selected.')
        return redirect('orders:order_detail', order_id=order.order_id)


# ==================== KHALTI ====================
def initiate_khalti_payment(request, order):
    secret_key = settings.KHALTI_SECRET_KEY.strip()
    amount_in_paisa = int(float(order.total_amount) * 100)

    payload = {
        "return_url": settings.KHALTI_RETURN_URL,
        "website_url": settings.KHALTI_WEBSITE_URL,
        "amount": amount_in_paisa,
        "purchase_order_id": order.order_id,
        "purchase_order_name": f"Order {order.order_id}",
        "customer_info": {
            "name": order.full_name,
            "email": order.email,
            "phone": order.phone
        }
    }

    headers = {
        "Authorization": f"Key {secret_key}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            settings.KHALTI_INITIATE_URL,
            json=payload,
            headers=headers,
            timeout=30
        )
        response_data = response.json()

        print("\n" + "=" * 60)
        print("📍 KHALTI INITIATE RESPONSE")
        print("Status Code:", response.status_code)
        print("Full Response:", json.dumps(response_data, indent=2))
        print("=" * 60 + "\n")

        if response.status_code == 200 and 'payment_url' in response_data:
            return redirect(response_data['payment_url'])
        else:
            error_msg = response_data.get('detail') or response_data.get('error_message') or str(response_data)
            messages.error(request, f'Khalti initiation failed: {error_msg}')
            return redirect('orders:order_detail', order_id=order.order_id)

    except requests.exceptions.RequestException as e:
        messages.error(request, f'Network error: {str(e)}')
        return redirect('orders:order_detail', order_id=order.order_id)


@login_required
def khalti_callback_view(request):
    pidx = request.GET.get('pidx')
    purchase_order_id = request.GET.get('purchase_order_id')
    status = request.GET.get('status')

    if status == 'Completed' and pidx and purchase_order_id:
        secret_key = settings.KHALTI_SECRET_KEY.strip()
        headers = {
            "Authorization": f"Key {secret_key}",
            "Content-Type": "application/json",
        }
        data = {"pidx": pidx}

        try:
            response = requests.post(
                settings.KHALTI_LOOKUP_URL,
                json=data,
                headers=headers,
                timeout=30
            )
            result = response.json()

            print("\n" + "=" * 60)
            print("📍 KHALTI LOOKUP RESPONSE")
            print("Status Code:", response.status_code)
            print("Full Response:", json.dumps(result, indent=2))
            print("=" * 60 + "\n")

            if result.get('status') == 'Completed':
                order = get_object_or_404(Order, order_id=purchase_order_id)
                order.is_paid = True
                order.status = 'paid'
                order.save()
                messages.success(request, f'Khalti payment successful! Order #{order.order_id} is confirmed.')
            else:
                messages.error(request, f'Khalti verification failed: {result.get("status", "Unknown error")}')
        except Exception as e:
            messages.error(request, f'Khalti verification error: {str(e)}')
    else:
        messages.error(request, f'Khalti payment was not completed. Status: {status}')

    return redirect('orders:order_detail', order_id=purchase_order_id)


# ==================== ESEWA ====================
def initiate_esewa_payment_form(request, order):
    esewa_url = "https://rc-epay.esewa.com.np/api/epay/main/v2/form"

    # ✅ Strip whitespace from env values (trailing \n breaks the signature)
    product_code = settings.ESEWA_MERCHANT_CODE.strip()
    secret_key = settings.ESEWA_SECRET_KEY.strip()

    # ✅ Force 2-decimal format to match eSewa's expected format exactly
    total_amount = f"{float(order.total_amount):.2f}"
    tax_amount = "0.00"
    product_service_charge = "0.00"
    product_delivery_charge = "0.00"

    # ✅ CRITICAL: Unique transaction UUID for EVERY attempt.
    #    Using order.order_id alone caused the "Duplicate transaction UUID" error.
    transaction_uuid = f"{order.order_id}_{uuid.uuid4().hex[:10]}"

    signed_field_names = "total_amount,transaction_uuid,product_code"
    message = (
        f"total_amount={total_amount},"
        f"transaction_uuid={transaction_uuid},"
        f"product_code={product_code}"
    )

    signature = base64.b64encode(
        hmac.new(
            secret_key.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).digest()
    ).decode('utf-8')

    print("\n" + "=" * 60)
    print("📍 ESEWA INITIATE")
    print(f"   Order ID:         {order.order_id}")
    print(f"   Transaction UUID: {transaction_uuid}")
    print(f"   Total Amount:     {total_amount!r}")
    print(f"   Product Code:     {product_code!r}")
    print(f"   Secret Key:       {secret_key!r}")
    print(f"   Signature:        {signature}")
    print("=" * 60 + "\n")

    context = {
        'esewa_url': esewa_url,
        'amount': total_amount,
        'tax_amount': tax_amount,
        'total_amount': total_amount,
        'product_service_charge': product_service_charge,
        'product_delivery_charge': product_delivery_charge,
        'product_code': product_code,
        'transaction_uuid': transaction_uuid,
        'success_url': settings.ESEWA_SUCCESS_URL,
        'failure_url': settings.ESEWA_FAILURE_URL,
        'signed_field_names': signed_field_names,
        'signature': signature,
        'order': order,
    }
    return render(request, 'orders/esewa_form.html', context)


@login_required
def esewa_callback_view(request):
    encoded_data = request.GET.get('data')
    if not encoded_data:
        messages.error(request, 'Invalid eSewa response.')
        return redirect('store:home')

    try:
        decoded_data = base64.b64decode(encoded_data).decode('utf-8')
        data = json.loads(decoded_data)
    except Exception as e:
        messages.error(request, f'Error parsing eSewa response: {str(e)}')
        return redirect('store:home')

    transaction_uuid = data.get('transaction_uuid', '')
    status = data.get('status')
    signature_from_esewa = data.get('signature')
    signed_field_names = data.get('signed_field_names', '')

    # ✅ Extract original order ID (strip "_hexsuffix")
    order_id = transaction_uuid.split('_')[0] if '_' in transaction_uuid else transaction_uuid

    secret_key = settings.ESEWA_SECRET_KEY.strip()
    field_names = signed_field_names.split(',')
    message_parts = []
    for field in field_names:
        if field in data:
            message_parts.append(f"{field}={data[field]}")
    message = ",".join(message_parts)

    print("\n" + "=" * 60)
    print("📍 ESEWA VERIFICATION")
    print("Transaction UUID:", transaction_uuid)
    print("Extracted Order ID:", order_id)
    print("Signed field names:", signed_field_names)
    print("Message being signed:", message)
    print("=" * 60 + "\n")

    computed_signature = base64.b64encode(
        hmac.new(
            secret_key.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).digest()
    ).decode('utf-8')

    if computed_signature != signature_from_esewa:
        messages.error(request, 'Payment verification failed: Invalid signature.')
        return redirect('store:home')

    if status == 'COMPLETE':
        try:
            order = Order.objects.get(order_id=order_id)
            order.is_paid = True
            order.status = 'paid'
            order.save()
            messages.success(request, f'Payment successful! Order #{order.order_id} is confirmed.')
        except Order.DoesNotExist:
            messages.error(request, 'Order not found.')
    else:
        messages.error(request, f'Payment failed. Status: {status}')

    return redirect('orders:order_detail', order_id=order_id)


@login_required
def esewa_failure_view(request):
    """Handle eSewa failure redirect (eSewa sends NO data param here)."""
    messages.error(request, 'eSewa payment was cancelled or failed. Please try again.')
    return redirect('store:cart_detail')