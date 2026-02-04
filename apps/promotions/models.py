"""
Promotions, discounts, and loyalty program models.
"""
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from apps.core.models import BaseModel


class Promotion(BaseModel):
    """Promotions and discount codes."""
    
    class DiscountType(models.TextChoices):
        PERCENTAGE = 'percentage', _('Percentage Off')
        FIXED = 'fixed', _('Fixed Amount Off')
        FREE_ITEM = 'free_item', _('Free Item')
        FREE_DELIVERY = 'free_delivery', _('Free Delivery')
        BOGO = 'bogo', _('Buy One Get One')
    
    class Status(models.TextChoices):
        ACTIVE = 'active', _('Active')
        SCHEDULED = 'scheduled', _('Scheduled')
        EXPIRED = 'expired', _('Expired')
        DISABLED = 'disabled', _('Disabled')
    
    restaurant = models.ForeignKey(
        'restaurants.Restaurant',
        on_delete=models.CASCADE,
        related_name='promotions'
    )
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    code = models.CharField(max_length=50, db_index=True)
    
    discount_type = models.CharField(max_length=20, choices=DiscountType.choices)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Conditions
    minimum_order = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    maximum_discount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Usage limits
    usage_limit = models.PositiveIntegerField(null=True, blank=True)  # Total uses
    usage_limit_per_customer = models.PositiveIntegerField(default=1)
    times_used = models.PositiveIntegerField(default=0)
    
    # Validity
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    
    # Restrictions
    applicable_items = models.ManyToManyField(
        'menus.MenuItem',
        blank=True,
        related_name='promotions'
    )
    applicable_categories = models.ManyToManyField(
        'menus.Category',
        blank=True,
        related_name='promotions'
    )
    applicable_locations = models.ManyToManyField(
        'restaurants.Location',
        blank=True,
        related_name='promotions'
    )
    
    # Order type restrictions
    apply_to_dine_in = models.BooleanField(default=True)
    apply_to_takeout = models.BooleanField(default=True)
    apply_to_delivery = models.BooleanField(default=True)
    
    # Customer restrictions
    first_order_only = models.BooleanField(default=False)
    eligible_customers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='exclusive_promotions'
    )
    
    # For free item promotions
    free_item = models.ForeignKey(
        'menus.MenuItem',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='free_with_promotions'
    )
    
    # BOGO settings
    buy_quantity = models.PositiveIntegerField(default=1)
    get_quantity = models.PositiveIntegerField(default=1)
    
    class Meta:
        ordering = ['-start_date']
        unique_together = ['restaurant', 'code']
        indexes = [
            models.Index(fields=['restaurant', 'status']),
            models.Index(fields=['code']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.code})"
    
    @property
    def is_valid(self):
        now = timezone.now()
        return (
            self.status == self.Status.ACTIVE and
            self.start_date <= now <= self.end_date and
            (self.usage_limit is None or self.times_used < self.usage_limit)
        )
    
    def can_use(self, customer, order_total, order_type=None):
        """Check if promotion can be used."""
        if not self.is_valid:
            return False, "Promotion is not valid"
        
        if order_total < self.minimum_order:
            return False, f"Minimum order of ${self.minimum_order} required"
        
        # Check order type
        if order_type:
            if order_type == 'dine_in' and not self.apply_to_dine_in:
                return False, "Not applicable for dine-in orders"
            if order_type == 'takeout' and not self.apply_to_takeout:
                return False, "Not applicable for takeout orders"
            if order_type == 'delivery' and not self.apply_to_delivery:
                return False, "Not applicable for delivery orders"
        
        # Check customer usage
        if customer:
            customer_usage = PromotionUsage.objects.filter(
                promotion=self,
                customer=customer
            ).count()
            if customer_usage >= self.usage_limit_per_customer:
                return False, "Usage limit reached for this customer"
            
            # First order check
            if self.first_order_only:
                from apps.orders.models import Order
                if Order.objects.filter(customer=customer).exists():
                    return False, "Only valid for first orders"
        
        return True, None
    
    def calculate_discount(self, order_total, items=None):
        """Calculate discount amount."""
        if self.discount_type == self.DiscountType.PERCENTAGE:
            discount = order_total * (self.discount_value / 100)
        elif self.discount_type == self.DiscountType.FIXED:
            discount = self.discount_value
        elif self.discount_type == self.DiscountType.FREE_DELIVERY:
            discount = 0  # Handled separately
        else:
            discount = 0
        
        # Apply maximum discount cap
        if self.maximum_discount:
            discount = min(discount, self.maximum_discount)
        
        return discount


class PromotionUsage(BaseModel):
    """Track promotion usage."""
    
    promotion = models.ForeignKey(
        Promotion,
        on_delete=models.CASCADE,
        related_name='usages'
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='promotion_usages'
    )
    order = models.ForeignKey(
        'orders.Order',
        on_delete=models.CASCADE,
        related_name='promotion_usages'
    )
    discount_applied = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.promotion.code} - {self.order.order_number}"


