from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['helmet', 'quantity', 'price', 'subtotal_display']
    fields = ['helmet', 'quantity', 'price', 'subtotal_display']
    can_delete = False

    def subtotal_display(self, obj):
        if obj.pk:
            return f"NRs {obj.get_subtotal()}"
        return "-"
    subtotal_display.short_description = 'Subtotal'


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'order_id',
        'user',
        'full_name',
        'total_amount',
        'payment_method',
        'status_badge',
        'paid_badge',
        'created_at',
    ]
    list_filter = ['status', 'payment_method', 'is_paid', 'created_at', 'province']
    search_fields = ['order_id', 'full_name', 'email', 'phone']
    list_editable = []
    readonly_fields = ['order_id', 'created_at', 'updated_at', 'is_paid']
    inlines = [OrderItemInline]

    fieldsets = (
        ('Order Info', {
            'fields': ('order_id', 'user', 'status', 'payment_method', 'is_paid', 'created_at', 'updated_at')
        }),
        ('Customer Details', {
            'fields': ('full_name', 'email', 'phone')
        }),
        ('Shipping Address', {
            'fields': ('address', 'city', 'province')
        }),
        ('Payment', {
            'fields': ('total_amount', 'shipping_cost')
        }),
    )

    actions = [
        'mark_as_paid',
        'mark_as_processing',
        'mark_as_shipped',
        'mark_as_delivered',
        'mark_as_cancelled',
    ]

    # ==================== CUSTOM COLUMNS ====================
    def status_badge(self, obj):
        colors = {
            'pending': '#ffc107',
            'paid': '#28a745',
            'processing': '#0d6efd',
            'shipped': '#17a2b8',
            'delivered': '#28a745',
            'cancelled': '#dc3545',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background:{};color:white;padding:3px 10px;border-radius:12px;font-size:11px;font-weight:600;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'

    def paid_badge(self, obj):
        if obj.is_paid:
            return mark_safe('<span style="color:#28a745;font-weight:700;">✔ Paid</span>')
        return mark_safe('<span style="color:#dc3545;font-weight:700;">✘ Unpaid</span>')
    paid_badge.short_description = 'Paid?'
    paid_badge.admin_order_field = 'is_paid'

    # ==================== ADMIN ACTIONS ====================
    def mark_as_paid(self, request, queryset):
        """Mark orders as PAID.
        - COD orders: also marked as DELIVERED (payment = delivery for COD)
        - Online orders: just marked paid, processing continues
        """
        cod_count = 0
        online_count = 0
        for order in queryset:
            if order.payment_method == 'cod':
                order.status = 'delivered'
                cod_count += 1
            else:
                order.status = 'paid'
                online_count += 1
            order.is_paid = True
            order.save()

        msg_parts = []
        if cod_count:
            msg_parts.append(f'📦 {cod_count} COD order(s) marked as Delivered & Paid')
        if online_count:
            msg_parts.append(f'✅ {online_count} online order(s) marked as Paid')
        self.message_user(request, '; '.join(msg_parts) + '.')
    mark_as_paid.short_description = '✅ Mark as Paid (COD → Delivered)'

    def mark_as_processing(self, request, queryset):
        updated = queryset.update(status='processing')
        self.message_user(request, f'⚙️ {updated} order(s) marked as Processing.')
    mark_as_processing.short_description = '⚙️ Mark selected orders as Processing'

    def mark_as_shipped(self, request, queryset):
        updated = queryset.update(status='shipped')
        self.message_user(request, f'🚚 {updated} order(s) marked as Shipped.')
    mark_as_shipped.short_description = '🚚 Mark selected orders as Shipped'

    def mark_as_delivered(self, request, queryset):
        """Mark as DELIVERED and also set is_paid=True (COD case)."""
        updated = queryset.update(is_paid=True, status='delivered')
        self.message_user(request, f'📦 {updated} order(s) marked as Delivered and Paid.')
    mark_as_delivered.short_description = '📦 Mark selected orders as Delivered (auto-marks Paid)'

    def mark_as_cancelled(self, request, queryset):
        updated = queryset.update(status='cancelled')
        self.message_user(request, f'❌ {updated} order(s) marked as Cancelled.')
    mark_as_cancelled.short_description = '❌ Mark selected orders as Cancelled'


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['id', 'order', 'helmet', 'quantity', 'price', 'subtotal_display']
    list_filter = ['order__status']
    search_fields = ['order__order_id', 'helmet__name', 'order__full_name']
    readonly_fields = ['order', 'helmet', 'quantity', 'price']

    def subtotal_display(self, obj):
        return f"NRs {obj.get_subtotal()}"
    subtotal_display.short_description = 'Subtotal'


# Customize admin site headers
admin.site.site_header = "HelmetHub Administration"
admin.site.site_title = "HelmetHub Admin"
admin.site.index_title = "Welcome to HelmetHub Admin Panel"