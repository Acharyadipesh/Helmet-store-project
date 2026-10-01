from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Avg
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import Helmet, Category, Brand, Cart, CartItem, Review, WishlistItem, CompareItem
from .forms import ReviewForm
from orders.models import Order, OrderItem


def is_ajax(request):
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest'


def get_cart(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    return cart


def home(request):
    featured = Helmet.objects.filter(is_featured=True, is_available=True)[:8]
    new_arrivals = Helmet.objects.filter(is_available=True).order_by('-created_at')[:8]
    categories = Category.objects.all()
    brands = Brand.objects.all()

    recent_reviews = Review.objects.select_related(
        'user', 'helmet', 'helmet__brand'
    ).order_by('-created_at')[:6]

    wishlist_ids = set()
    if request.user.is_authenticated:
        wishlist_ids = set(
            WishlistItem.objects.filter(user=request.user).values_list('helmet_id', flat=True)
        )

    context = {
        'featured': featured,
        'new_arrivals': new_arrivals,
        'categories': categories,
        'brands': brands,
        'recent_reviews': recent_reviews,
        'wishlist_ids': wishlist_ids,
    }
    return render(request, 'store/home.html', context)


def helmet_list(request):
    helmets = Helmet.objects.filter(is_available=True)
    category_slug = request.GET.get('category')
    brand_slug = request.GET.get('brand')
    helmet_type = request.GET.get('type')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    size = request.GET.get('size')
    search = request.GET.get('q')
    sort = request.GET.get('sort', '-created_at')

    if category_slug:
        helmets = helmets.filter(category__slug=category_slug)
    if brand_slug:
        helmets = helmets.filter(brand__slug=brand_slug)
    if helmet_type:
        helmets = helmets.filter(helmet_type=helmet_type)
    if min_price:
        helmets = helmets.filter(price__gte=min_price)
    if max_price:
        helmets = helmets.filter(price__lte=max_price)
    if size:
        helmets = helmets.filter(size=size)
    if search:
        helmets = helmets.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search) |
            Q(brand__name__icontains=search)
        )

    helmets = helmets.order_by(sort)
    paginator = Paginator(helmets, 12)
    page = request.GET.get('page')
    helmets = paginator.get_page(page)

    wishlist_ids = set()
    if request.user.is_authenticated:
        wishlist_ids = set(
            WishlistItem.objects.filter(user=request.user).values_list('helmet_id', flat=True)
        )

    context = {
        'helmets': helmets,
        'categories': Category.objects.all(),
        'brands': Brand.objects.all(),
        'sizes': Helmet.SIZES,
        'types': Helmet.HELMET_TYPES,
        'search_query': search or '',
        'wishlist_ids': wishlist_ids,
    }
    return render(request, 'store/helmet_list.html', context)


def helmet_detail(request, slug):
    helmet = get_object_or_404(Helmet, slug=slug, is_available=True)
    related = Helmet.objects.filter(
        category=helmet.category, is_available=True
    ).exclude(id=helmet.id)[:4]

    reviews = helmet.reviews.select_related('user', 'order').order_by('-created_at')
    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0

    # Only users with a DELIVERED order can review
    has_purchased = False
    if request.user.is_authenticated:
        has_purchased = OrderItem.objects.filter(
            order__user=request.user,
            helmet=helmet,
            order__status='delivered'
        ).exists()

    user_reviewed = False
    if request.user.is_authenticated:
        user_reviewed = Review.objects.filter(helmet=helmet, user=request.user).exists()

    in_wishlist = False
    if request.user.is_authenticated:
        in_wishlist = WishlistItem.objects.filter(user=request.user, helmet=helmet).exists()

    size_guide = {
        'XS': '53-54 cm', 'S': '55-56 cm', 'M': '57-58 cm',
        'L': '59-60 cm', 'XL': '61-62 cm', 'XXL': '63-64 cm',
    }

    context = {
        'helmet': helmet,
        'related': related,
        'reviews': reviews,
        'avg_rating': round(avg_rating, 1),
        'size_guide': size_guide,
        'has_purchased': has_purchased,
        'user_reviewed': user_reviewed,
        'in_wishlist': in_wishlist,
    }
    return render(request, 'store/helmet_detail.html', context)


