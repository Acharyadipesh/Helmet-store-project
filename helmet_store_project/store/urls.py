from django.urls import path
from . import views

app_name = 'store'

urlpatterns = [
    path('', views.home, name='home'),
    path('helmets/', views.helmet_list, name='helmet_list'),
    path('helmets/<slug:slug>/', views.helmet_detail, name='helmet_detail'),
    path('cart/', views.cart_detail, name='cart_detail'),
    path('cart/add/<int:helmet_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:item_id>/', views.update_cart, name='update_cart'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),

    # Reviews
    path('review/<int:helmet_id>/', views.add_review, name='add_review'),
    path('review/write/<int:item_id>/', views.write_review_view, name='write_review'),
    path('review/delete/<int:review_id>/', views.delete_review_view, name='delete_review'),

    # Wishlist
    path('wishlist/', views.wishlist, name='wishlist'),
    path('wishlist/add/<int:helmet_id>/', views.add_to_wishlist, name='add_to_wishlist'),
    path('wishlist/remove/<int:helmet_id>/', views.remove_from_wishlist, name='remove_from_wishlist'),

    # Compare
    path('compare/', views.compare_list, name='compare_list'),
    path('compare/add/<int:helmet_id>/', views.add_to_compare, name='add_to_compare'),
    path('compare/remove/<int:helmet_id>/', views.remove_from_compare, name='remove_from_compare'),

    # Size finder
    path('size-finder/', views.size_finder, name='size_finder'),
]