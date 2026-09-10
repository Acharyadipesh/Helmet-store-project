from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('checkout/', views.checkout_view, name='checkout'),
    path('detail/<str:order_id>/', views.order_detail_view, name='order_detail'),
    
    # Payment Initiation
    path('initiate/<str:order_id>/', views.initiate_payment_view, name='initiate_payment'),
    
    # eSewa Callbacks
    path('esewa-success/', views.esewa_callback_view, name='esewa_success'),
    path('esewa-failure/', views.esewa_callback_view, name='esewa_failure'),
    
    # Khalti Callback
    path('khalti-verify/', views.khalti_callback_view, name='khalti_verify'),
]