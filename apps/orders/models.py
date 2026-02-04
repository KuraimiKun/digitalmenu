"""
Order models for online and in-store ordering.
"""
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from apps.core.models import BaseModel
import uuid


class Order(BaseModel):
    """Main order entity."""
    
    class Status(models.TextChoices):
        PENDING = 'pending', _('Pending')
        CONFIRMED = 'confirmed', _('Confirmed')
        PREPARING = 'preparing', _('Preparing')
        READY = 'ready', _('Ready')
        OUT_FOR_DELIVERY = 'out_for_delivery', _('Out for Delivery')
        DELIVERED = 'delivered', _('Delivered')
        PICKED_UP = 'picked_up', _('Picked Up')
        COMPLETED = 'completed', _('Completed')
        CANCELLED = 'cancelled', _('Cancelled')
        REFUNDED = 'refunded', _('Refunded')
    
    class OrderType(models.TextChoices):
        DINE_IN = 'dine_in', _('Dine In')
        TAKEOUT = 'takeout', _('Takeout')
        DELIVERY = 'delivery', _('Delivery')
        CURBSIDE = 'curbside', _('Curbside Pickup')
    
    class PaymentStatus(models.TextChoices):
        PENDING = 'pending', _('Pending')
        PAID = 'paid', _('Paid')
        PARTIALLY_PAID = 'partially_paid', _('Partially Paid')
        REFUNDED = 'refunded', _('Refunded')
        FAILED = 'failed', _('Failed')
    
    # Order identification
    order_number = models.CharField(max_length=20, unique=True, db_index=True)
    
    # Restaurant & Location
    restaurant = models.ForeignKey(
        'restaurants.Restaurant',
        on_delete=models.PROTECT,
        related_name='orders'
    )
    location = models.ForeignKey(
        'restaurants.Location',
        on_delete=models.PROTECT,
        related_name='orders'
    )
    
    # Customer
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders'
    )
    customer_name = models.CharField(max_length=200, blank=True)
    customer_email = models.EmailField(blank=True)
    customer_phone = models.CharField(max_length=30, blank=True)
    
    # Table (for dine-in)
    table = models.ForeignKey(
        'restaurants.Table',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders'
    )
    
    # Order details
    order_type = models.CharField(max_length=20, choices=OrderType.choices, default=OrderType.DINE_IN)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    
    # Pricing
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tip_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='USD')
    
    # Payment
    payment_status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    payment_method = models.CharField(max_length=50, blank=True)
    stripe_payment_intent_id = models.CharField(max_length=100, blank=True, db_index=True)
    
    # Delivery details
    delivery_address = models.TextField(blank=True)
    delivery_instructions = models.TextField(blank=True)
    delivery_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    delivery_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    # Timing
    scheduled_time = models.DateTimeField(null=True, blank=True)  # For scheduled orders
    estimated_ready_time = models.DateTimeField(null=True, blank=True)
    actual_ready_time = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Notes
    notes = models.TextField(blank=True)
    internal_notes = models.TextField(blank=True)
    
    # Promotion
    promotion = models.ForeignKey(
        'promotions.Promotion',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders'
    )
    promo_code = models.CharField(max_length=50, blank=True)
    
    # Source tracking
    source = models.CharField(max_length=50, default='web')  # web, app, pos, kiosk, third_party
    source_order_id = models.CharField(max_length=100, blank=True)  # External order ID
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['restaurant', 'status']),
            models.Index(fields=['location', 'status']),
            models.Index(fields=['customer', 'created_at']),
            models.Index(fields=['order_number']),
        ]
    
    def __str__(self):
        return f"Order #{self.order_number}"
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        self.calculate_totals()
        super().save(*args, **kwargs)
    
    def generate_order_number(self):
        """Generate unique order number."""
        import random
        import string
        prefix = self.location.slug[:3].upper() if self.location else 'ORD'
        suffix = ''.join(random.choices(string.digits, k=6))
        return f"{prefix}-{suffix}"
    
    def calculate_totals(self):
        """Calculate order totals from items."""
        subtotal = sum(item.total for item in self.items.all())
        self.subtotal = subtotal
        self.total = subtotal + self.tax_amount + self.delivery_fee - self.discount_amount + self.tip_amount


class OrderItem(BaseModel):
    """Individual items in an order."""
    
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )
    menu_item = models.ForeignKey(
        'menus.MenuItem',
        on_delete=models.PROTECT,
        related_name='order_items'
    )
    variant = models.ForeignKey(
        'menus.MenuItemVariant',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    name = models.CharField(max_length=200)  # Snapshot of item name
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Modifiers
    modifiers = models.JSONField(default=list)  # List of selected modifiers with prices
    modifier_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Notes
    special_instructions = models.TextField(blank=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.quantity}x {self.name}"
    
    @property
    def total(self):
        return (self.unit_price + self.modifier_total) * self.quantity


class OrderStatusHistory(BaseModel):
    """Track order status changes."""
    
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='status_history'
    )
    status = models.CharField(max_length=20, choices=Order.Status.choices)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Order status histories'
    
    def __str__(self):
        return f"{self.order.order_number} - {self.status}"


class Cart(BaseModel):
    """Shopping cart for in-progress orders."""
    
    session_id = models.CharField(max_length=100, db_index=True)
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='carts'
    )
    restaurant = models.ForeignKey(
        'restaurants.Restaurant',
        on_delete=models.CASCADE,
        related_name='carts'
    )
    location = models.ForeignKey(
        'restaurants.Location',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    
    # Applied promotion
    promo_code = models.CharField(max_length=50, blank=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    expires_at = models.DateTimeField()
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Cart {self.id}"
    
    @property
    def subtotal(self):
        return sum(item.total for item in self.items.all())
    
    @property
    def item_count(self):
        return sum(item.quantity for item in self.items.all())


class CartItem(BaseModel):
    """Items in a cart."""
    
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items'
    )
    menu_item = models.ForeignKey(
        'menus.MenuItem',
        on_delete=models.CASCADE
    )
    variant = models.ForeignKey(
        'menus.MenuItemVariant',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    quantity = models.PositiveIntegerField(default=1)
    modifiers = models.JSONField(default=list)
    special_instructions = models.TextField(blank=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.quantity}x {self.menu_item.name}"
    
    @property
    def unit_price(self):
        price = self.menu_item.price
        if self.variant:
            price += self.variant.price_adjustment
        return price
    
    @property
    def modifier_total(self):
        return sum(m.get('price', 0) for m in self.modifiers)
    
    @property
    def total(self):
        return (self.unit_price + self.modifier_total) * self.quantity


class Review(BaseModel):
    """Customer reviews for orders."""
    
    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name='review'
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='reviews'
    )
    
    rating = models.PositiveSmallIntegerField()  # 1-5
    food_rating = models.PositiveSmallIntegerField(null=True, blank=True)
    service_rating = models.PositiveSmallIntegerField(null=True, blank=True)
    delivery_rating = models.PositiveSmallIntegerField(null=True, blank=True)
    
    comment = models.TextField(blank=True)
    
    # Restaurant response
    response = models.TextField(blank=True)
    responded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='review_responses'
    )
    responded_at = models.DateTimeField(null=True, blank=True)
    
    is_public = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Review for {self.order.order_number}"