# ==================== CART ====================
@login_required
@require_POST
def add_to_cart(request, helmet_id):
    helmet = get_object_or_404(Helmet, id=helmet_id)

    # ✅ Safety: block coming-soon items
    if helmet.is_coming_soon:
        return JsonResponse({
            'success': False,
            'message': f'"{helmet.name}" is not available yet. Coming soon!'
        })

    cart = get_cart(request)
    cart_item, created = CartItem.objects.get_or_create(cart=cart, helmet=helmet)

    if not created:
        if cart_item.quantity + 1 > helmet.stock:
            return JsonResponse({
                'success': False,
                'message': f'Sorry, only {helmet.stock} unit(s) of "{helmet.name}" are available.'
            })
        cart_item.quantity += 1
        cart_item.save()
    else:
        if helmet.stock < 1:
            cart_item.delete()
            return JsonResponse({
                'success': False,
                'message': f'"{helmet.name}" is currently out of stock.'
            })

    return JsonResponse({
        'success': True,
        'message': f'"{helmet.name}" added to cart!',
        'cart_count': cart.get_item_count(),
    })


@login_required
def cart_detail(request):
    cart = get_cart(request)
    return render(request, 'store/cart.html', {'cart': cart})


@login_required
@require_POST
def update_cart(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    quantity = int(request.POST.get('quantity', 1))
    cart = item.cart

    if quantity < 1:
        item.delete()
        if is_ajax(request):
            return JsonResponse({
                'success': True,
                'removed': True,
                'message': 'Item removed from cart.',
                'cart_count': cart.get_item_count(),
                'cart_total': str(cart.get_total()),
                'item_subtotal': None,
            })
        messages.info(request, 'Item removed from cart.')
        return redirect('store:cart_detail')

    if quantity > item.helmet.stock:
        if is_ajax(request):
            return JsonResponse({
                'success': False,
                'message': f'Only {item.helmet.stock} units available.',
            })
        messages.error(request, f'Only {item.helmet.stock} units available.')
        return redirect('store:cart_detail')

    item.quantity = quantity
    item.save()

    if is_ajax(request):
        return JsonResponse({
            'success': True,
            'removed': False,
            'message': 'Cart updated.',
            'cart_count': cart.get_item_count(),
            'cart_total': str(cart.get_total()),
            'item_subtotal': str(item.get_subtotal()),
        })
    return redirect('store:cart_detail')


@login_required
@require_POST
def remove_from_cart(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    cart = item.cart
    item.delete()

    if is_ajax(request):
        return JsonResponse({
            'success': True,
            'message': 'Item removed from cart.',
            'cart_count': cart.get_item_count(),
            'cart_total': str(cart.get_total()),
        })
    messages.info(request, 'Item removed from cart.')
    return redirect('store:cart_detail')


# ==================== WISHLIST ====================
@login_required
@require_POST
def add_to_wishlist(request, helmet_id):
    helmet = get_object_or_404(Helmet, id=helmet_id)
    item = WishlistItem.objects.filter(user=request.user, helmet=helmet).first()

    if item:
        item.delete()
        in_wishlist = False
        message = f'"{helmet.name}" removed from wishlist.'
    else:
        WishlistItem.objects.create(user=request.user, helmet=helmet)
        in_wishlist = True
        message = f'"{helmet.name}" added to wishlist!'

    wishlist_count = WishlistItem.objects.filter(user=request.user).count()

    if is_ajax(request):
        return JsonResponse({
            'success': True,
            'in_wishlist': in_wishlist,
            'message': message,
            'wishlist_count': wishlist_count,
        })
    messages.success(request, message)
    return redirect(request.META.get('HTTP_REFERER', 'store:home'))


@login_required
@require_POST
def remove_from_wishlist(request, helmet_id):
    WishlistItem.objects.filter(user=request.user, helmet_id=helmet_id).delete()
    if is_ajax(request):
        return JsonResponse({
            'success': True,
            'message': 'Removed from wishlist.',
            'wishlist_count': WishlistItem.objects.filter(user=request.user).count(),
        })
    return redirect('store:wishlist')


@login_required
def wishlist(request):
    items = WishlistItem.objects.filter(user=request.user).select_related(
        'helmet', 'helmet__brand'
    )
    return render(request, 'store/wishlist.html', {'items': items})


# ==================== COMPARE ====================
@require_POST
def add_to_compare(request, helmet_id):
    helmet = get_object_or_404(Helmet, id=helmet_id)
    session_id = request.session.session_key
    if not session_id:
        request.session.create()
        session_id = request.session.session_key

    item = CompareItem.objects.filter(session_id=session_id, helmet=helmet).first()

    if item:
        item.delete()
        in_compare = False
        message = f'"{helmet.name}" removed from comparison.'
    else:
        current_count = CompareItem.objects.filter(session_id=session_id).count()
        if current_count >= 3:
            if is_ajax(request):
                return JsonResponse({
                    'success': False,
                    'message': 'You can compare up to 3 helmets only.',
                })
            messages.warning(request, 'You can only compare up to 3 helmets.')
            return redirect(request.META.get('HTTP_REFERER', 'store:home'))
        CompareItem.objects.create(session_id=session_id, helmet=helmet)
        in_compare = True
        message = f'"{helmet.name}" added to comparison.'

    compare_count = CompareItem.objects.filter(session_id=session_id).count()

    if is_ajax(request):
        return JsonResponse({
            'success': True,
            'in_compare': in_compare,
            'message': message,
            'compare_count': compare_count,
        })
    messages.success(request, message)
    return redirect(request.META.get('HTTP_REFERER', 'store:home'))


@require_POST
def remove_from_compare(request, helmet_id):
    session_id = request.session.session_key
    if session_id:
        CompareItem.objects.filter(session_id=session_id, helmet_id=helmet_id).delete()
    if is_ajax(request):
        return JsonResponse({
            'success': True,
            'message': 'Removed from comparison.',
            'compare_count': CompareItem.objects.filter(session_id=session_id).count() if session_id else 0,
        })
    return redirect('store:compare_list')


def compare_list(request):
    session_id = request.session.session_key
    helmets = []
    if session_id:
        items = CompareItem.objects.filter(
            session_id=session_id
        ).select_related('helmet', 'helmet__brand')[:3]
        helmets = [item.helmet for item in items]
    return render(request, 'store/compare.html', {'helmets': helmets})


# ==================== REVIEWS ====================
@login_required
def add_review(request, helmet_id):
    helmet = get_object_or_404(Helmet, id=helmet_id)

    purchased_item = OrderItem.objects.filter(
        order__user=request.user,
        helmet=helmet,
        order__status='delivered'
    ).select_related('order').first()

    if not purchased_item:
        messages.error(request, 'You can only review helmets after your order has been delivered!')
        return redirect('store:helmet_detail', slug=helmet.slug)

    if Review.objects.filter(helmet=helmet, user=request.user).exists():
        messages.warning(request, 'You have already reviewed this helmet!')
        return redirect('store:helmet_detail', slug=helmet.slug)

    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.user = request.user
            review.helmet = helmet
            review.order = purchased_item.order
            review.is_verified_purchase = True
            review.save()
            messages.success(request, 'Review submitted! Thank you.')
    return redirect('store:helmet_detail', slug=helmet.slug)


@login_required
def write_review_view(request, item_id):
    order_item = get_object_or_404(
        OrderItem, id=item_id, order__user=request.user
    )
    order = order_item.order
    helmet = order_item.helmet

    if order.status != 'delivered':
        messages.error(
            request,
            'You can only review after your order has been delivered.'
        )
        return redirect('orders:order_detail', order_id=order.order_id)

    existing = Review.objects.filter(helmet=helmet, user=request.user).first()
    if existing:
        messages.info(request, 'You have already reviewed this helmet.')
        return redirect('store:helmet_detail', slug=helmet.slug)

    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.user = request.user
            review.helmet = helmet
            review.order = order
            review.is_verified_purchase = True
            review.save()
            messages.success(request, 'Thank you! Your review has been posted.')
            return redirect('store:helmet_detail', slug=helmet.slug)
    else:
        form = ReviewForm()

    return render(request, 'store/write_review.html', {
        'form': form,
        'order': order,
        'order_item': order_item,
        'helmet': helmet,
    })


@login_required
def delete_review_view(request, review_id):
    review = get_object_or_404(Review, id=review_id, user=request.user)
    slug = review.helmet.slug
    if request.method == 'POST':
        review.delete()
        messages.success(request, 'Your review has been deleted.')
    return redirect('store:helmet_detail', slug=slug)


def size_finder(request):
    result = None
    if request.method == 'POST':
        circumference = float(request.POST.get('circumference', 0))
        riding_style = request.POST.get('riding_style')

        if circumference < 54:
            size = 'XS'
        elif circumference < 56:
            size = 'S'
        elif circumference < 58:
            size = 'M'
        elif circumference < 60:
            size = 'L'
        elif circumference < 62:
            size = 'XL'
        else:
            size = 'XXL'

        type_map = {
            'commute': ('open_face', 'Open Face - Best visibility for city riding'),
            'sport': ('full_face', 'Full Face - Maximum protection at high speeds'),
            'touring': ('modular', 'Modular - Versatile for long rides'),
            'offroad': ('off_road', 'Off-Road - Lightweight with peak visor'),
            'adventure': ('dual_sport', 'Dual Sport - Best of both worlds'),
        }

        helmet_type, description = type_map.get(riding_style, ('full_face', 'Full Face'))

        result = {
            'size': size,
            'helmet_type': helmet_type,
            'description': description,
            'circumference': circumference,
        }

    return render(request, 'store/size_finder.html', {
        'result': result,
        'types': Helmet.HELMET_TYPES
    })