class LoyaltyProgram(BaseModel):
    """Loyalty program configuration."""
    
    restaurant = models.OneToOneField(
        'restaurants.Restaurant',
        on_delete=models.CASCADE,
        related_name='loyalty_program'
    )
    
    name = models.CharField(max_length=200, default='Rewards Program')
    description = models.TextField(blank=True)
    
    # Points configuration
    points_per_dollar = models.PositiveIntegerField(default=1)
    points_per_visit = models.PositiveIntegerField(default=0)
    signup_bonus = models.PositiveIntegerField(default=0)
    referral_bonus = models.PositiveIntegerField(default=0)
    birthday_bonus = models.PositiveIntegerField(default=0)
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['restaurant__name']
    
    def __str__(self):
        return f"{self.restaurant.name} - {self.name}"


class LoyaltyTier(BaseModel):
    """Loyalty program tiers."""
    
    program = models.ForeignKey(
        LoyaltyProgram,
        on_delete=models.CASCADE,
        related_name='tiers'
    )
    
    name = models.CharField(max_length=100)
    min_points = models.PositiveIntegerField(default=0)
    color = models.CharField(max_length=7, default='#3B82F6')
    icon = models.CharField(max_length=50, blank=True)
    
    # Benefits
    points_multiplier = models.DecimalField(max_digits=3, decimal_places=2, default=1)
    discount_percentage = models.PositiveIntegerField(default=0)
    free_delivery = models.BooleanField(default=False)
    priority_support = models.BooleanField(default=False)
    exclusive_items = models.BooleanField(default=False)
    
    position = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['position']
    
    def __str__(self):
        return f"{self.program.restaurant.name} - {self.name}"


class LoyaltyReward(BaseModel):
    """Redeemable rewards."""
    
    program = models.ForeignKey(
        LoyaltyProgram,
        on_delete=models.CASCADE,
        related_name='rewards'
    )
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='rewards/', blank=True, null=True)
    
    points_required = models.PositiveIntegerField()
    
    # Reward type
    reward_type = models.CharField(max_length=20, choices=[
        ('free_item', 'Free Item'),
        ('discount', 'Discount'),
        ('free_delivery', 'Free Delivery'),
    ])
    
    # For free item rewards
    reward_item = models.ForeignKey(
        'menus.MenuItem',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    # For discount rewards
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_type = models.CharField(max_length=20, choices=[
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ], default='fixed')
    
    is_active = models.BooleanField(default=True)
    
    # Limits
    quantity_available = models.PositiveIntegerField(null=True, blank=True)
    quantity_redeemed = models.PositiveIntegerField(default=0)
    
    valid_until = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['points_required']
    
    def __str__(self):
        return f"{self.name} ({self.points_required} pts)"


class CustomerLoyalty(BaseModel):
    """Customer loyalty status."""
    
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='loyalty_memberships'
    )
    program = models.ForeignKey(
        LoyaltyProgram,
        on_delete=models.CASCADE,
        related_name='members'
    )
    
    points_balance = models.PositiveIntegerField(default=0)
    points_earned_total = models.PositiveIntegerField(default=0)
    points_redeemed_total = models.PositiveIntegerField(default=0)
    
    current_tier = models.ForeignKey(
        LoyaltyTier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    # Referral tracking
    referral_code = models.CharField(max_length=20, unique=True)
    referred_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='referrals'
    )
    
    joined_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['customer', 'program']
        ordering = ['-points_balance']
    
    def __str__(self):
        return f"{self.customer.email} - {self.program.name}"
    
    def save(self, *args, **kwargs):
        if not self.referral_code:
            import random
            import string
            self.referral_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        super().save(*args, **kwargs)
    
    def add_points(self, points, reason=''):
        """Add points and update tier."""
        self.points_balance += points
        self.points_earned_total += points
        self.save()
        
        # Update tier
        self.update_tier()
        
        # Create transaction record
        LoyaltyTransaction.objects.create(
            membership=self,
            transaction_type=LoyaltyTransaction.TransactionType.EARNED,
            points=points,
            description=reason
        )
    
    def redeem_points(self, points, reason=''):
        """Redeem points."""
        if points > self.points_balance:
            raise ValueError("Insufficient points")
        
        self.points_balance -= points
        self.points_redeemed_total += points
        self.save()
        
        LoyaltyTransaction.objects.create(
            membership=self,
            transaction_type=LoyaltyTransaction.TransactionType.REDEEMED,
            points=-points,
            description=reason
        )
    
    def update_tier(self):
        """Update customer tier based on total points earned."""
        tiers = self.program.tiers.order_by('-min_points')
        for tier in tiers:
            if self.points_earned_total >= tier.min_points:
                self.current_tier = tier
                self.save()
                break


class LoyaltyTransaction(BaseModel):
    """Loyalty points transactions."""
    
    class TransactionType(models.TextChoices):
        EARNED = 'earned', _('Points Earned')
        REDEEMED = 'redeemed', _('Points Redeemed')
        EXPIRED = 'expired', _('Points Expired')
        BONUS = 'bonus', _('Bonus Points')
        ADJUSTED = 'adjusted', _('Points Adjusted')
    
    membership = models.ForeignKey(
        CustomerLoyalty,
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    
    transaction_type = models.CharField(max_length=20, choices=TransactionType.choices)
    points = models.IntegerField()  # Positive for earned, negative for redeemed
    description = models.CharField(max_length=255, blank=True)
    
    # Related order
    order = models.ForeignKey(
        'orders.Order',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='loyalty_transactions'
    )
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.membership.customer.email} - {self.points} pts"
