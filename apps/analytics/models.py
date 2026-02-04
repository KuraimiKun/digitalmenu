"""
Analytics models for tracking restaurant performance.
"""
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from apps.core.models import BaseModel


class DailySalesReport(BaseModel):
    """Daily aggregated sales data."""
    
    restaurant = models.ForeignKey(
        'restaurants.Restaurant',
        on_delete=models.CASCADE,
        related_name='daily_sales'
    )
    location = models.ForeignKey(
        'restaurants.Location',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='daily_sales'
    )
    date = models.DateField(db_index=True)
    
    # Order counts
    total_orders = models.PositiveIntegerField(default=0)
    completed_orders = models.PositiveIntegerField(default=0)
    cancelled_orders = models.PositiveIntegerField(default=0)
    
    # Order types
    dine_in_orders = models.PositiveIntegerField(default=0)
    takeout_orders = models.PositiveIntegerField(default=0)
    delivery_orders = models.PositiveIntegerField(default=0)
    
    # Revenue
    gross_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_collected = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discounts_given = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tips_received = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    delivery_fees = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Averages
    average_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    average_items_per_order = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Items
    total_items_sold = models.PositiveIntegerField(default=0)
    
    # Customers
    unique_customers = models.PositiveIntegerField(default=0)
    new_customers = models.PositiveIntegerField(default=0)
    returning_customers = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['-date']
        unique_together = ['restaurant', 'location', 'date']
        indexes = [
            models.Index(fields=['restaurant', 'date']),
            models.Index(fields=['location', 'date']),
        ]
    
    def __str__(self):
        return f"{self.restaurant.name} - {self.date}"


class MenuItemAnalytics(BaseModel):
    """Analytics for individual menu items."""
    
    restaurant = models.ForeignKey(
        'restaurants.Restaurant',
        on_delete=models.CASCADE,
        related_name='item_analytics'
    )
    menu_item = models.ForeignKey(
        'menus.MenuItem',
        on_delete=models.CASCADE,
        related_name='analytics'
    )
    date = models.DateField(db_index=True)
    
    # Sales
    quantity_sold = models.PositiveIntegerField(default=0)
    revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Engagement
    views = models.PositiveIntegerField(default=0)
    add_to_cart = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['-date']
        unique_together = ['menu_item', 'date']
        indexes = [
            models.Index(fields=['restaurant', 'date']),
        ]
    
    def __str__(self):
        return f"{self.menu_item.name} - {self.date}"
    
    @property
    def conversion_rate(self):
        if self.views > 0:
            return (self.quantity_sold / self.views) * 100
        return 0


class CategoryAnalytics(BaseModel):
    """Analytics for menu categories."""
    
    restaurant = models.ForeignKey(
        'restaurants.Restaurant',
        on_delete=models.CASCADE,
        related_name='category_analytics'
    )
    category = models.ForeignKey(
        'menus.Category',
        on_delete=models.CASCADE,
        related_name='analytics'
    )
    date = models.DateField(db_index=True)
    
    items_sold = models.PositiveIntegerField(default=0)
    revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    views = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['-date']
        unique_together = ['category', 'date']


class CustomerAnalytics(BaseModel):
    """Customer behavior analytics."""
    
    restaurant = models.ForeignKey(
        'restaurants.Restaurant',
        on_delete=models.CASCADE,
        related_name='customer_analytics'
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='restaurant_analytics'
    )
    
    # Lifetime stats
    total_orders = models.PositiveIntegerField(default=0)
    total_spent = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    average_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Preferences
    favorite_items = models.JSONField(default=list)  # List of item IDs
    favorite_categories = models.JSONField(default=list)
    preferred_order_type = models.CharField(max_length=20, blank=True)
    
    # Engagement
    last_order_date = models.DateTimeField(null=True, blank=True)
    days_since_last_order = models.PositiveIntegerField(default=0)
    
    # Loyalty
    loyalty_points = models.PositiveIntegerField(default=0)
    loyalty_tier = models.CharField(max_length=50, blank=True)
    
    class Meta:
        unique_together = ['restaurant', 'customer']
    
    def __str__(self):
        return f"{self.customer.email} - {self.restaurant.name}"


class MenuViewEvent(BaseModel):
    """Track menu view events for analytics."""
    
    restaurant = models.ForeignKey(
        'restaurants.Restaurant',
        on_delete=models.CASCADE,
        related_name='menu_views'
    )
    menu = models.ForeignKey(
        'menus.Menu',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    menu_item = models.ForeignKey(
        'menus.MenuItem',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    
    session_id = models.CharField(max_length=100, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    # Event details
    event_type = models.CharField(max_length=50)  # view, add_to_cart, etc.
    
    # Context
    device_type = models.CharField(max_length=20, blank=True)  # mobile, tablet, desktop
    browser = models.CharField(max_length=50, blank=True)
    referrer = models.URLField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['restaurant', 'created_at']),
            models.Index(fields=['session_id']),
        ]


class HourlySalesData(BaseModel):
    """Hourly sales aggregation for peak time analysis."""
    
    restaurant = models.ForeignKey(
        'restaurants.Restaurant',
        on_delete=models.CASCADE,
        related_name='hourly_sales'
    )
    location = models.ForeignKey(
        'restaurants.Location',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    
    date = models.DateField()
    hour = models.PositiveSmallIntegerField()  # 0-23
    
    order_count = models.PositiveIntegerField(default=0)
    revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    items_sold = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['date', 'hour']
        unique_together = ['restaurant', 'location', 'date', 'hour']


class PopularItemsReport(BaseModel):
    """Weekly/Monthly popular items report."""
    
    class Period(models.TextChoices):
        WEEKLY = 'weekly', _('Weekly')
        MONTHLY = 'monthly', _('Monthly')
    
    restaurant = models.ForeignKey(
        'restaurants.Restaurant',
        on_delete=models.CASCADE,
        related_name='popular_items_reports'
    )
    
    period = models.CharField(max_length=20, choices=Period.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    
    # Top items data (JSON for flexibility)
    top_items = models.JSONField(default=list)
    top_categories = models.JSONField(default=list)
    
    class Meta:
        ordering = ['-start_date']
