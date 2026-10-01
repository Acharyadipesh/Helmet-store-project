from .models import Cart, CompareItem


def cart_context(request):
    """Provides cart_count and compare_count to every template."""
    cart_count = 0
    compare_count = 0

    # Cart count (only for logged-in users)
    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user)
            cart_count = cart.get_item_count()
        except Cart.DoesNotExist:
            cart_count = 0

    # Compare count (session-based, works for everyone)
    session_id = request.session.session_key
    if session_id:
        compare_count = CompareItem.objects.filter(session_id=session_id).count()

    return {
        'cart_count': cart_count,
        'compare_count': compare_count,
    }