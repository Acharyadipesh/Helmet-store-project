from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Avg
from django.core.paginator import Paginator
from .models import Helmet, Category, Brand, Cart, CartItem, Review, WishlistItem, CompareItem
from .forms import ReviewForm
from orders.models import Order, OrderItem

def get_cart(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    return cart

def home(request):
    featured = Helmet.objects.filter(is_featured=True, is_available=True)[:8]
    new_arrivals = Helmet.objects.filter(is_available=True).order_by('-created_at')[:8]
    categories = Category.objects.all()
    brands = Brand.objects.all()
    
    # Recent reviews for homepage
    recent_reviews = Review.objects.select_related('user', 'helmet', 'helmet__brand').order_by('-created_at')[:6]
    
    context = {
        'featured': featured,
        'new_arrivals': new_arrivals,
        'categories': categories,
        'brands': brands,
        'recent_reviews': recent_reviews,
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
    
    context = {
        'helmets': helmets,
        'categories': Category.objects.all(),
        'brands': Brand.objects.all(),
        'sizes': Helmet.SIZES,
        'types': Helmet.HELMET_TYPES,
        'search_query': search or '',
    }
    return render(request, 'store/helmet_list.html', context)

def helmet_detail(request, slug):
    helmet = get_object_or_404(Helmet, slug=slug, is_available=True)
    related = Helmet.objects.filter(category=helmet.category, is_available=True).exclude(id=helmet.id)[:4]
    reviews = helmet.reviews.select_related('user').order_by('-created_at')
    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0
    
    # Check if user has purchased this helmet
    has_purchased = False
    if request.user.is_authenticated:
        has_purchased = OrderItem.objects.filter(
            order__user=request.user,
            helmet=helmet,
            order__status__in=['delivered', 'shipped']
        ).exists()
    
    # Check if user already reviewed
    user_reviewed = False
    if request.user.is_authenticated:
        user_reviewed = Review.objects.filter(helmet=helmet, user=request.user).exists()
    
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
    }
    return render(request, 'store/helmet_detail.html', context)

@login_required
def add_to_cart(request, helmet_id):
    helmet = get_object_or_404(Helmet, id=helmet_id)
    cart = get_cart(request)
    cart_item, created = CartItem.objects.get_or_create(cart=cart, helmet=helmet)
    if not created:
        cart_item.quantity += 1
        cart_item.save()
    messages.success(request, f'{helmet.name} added to cart!')
    return redirect(request.META.get('HTTP_REFERER', 'store:home'))

@login_required
def cart_detail(request):
    cart = get_cart(request)
    return render(request, 'store/cart.html', {'cart': cart})

@login_required
def update_cart(request, item_id):
    item = get_object_or_404(CartItem, id=item_id)
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))
        if quantity > 0 and quantity <= item.helmet.stock:
            item.quantity = quantity
            item.save()
        else:
            item.delete()
    return redirect('store:cart_detail')

@login_required
def remove_from_cart(request, item_id):
    item = get_object_or_404(CartItem, id=item_id)
    item.delete()
    messages.info(request, 'Item removed from cart.')
    return redirect('store:cart_detail')

@login_required
def add_review(request, helmet_id):
    helmet = get_object_or_404(Helmet, id=helmet_id)
    
    # Check if user purchased this helmet
    has_purchased = OrderItem.objects.filter(
        order__user=request.user,
        helmet=helmet,
        order__status__in=['delivered', 'shipped']
    ).exists()
    
    if not has_purchased:
        messages.error(request, 'You can only review helmets you have purchased!')
        return redirect('store:helmet_detail', slug=helmet.slug)
    
    # Check if already reviewed
    if Review.objects.filter(helmet=helmet, user=request.user).exists():
        messages.warning(request, 'You have already reviewed this helmet!')
        return redirect('store:helmet_detail', slug=helmet.slug)
    
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.user = request.user
            review.helmet = helmet
            review.save()
            messages.success(request, 'Review submitted!')
    return redirect('store:helmet_detail', slug=helmet.slug)

@login_required
def add_to_wishlist(request, helmet_id):
    helmet = get_object_or_404(Helmet, id=helmet_id)
    WishlistItem.objects.get_or_create(user=request.user, helmet=helmet)
    messages.success(request, 'Added to wishlist!')
    return redirect(request.META.get('HTTP_REFERER', 'store:home'))

@login_required
def remove_from_wishlist(request, helmet_id):
    WishlistItem.objects.filter(user=request.user, helmet_id=helmet_id).delete()
    return redirect('store:wishlist')

@login_required
def wishlist(request):
    items = WishlistItem.objects.filter(user=request.user).select_related('helmet', 'helmet__brand')
    return render(request, 'store/wishlist.html', {'items': items})

def add_to_compare(request, helmet_id):
    helmet = get_object_or_404(Helmet, id=helmet_id)
    session_id = request.session.session_key
    if not session_id:
        request.session.create()
        session_id = request.session.session_key
    
    current_count = CompareItem.objects.filter(session_id=session_id).count()
    if current_count >= 3:
        messages.warning(request, 'You can only compare up to 3 helmets.')
        return redirect(request.META.get('HTTP_REFERER', 'store:home'))
    
    CompareItem.objects.get_or_create(session_id=session_id, helmet=helmet)
    messages.success(request, f'{helmet.name} added to comparison.')
    return redirect(request.META.get('HTTP_REFERER', 'store:home'))

def remove_from_compare(request, helmet_id):
    session_id = request.session.session_key
    if session_id:
        CompareItem.objects.filter(session_id=session_id, helmet_id=helmet_id).delete()
    return redirect('store:compare_list')

def compare_list(request):
    session_id = request.session.session_key
    helmets = []
    if session_id:
        items = CompareItem.objects.filter(session_id=session_id).select_related('helmet', 'helmet__brand')[:3]
        helmets = [item.helmet for item in items]
    return render(request, 'store/compare.html', {'helmets': helmets})

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
    
    return render(request, 'store/size_finder.html', {'result': result, 'types': Helmet.HELMET_TYPES})