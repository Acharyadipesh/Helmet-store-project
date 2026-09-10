from django.db import models
from django.contrib.auth.models import User
from store.models import Helmet

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    
    PAYMENT_CHOICES = [
        ('cod', 'Cash on Delivery'),
        ('khalti', 'Khalti'),
        ('esewa', 'eSewa'),
    ]
    
    PROVINCE_CHOICES = [
        ('koshi', 'Koshi Province'),
        ('madhesh', 'Madhesh Province'),
        ('bagmati', 'Bagmati Province'),
        ('gandaki', 'Gandaki Province'),
        ('lumbini', 'Lumbini Province'),
        ('karnali', 'Karnali Province'),
        ('sudurpashchim', 'Sudurpashchim Province'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='order_set')
    order_id = models.CharField(max_length=20, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default='cod')
    
    full_name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    address = models.TextField()
    city = models.CharField(max_length=100)
    province = models.CharField(max_length=20, choices=PROVINCE_CHOICES)
    
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_paid = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Order #{self.order_id}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    helmet = models.ForeignKey(Helmet, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    
    def __str__(self):
        return f"{self.quantity} x {self.helmet.name}"
    
    def get_subtotal(self):
        return self.quantity * self.price