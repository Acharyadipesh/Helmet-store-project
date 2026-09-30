from django.contrib import admin
from .models import Category, Brand, Helmet, HelmetImage, Review, Cart, CartItem, WishlistItem, CompareItem


class HelmetImageInline(admin.TabularInline):
    model = HelmetImage
    extra = 2


@admin.register(Helmet)
class HelmetAdmin(admin.ModelAdmin):
    list_display = ['name', 'brand', 'price', 'stock', 'helmet_type', 'is_available', 'is_featured']
    list_filter = ['helmet_type', 'brand', 'certification', 'is_available', 'size']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [HelmetImageInline]
    list_editable = ['price', 'stock', 'is_available', 'is_featured']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['user', 'helmet', 'rating', 'is_verified_purchase', 'created_at']
    list_filter = ['rating', 'is_verified_purchase', 'created_at']
    search_fields = ['user__username', 'helmet__name', 'comment']
    readonly_fields = ['created_at']


admin.site.register(Cart)
admin.site.register(CartItem)
admin.site.register(WishlistItem)
admin.site.register(CompareItem)