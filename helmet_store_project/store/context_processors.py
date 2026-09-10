from .models import Cart, CompareItem

def cart_context(request):
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
    else:
        session_id = request.session.session_key
        if not session_id:
            request.session.create()
            session_id = request.session.session_key
        cart, _ = Cart.objects.get_or_create(session_id=session_id)
    
    session_id = request.session.session_key
    compare_count = 0
    if session_id:
        compare_count = CompareItem.objects.filter(session_id=session_id).count()
    
    return {
        'cart': cart,
        'cart_count': cart.get_item_count(),
        'compare_count': compare_count,
    }