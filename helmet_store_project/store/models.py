from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.db.models import Avg


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class Brand(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    logo = models.ImageField(upload_to='brands/', blank=True, null=True)

    def __str__(self):
        return self.name


class Helmet(models.Model):
    HELMET_TYPES = [
        ('full_face', 'Full Face'),
        ('open_face', 'Open Face / 3/4'),
        ('half', 'Half Helmet'),
        ('modular', 'Modular / Flip-up'),
        ('off_road', 'Off-Road / Motocross'),
        ('dual_sport', 'Dual Sport / Adventure'),
    ]

    SIZES = [
        ('XS', 'Extra Small'),
        ('S', 'Small'),
        ('M', 'Medium'),
        ('L', 'Large'),
        ('XL', 'Extra Large'),
        ('XXL', 'Double Extra Large'),
    ]

    CERTIFICATIONS = [
        ('dot', 'DOT'),
        ('ece', 'ECE 22.05'),
        ('snell', 'SNELL'),
        ('sharp', 'SHARP'),
    ]

    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='helmets')
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='helmets')
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    helmet_type = models.CharField(max_length=20, choices=HELMET_TYPES)
    size = models.CharField(max_length=10, choices=SIZES)
    color = models.CharField(max_length=50)
    weight = models.DecimalField(max_digits=5, decimal_places=2, help_text="Weight in kg", default=1.5)
    material = models.CharField(max_length=100, help_text="e.g., Carbon Fiber, Polycarbonate", default="Polycarbonate")
    certification = models.CharField(max_length=20, choices=CERTIFICATIONS, default='dot')
    ventilation = models.BooleanField(default=True)
    bluetooth_ready = models.BooleanField(default=False)
    sun_visor = models.BooleanField(default=False)
    image = models.ImageField(upload_to='helmets/%Y/%m/', blank=True, null=True)
    stock = models.PositiveIntegerField(default=10)
    is_available = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.brand.name} {self.name}"

    def get_absolute_url(self):
        return reverse('store:helmet_detail', args=[self.slug])

    def get_price(self):
        if self.discount_price:
            return self.discount_price
        return self.price

    def get_discount_percentage(self):
        if self.discount_price:
            return int(((self.price - self.discount_price) / self.price) * 100)
        return 0

    def get_avg_rating(self):
        avg = self.reviews.aggregate(Avg('rating'))['rating__avg']
        return round(avg, 1) if avg else 0


class HelmetImage(models.Model):
    helmet = models.ForeignKey(Helmet, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='helmets/gallery/')

    def __str__(self):
        return f"Image for {self.helmet.name}"


class Review(models.Model):
    helmet = models.ForeignKey(Helmet, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    order = models.ForeignKey(
        'orders.Order',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviews'
    )
    rating = models.PositiveSmallIntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField()
    is_verified_purchase = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['helmet', 'user']
        ordering = ['-created_at']

    def __str__(self):
        return f"Review by {self.user.username}"


class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    session_id = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cart {self.id}"

    def get_total(self):
        return sum(item.get_subtotal() for item in self.items.all())

    def get_item_count(self):
        return sum(item.quantity for item in self.items.all())


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    helmet = models.ForeignKey(Helmet, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ['cart', 'helmet']

    def __str__(self):
        return f"{self.quantity} x {self.helmet.name}"

    def get_subtotal(self):
        return self.quantity * self.helmet.get_price()


class WishlistItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlist')
    helmet = models.ForeignKey(Helmet, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'helmet']

    def __str__(self):
        return f"{self.user.username} - {self.helmet.name}"


class CompareItem(models.Model):
    session_id = models.CharField(max_length=100)
    helmet = models.ForeignKey(Helmet, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['session_id', 'helmet']

    def __str__(self):
        return f"Compare: {self.helmet.name}"