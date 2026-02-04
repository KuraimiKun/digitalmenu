"""Integration models for third-party services."""
import uuid
from django.db import models
from django.conf import settings
from apps.core.models import BaseModel


class IntegrationProvider(models.Model):
    """Third-party service providers available for integration."""
    
    CATEGORY_CHOICES = [
        ('delivery', 'Delivery Service'),
        ('pos', 'Point of Sale'),
        ('payment', 'Payment Gateway'),
        ('reservation', 'Reservation System'),
        ('marketing', 'Marketing Platform'),
        ('accounting', 'Accounting Software'),
        ('inventory', 'Inventory Management'),
        ('analytics', 'Analytics Platform'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to='integrations/logos/', blank=True, null=True)
    website_url = models.URLField(blank=True)
    documentation_url = models.URLField(blank=True)
    
    # API configuration template
    required_fields = models.JSONField(
        default=list,
        help_text='List of required configuration fields'
    )
    optional_fields = models.JSONField(default=list)
    
    # Webhook support
    supports_webhooks = models.BooleanField(default=False)
    webhook_events = models.JSONField(
        default=list,
        help_text='List of webhook events this provider can send'
    )
    
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['category', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"


class RestaurantIntegration(BaseModel):
    """Restaurant-specific integration configuration."""
    
    STATUS_CHOICES = [
        ('pending', 'Pending Setup'),
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('error', 'Error'),
        ('disconnected', 'Disconnected'),
    ]
    
    restaurant = models.ForeignKey(
        'restaurants.Restaurant',
        on_delete=models.CASCADE,
        related_name='integrations'
    )
    provider = models.ForeignKey(
        IntegrationProvider,
        on_delete=models.PROTECT,
        related_name='restaurant_integrations'
    )
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Encrypted credentials and configuration
    credentials = models.JSONField(
        default=dict,
        help_text='Encrypted API credentials'
    )
    configuration = models.JSONField(
        default=dict,
        help_text='Integration-specific settings'
    )
    
    # Menu sync settings for delivery platforms
    sync_menu = models.BooleanField(default=True)
    sync_prices = models.BooleanField(default=True)
    sync_availability = models.BooleanField(default=True)
    price_markup_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        help_text='Price markup for this platform'
    )
    
    # Location mapping
    location_mappings = models.JSONField(
        default=dict,
        help_text='Map restaurant locations to provider locations'
    )
    
    # Sync status
    last_sync_at = models.DateTimeField(null=True, blank=True)
    last_sync_status = models.CharField(max_length=20, blank=True)
    last_sync_message = models.TextField(blank=True)
    
    # Webhook configuration
    webhook_secret = models.CharField(max_length=255, blank=True)
    webhook_url = models.URLField(blank=True)
    
    connected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='connected_integrations'
    )
    connected_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['restaurant', 'provider']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.restaurant.name} - {self.provider.name}"


class DeliveryPlatformMenu(BaseModel):
    """Synced menu on a delivery platform."""
    
    integration = models.ForeignKey(
        RestaurantIntegration,
        on_delete=models.CASCADE,
        related_name='delivery_menus'
    )
    menu = models.ForeignKey(
        'menus.Menu',
        on_delete=models.CASCADE,
        related_name='delivery_platform_menus'
    )
    
    external_menu_id = models.CharField(max_length=255, blank=True)
    is_synced = models.BooleanField(default=False)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    
    # Track what's published
    synced_items = models.JSONField(
        default=dict,
        help_text='Map of local item IDs to external IDs'
    )
    sync_errors = models.JSONField(default=list)
    
    class Meta:
        unique_together = ['integration', 'menu']


