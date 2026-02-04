"""Order serializers."""
from rest_framework import serializers
from django.utils import timezone
from datetime import timedelta
from .models import Order, OrderItem, OrderStatusHistory, Cart, CartItem, Review


class OrderItemSerializer(serializers.ModelSerializer):
    total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = OrderItem
        fields = [
            'id', 'menu_item', 'variant', 'name', 'quantity',
            'unit_price', 'modifiers', 'modifier_total',
            'special_instructions', 'total'
        ]
        read_only_fields = ['id', 'total']


class OrderStatusHistorySerializer(serializers.ModelSerializer):
    changed_by_name = serializers.CharField(source='changed_by.get_full_name', read_only=True)
    
    class Meta:
        model = OrderStatusHistory
        fields = ['id', 'status', 'changed_by', 'changed_by_name', 'notes', 'created_at']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    status_history = OrderStatusHistorySerializer(many=True, read_only=True)
    restaurant_name = serializers.CharField(source='restaurant.name', read_only=True)
    location_name = serializers.CharField(source='location.name', read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'restaurant', 'restaurant_name',
            'location', 'location_name', 'table',
            'customer', 'customer_name', 'customer_email', 'customer_phone',
            'order_type', 'status',
            'subtotal', 'tax_amount', 'discount_amount', 'delivery_fee',
            'tip_amount', 'total', 'currency',
            'payment_status', 'payment_method',
            'delivery_address', 'delivery_instructions',
            'scheduled_time', 'estimated_ready_time',
            'notes', 'promo_code',
            'source', 'items', 'status_history',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'order_number', 'subtotal', 'total',
            'created_at', 'updated_at'
        ]


class OrderListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for order lists."""
    item_count = serializers.IntegerField(source='items.count', read_only=True)
    customer_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'customer_display', 'order_type',
            'status', 'payment_status', 'total', 'item_count',
            'scheduled_time', 'created_at'
        ]
    
    def get_customer_display(self, obj):
        if obj.customer:
            return obj.customer.get_full_name()
        return obj.customer_name or 'Guest'


class OrderCreateSerializer(serializers.Serializer):
    """Serializer for creating orders from cart."""
    cart_id = serializers.UUIDField(required=False)
    location_id = serializers.UUIDField()
    order_type = serializers.ChoiceField(choices=Order.OrderType.choices)
    
    # Customer info (for guests)
    customer_name = serializers.CharField(required=False, allow_blank=True)
    customer_email = serializers.EmailField(required=False, allow_blank=True)
    customer_phone = serializers.CharField(required=False, allow_blank=True)
    
    # Dine-in
    table_id = serializers.UUIDField(required=False, allow_null=True)
    
    # Delivery
    delivery_address = serializers.CharField(required=False, allow_blank=True)
    delivery_instructions = serializers.CharField(required=False, allow_blank=True)
    
    # Timing
    scheduled_time = serializers.DateTimeField(required=False, allow_null=True)
    
    # Notes
    notes = serializers.CharField(required=False, allow_blank=True)
    
    # Payment
    payment_method = serializers.CharField(required=False)
    
    # Items (if not using cart)
    items = serializers.ListField(
        child=serializers.DictField(),
        required=False
    )


class OrderUpdateStatusSerializer(serializers.Serializer):
    """Serializer for updating order status."""
    status = serializers.ChoiceField(choices=Order.Status.choices)
    notes = serializers.CharField(required=False, allow_blank=True)
    estimated_ready_time = serializers.DateTimeField(required=False, allow_null=True)


class CartItemSerializer(serializers.ModelSerializer):
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    modifier_total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    item_name = serializers.CharField(source='menu_item.name', read_only=True)
    item_image = serializers.ImageField(source='menu_item.image', read_only=True)
    variant_name = serializers.CharField(source='variant.name', read_only=True)
    
    class Meta:
        model = CartItem
        fields = [
            'id', 'menu_item', 'item_name', 'item_image',
            'variant', 'variant_name', 'quantity',
            'modifiers', 'special_instructions',
            'unit_price', 'modifier_total', 'total'
        ]
        read_only_fields = ['id', 'unit_price', 'modifier_total', 'total']


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    item_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Cart
        fields = [
            'id', 'restaurant', 'location', 'items',
            'promo_code', 'discount_amount',
            'subtotal', 'item_count', 'expires_at'
        ]
        read_only_fields = ['id', 'expires_at']


class AddToCartSerializer(serializers.Serializer):
    """Serializer for adding items to cart."""
    menu_item_id = serializers.UUIDField()
    variant_id = serializers.UUIDField(required=False, allow_null=True)
    quantity = serializers.IntegerField(min_value=1, default=1)
    modifiers = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=list
    )
    special_instructions = serializers.CharField(required=False, allow_blank=True)


class UpdateCartItemSerializer(serializers.Serializer):
    """Serializer for updating cart items."""
    quantity = serializers.IntegerField(min_value=0)  # 0 removes the item
    modifiers = serializers.ListField(
        child=serializers.DictField(),
        required=False
    )
    special_instructions = serializers.CharField(required=False, allow_blank=True)


class ApplyPromoCodeSerializer(serializers.Serializer):
    """Serializer for applying promo codes."""
    promo_code = serializers.CharField()


class ReviewSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    
    class Meta:
        model = Review
        fields = [
            'id', 'order', 'customer', 'customer_name',
            'rating', 'food_rating', 'service_rating', 'delivery_rating',
            'comment', 'response', 'responded_at',
            'is_public', 'created_at'
        ]
        read_only_fields = ['id', 'customer', 'response', 'responded_at', 'created_at']


class ReviewResponseSerializer(serializers.Serializer):
    """Serializer for responding to reviews."""
    response = serializers.CharField()
