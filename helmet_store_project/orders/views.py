import json
import requests
import base64
import hmac
import hashlib
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.crypto import get_random_string
from django.conf import settings
from store.models import Cart
from .models import Order, OrderItem


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
        
        for item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                helmet=item.helmet,
                quantity=item.quantity,
                price=item.helmet.get_price(),
            )
            item.helmet.stock -= item.quantity
            item.helmet.save()
        
        cart.items.all().delete()
        
        if payment_method == 'cod':
            messages.success(request, f'Order placed! Pay NRs {order.total_amount} on delivery. Order ID: {order.order_id}')
            return redirect('orders:order_detail', order_id=order.order_id)
        else:
            return redirect('orders:initiate_payment', order_id=order.order_id)
    
    return render(request, 'orders/checkout.html', {'cart': cart})


@login_required
def order_detail_view(request, order_id):
    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    return render(request, 'orders/order_detail.html', {'order': order})


# ---------- PAYMENT INITIATION ----------
@login_required
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


# ---------- ESEWA (FORM METHOD - MOST RELIABLE) ----------
def initiate_esewa_payment_form(request, order):
    """
    Uses eSewa's traditional Form POST method.
    Generates HMAC signature and renders a form that auto-submits.
    """
    esewa_url = "https://rc-epay.esewa.com.np/api/epay/main/v2/form"
    
    total_amount = str(order.total_amount)
    tax_amount = "0.00"
    product_service_charge = "0.00"
    product_delivery_charge = "0.00"
    product_code = settings.ESEWA_MERCHANT_CODE
    transaction_uuid = order.order_id
    secret_key = settings.ESEWA_SECRET_KEY

    # ✅ Generate HMAC Signature
    signed_field_names = "total_amount,transaction_uuid,product_code"
    message = f"total_amount={total_amount},transaction_uuid={transaction_uuid},product_code={product_code}"
    
    signature = base64.b64encode(
        hmac.new(
            secret_key.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).digest()
    ).decode('utf-8')

    # ✅ Pass all data to the template
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
    
    decoded_data = base64.b64decode(encoded_data).decode('utf-8')
    data = json.loads(decoded_data)
    
    transaction_uuid = data.get('transaction_uuid')
    status = data.get('status')
    total_amount = data.get('total_amount')
    signature_from_esewa = data.get('signature')
    
    secret_key = settings.ESEWA_SECRET_KEY
    message = f"transaction_uuid={transaction_uuid},status={status},total_amount={total_amount}"
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
            order = Order.objects.get(order_id=transaction_uuid)
            order.is_paid = True
            order.status = 'processing'
            order.save()
            messages.success(request, f'Payment successful! Order #{order.order_id} is confirmed.')
        except Order.DoesNotExist:
            messages.error(request, 'Order not found.')
    else:
        messages.error(request, f'Payment failed. Status: {status}')
    
    return redirect('orders:order_detail', order_id=transaction_uuid)


# ---------- KHALTI ----------
def initiate_khalti_payment(request, order):
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
        "Authorization": f"Key {settings.KHALTI_SECRET_KEY}",
        "Content-Type": "application/json",
    }
    
    try:
        response = requests.post(
            settings.KHALTI_INITIATE_URL,
            data=json.dumps(payload),
            headers=headers
        )
        response_data = response.json()
        
        if response.status_code == 200 and 'payment_url' in response_data:
            return redirect(response_data['payment_url'])
        else:
            messages.error(request, f'Khalti initiation failed: {response_data.get("detail", "Unknown error")}')
            return redirect('orders:order_detail', order_id=order.order_id)
    except Exception as e:
        messages.error(request, f'Khalti error: {str(e)}')
        return redirect('orders:order_detail', order_id=order.order_id)


@login_required
def khalti_callback_view(request):
    pidx = request.GET.get('pidx')
    purchase_order_id = request.GET.get('purchase_order_id')
    status = request.GET.get('status')
    
    if status == 'Completed':
        headers = {"Authorization": f"Key {settings.KHALTI_SECRET_KEY}"}
        data = {"pidx": pidx}
        verify_url = "https://a.khalti.com/api/v2/epayment/lookup/"
        
        try:
            response = requests.post(verify_url, json=data, headers=headers)
            result = response.json()
            
            if result.get('status') == 'Completed':
                order = get_object_or_404(Order, order_id=purchase_order_id)
                order.is_paid = True
                order.status = 'processing'
                order.save()
                messages.success(request, f'Khalti payment successful! Order #{order.order_id} is confirmed.')
            else:
                messages.error(request, 'Khalti verification failed: Payment not completed.')
        except Exception as e:
            messages.error(request, f'Khalti verification error: {str(e)}')
    else:
        messages.error(request, f'Khalti payment was not completed. Status: {status}')
    
    return redirect('orders:order_detail', order_id=purchase_order_id)