class DeliveryOrder(BaseModel):
    """Orders received from delivery platforms."""
    
    STATUS_CHOICES = [
        ('received', 'Received'),
        ('confirmed', 'Confirmed'),
        ('preparing', 'Preparing'),
        ('ready', 'Ready for Pickup'),
        ('picked_up', 'Picked Up'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    
    integration = models.ForeignKey(
        RestaurantIntegration,
        on_delete=models.PROTECT,
        related_name='delivery_orders'
    )
    location = models.ForeignKey(
        'restaurants.Location',
        on_delete=models.PROTECT,
        related_name='delivery_orders'
    )
    
    # External order info
    external_order_id = models.CharField(max_length=255)
    external_order_number = models.CharField(max_length=100)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='received')
    
    # Customer info from platform
    customer_name = models.CharField(max_length=255)
    customer_phone = models.CharField(max_length=50, blank=True)
    delivery_address = models.JSONField(default=dict)
    special_instructions = models.TextField(blank=True)
    
    # Order details
    items = models.JSONField(default=list)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    platform_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tip = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Timing
    estimated_pickup_time = models.DateTimeField(null=True, blank=True)
    estimated_delivery_time = models.DateTimeField(null=True, blank=True)
    actual_pickup_time = models.DateTimeField(null=True, blank=True)
    
    # Link to internal order if created
    internal_order = models.OneToOneField(
        'orders.Order',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='delivery_order'
    )
    
    # Raw payload for debugging
    raw_payload = models.JSONField(default=dict)
    
    class Meta:
        unique_together = ['integration', 'external_order_id']
        ordering = ['-created_at']


class WebhookEvent(BaseModel):
    """Incoming webhook events from integrations."""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('processed', 'Processed'),
        ('failed', 'Failed'),
    ]
    
    integration = models.ForeignKey(
        RestaurantIntegration,
        on_delete=models.CASCADE,
        related_name='webhook_events'
    )
    
    event_type = models.CharField(max_length=100)
    event_id = models.CharField(max_length=255, blank=True)
    
    payload = models.JSONField(default=dict)
    headers = models.JSONField(default=dict)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    processed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    retry_count = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-created_at']


class POSIntegration(BaseModel):
    """Point of Sale system integration details."""
    
    integration = models.OneToOneField(
        RestaurantIntegration,
        on_delete=models.CASCADE,
        related_name='pos_config'
    )
    
    # Terminal configuration
    terminals = models.JSONField(
        default=list,
        help_text='List of POS terminals'
    )
    
    # Sync settings
    sync_sales = models.BooleanField(default=True)
    sync_inventory = models.BooleanField(default=False)
    sync_employees = models.BooleanField(default=False)
    
    # Menu item mapping
    item_mappings = models.JSONField(
        default=dict,
        help_text='Map POS items to menu items'
    )
    category_mappings = models.JSONField(default=dict)
    modifier_mappings = models.JSONField(default=dict)
    
    # Last sync data
    last_sales_sync = models.DateTimeField(null=True, blank=True)
    last_inventory_sync = models.DateTimeField(null=True, blank=True)


class PaymentGatewayConfig(BaseModel):
    """Payment gateway configuration."""
    
    integration = models.OneToOneField(
        RestaurantIntegration,
        on_delete=models.CASCADE,
        related_name='payment_config'
    )
    
    # Supported payment methods
    accept_credit_cards = models.BooleanField(default=True)
    accept_debit_cards = models.BooleanField(default=True)
    accept_digital_wallets = models.BooleanField(default=True)
    
    # Processing settings
    auto_capture = models.BooleanField(default=True)
    capture_delay_hours = models.IntegerField(default=0)
    
    # Stripe-specific
    stripe_account_id = models.CharField(max_length=255, blank=True)
    stripe_publishable_key = models.CharField(max_length=255, blank=True)
    
    # Square-specific
    square_location_id = models.CharField(max_length=255, blank=True)
    
    # Fee handling
    pass_processing_fee_to_customer = models.BooleanField(default=False)
    processing_fee_percentage = models.DecimalField(
        max_digits=4, decimal_places=2, default=2.9
    )
    processing_fee_fixed = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.30
    )


class IntegrationLog(models.Model):
    """Detailed logging for integration activities."""
    
    LEVEL_CHOICES = [
        ('debug', 'Debug'),
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    integration = models.ForeignKey(
        RestaurantIntegration,
        on_delete=models.CASCADE,
        related_name='logs'
    )
    
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES)
    action = models.CharField(max_length=100)
    message = models.TextField()
    
    request_data = models.JSONField(null=True, blank=True)
    response_data = models.JSONField(null=True, blank=True)
    
    duration_ms = models.IntegerField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['integration', '-created_at']),
            models.Index(fields=['level', '-created_at']),
        ]
