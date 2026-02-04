"""Order admin configuration."""
from django.contrib import admin
from .models import Order, OrderItem, OrderStatusHistory, Cart, CartItem, Review


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['total']


class OrderStatusHistoryInline(admin.TabularInline):
    model = OrderStatusHistory
    extra = 0
    readonly_fields = ['status', 'changed_by', 'notes', 'created_at']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'order_number', 'restaurant', 'location', 'customer_name',
        'order_type', 'status', 'payment_status', 'total', 'created_at'
    ]
    list_filter = ['status', 'order_type', 'payment_status', 'restaurant', 'created_at']
    search_fields = ['order_number', 'customer_name', 'customer_email', 'customer_phone']
    readonly_fields = ['order_number', 'subtotal', 'total']
    inlines = [OrderItemInline, OrderStatusHistoryInline]
    
    fieldsets = (
        ('Order Info', {
            'fields': ('order_number', 'restaurant', 'location', 'table', 'order_type', 'status')
        }),
        ('Customer', {
            'fields': ('customer', 'customer_name', 'customer_email', 'customer_phone')
        }),
        ('Pricing', {
            'fields': ('subtotal', 'tax_amount', 'discount_amount', 'delivery_fee', 'tip_amount', 'total', 'currency')
        }),
        ('Payment', {
            'fields': ('payment_status', 'payment_method', 'stripe_payment_intent_id')
        }),
        ('Delivery', {
            'fields': ('delivery_address', 'delivery_instructions'),
            'classes': ('collapse',)
        }),
        ('Timing', {
            'fields': ('scheduled_time', 'estimated_ready_time', 'actual_ready_time', 'completed_at')
        }),
        ('Notes', {
            'fields': ('notes', 'internal_notes', 'promo_code')
        }),
    )


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['id', 'restaurant', 'customer', 'expires_at', 'created_at']
    list_filter = ['restaurant', 'created_at']
    inlines = [CartItemInline]


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['order', 'customer', 'rating', 'is_public', 'created_at']
    list_filter = ['rating', 'is_public', 'created_at']
    search_fields = ['order__order_number', 'customer__email', 'comment']
