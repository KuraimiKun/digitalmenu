"""
Menu models with drag-and-drop builder support.
"""
from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from apps.core.models import BaseModel


class MenuTheme(BaseModel):
    """Pre-built themes for menu customization."""
    
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    preview_image = models.ImageField(upload_to='themes/previews/', blank=True, null=True)
    
    # Theme styles (JSON)
    styles = models.JSONField(default=dict)
    
    # Colors
    primary_color = models.CharField(max_length=7, default='#3B82F6')
    secondary_color = models.CharField(max_length=7, default='#1E40AF')
    background_color = models.CharField(max_length=7, default='#FFFFFF')
    text_color = models.CharField(max_length=7, default='#1F2937')
    accent_color = models.CharField(max_length=7, default='#10B981')
    
    # Typography
    heading_font = models.CharField(max_length=100, default='Playfair Display')
    body_font = models.CharField(max_length=100, default='Inter')
    
    is_premium = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Menu(BaseModel):
    """Menu entity with customization options."""
    
    class Status(models.TextChoices):
        DRAFT = 'draft', _('Draft')
        PUBLISHED = 'published', _('Published')
        ARCHIVED = 'archived', _('Archived')
    
    class MenuType(models.TextChoices):
        STANDARD = 'standard', _('Standard Menu')
        BREAKFAST = 'breakfast', _('Breakfast')
        LUNCH = 'lunch', _('Lunch')
        DINNER = 'dinner', _('Dinner')
        DRINKS = 'drinks', _('Drinks')
        DESSERTS = 'desserts', _('Desserts')
        SPECIALS = 'specials', _('Daily Specials')
        KIDS = 'kids', _('Kids Menu')
        CATERING = 'catering', _('Catering')
    
    restaurant = models.ForeignKey(
        'restaurants.Restaurant',
        on_delete=models.CASCADE,
        related_name='menus'
    )
    locations = models.ManyToManyField(
        'restaurants.Location',
        blank=True,
        related_name='menus'
    )
    
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, db_index=True)
    description = models.TextField(blank=True)
    
    menu_type = models.CharField(max_length=20, choices=MenuType.choices, default=MenuType.STANDARD)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    
    # Theme & Customization
    theme = models.ForeignKey(
        MenuTheme,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    custom_styles = models.JSONField(default=dict, blank=True)
    
    # Images
    header_image = models.ImageField(upload_to='menus/headers/', blank=True, null=True)
    background_image = models.ImageField(upload_to='menus/backgrounds/', blank=True, null=True)
    
    # Availability
    is_active = models.BooleanField(default=True)
    available_from = models.TimeField(null=True, blank=True)
    available_until = models.TimeField(null=True, blank=True)
    available_days = models.JSONField(default=list)  # [0,1,2,3,4,5,6] for all days
    
    # Ordering
    position = models.PositiveIntegerField(default=0)
    
    # Layout configuration for drag-and-drop builder
    layout_config = models.JSONField(default=dict)
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_menus'
    )
    
    class Meta:
        ordering = ['position', 'name']
        unique_together = ['restaurant', 'slug']
    
    def __str__(self):
        return f"{self.restaurant.name} - {self.name}"
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Category(BaseModel):
    """Menu category (e.g., Appetizers, Main Course)."""
    
    menu = models.ForeignKey(
        Menu,
        on_delete=models.CASCADE,
        related_name='categories'
    )
    
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='menus/categories/', blank=True, null=True)
    
    # Display options
    position = models.PositiveIntegerField(default=0)
    is_visible = models.BooleanField(default=True)
    
    # Availability
    available_from = models.TimeField(null=True, blank=True)
    available_until = models.TimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['position', 'name']
        unique_together = ['menu', 'slug']
        verbose_name_plural = 'categories'
    
    def __str__(self):
        return f"{self.menu.name} - {self.name}"
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class MenuItem(BaseModel):
    """Individual menu item with full details."""
    
    class Status(models.TextChoices):
        AVAILABLE = 'available', _('Available')
        OUT_OF_STOCK = 'out_of_stock', _('Out of Stock')
        HIDDEN = 'hidden', _('Hidden')
        COMING_SOON = 'coming_soon', _('Coming Soon')
    
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='items'
    )
    
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220)
    description = models.TextField(blank=True)
    
    # Pricing
    price = models.DecimalField(max_digits=10, decimal_places=2)
    compare_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, blank=True)  # Override if different from restaurant
    
    # Images
    image = models.ImageField(upload_to='menus/items/', blank=True, null=True)
    thumbnail = models.ImageField(upload_to='menus/items/thumbs/', blank=True, null=True)
    gallery = models.JSONField(default=list)  # List of image URLs
    
    # Status & Availability
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.AVAILABLE)
    is_featured = models.BooleanField(default=False)
    is_new = models.BooleanField(default=False)
    is_popular = models.BooleanField(default=False)
    is_spicy = models.BooleanField(default=False)
    spicy_level = models.PositiveSmallIntegerField(default=0)  # 0-5
    
    # Dietary information
    is_vegetarian = models.BooleanField(default=False)
    is_vegan = models.BooleanField(default=False)
    is_gluten_free = models.BooleanField(default=False)
    is_halal = models.BooleanField(default=False)
    is_kosher = models.BooleanField(default=False)
    
    # Allergens
    allergens = models.JSONField(default=list)  # List of allergen identifiers
    
    # Nutritional info
    calories = models.PositiveIntegerField(null=True, blank=True)
    nutritional_info = models.JSONField(default=dict)
    
    # Preparation
    prep_time = models.PositiveIntegerField(null=True, blank=True)  # Minutes
    
    # Inventory tracking
    track_inventory = models.BooleanField(default=False)
    inventory_count = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(default=5)
    
    # Display
    position = models.PositiveIntegerField(default=0)
    
    # Tags for filtering
    tags = models.JSONField(default=list)
    
    class Meta:
        ordering = ['position', 'name']
        unique_together = ['category', 'slug']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        if not self.currency:
            self.currency = self.category.menu.restaurant.default_currency
        super().save(*args, **kwargs)
    
    @property
    def is_on_sale(self):
        return self.compare_price is not None and self.compare_price > self.price
    
    @property
    def discount_percentage(self):
        if self.is_on_sale:
            return round((1 - self.price / self.compare_price) * 100)
        return 0


class MenuItemVariant(BaseModel):
    """Variants for menu items (e.g., sizes, flavors)."""
    
    item = models.ForeignKey(
        MenuItem,
        on_delete=models.CASCADE,
        related_name='variants'
    )
    
    name = models.CharField(max_length=100)  # e.g., "Small", "Large"
    price_adjustment = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    is_default = models.BooleanField(default=False)
    is_available = models.BooleanField(default=True)
    
    position = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['position', 'name']
    
    def __str__(self):
        return f"{self.item.name} - {self.name}"
    
    @property
    def total_price(self):
        return self.item.price + self.price_adjustment


class ModifierGroup(BaseModel):
    """Groups of modifiers (e.g., "Toppings", "Sauces")."""
    
    class SelectionType(models.TextChoices):
        SINGLE = 'single', _('Single Selection')
        MULTIPLE = 'multiple', _('Multiple Selection')
    
    restaurant = models.ForeignKey(
        'restaurants.Restaurant',
        on_delete=models.CASCADE,
        related_name='modifier_groups'
    )
    
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    selection_type = models.CharField(max_length=20, choices=SelectionType.choices, default=SelectionType.SINGLE)
    is_required = models.BooleanField(default=False)
    min_selections = models.PositiveIntegerField(default=0)
    max_selections = models.PositiveIntegerField(default=10)
    
    position = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['position', 'name']
    
    def __str__(self):
        return self.name


class Modifier(BaseModel):
    """Individual modifier options."""
    
    group = models.ForeignKey(
        ModifierGroup,
        on_delete=models.CASCADE,
        related_name='modifiers'
    )
    
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    is_default = models.BooleanField(default=False)
    is_available = models.BooleanField(default=True)
    
    # Inventory
    track_inventory = models.BooleanField(default=False)
    inventory_count = models.PositiveIntegerField(default=0)
    
    position = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['position', 'name']
    
    def __str__(self):
        return f"{self.group.name} - {self.name}"


class MenuItemModifierGroup(BaseModel):
    """Link between menu items and modifier groups."""
    
    item = models.ForeignKey(
        MenuItem,
        on_delete=models.CASCADE,
        related_name='modifier_groups'
    )
    group = models.ForeignKey(
        ModifierGroup,
        on_delete=models.CASCADE,
        related_name='menu_items'
    )
    
    is_required = models.BooleanField(null=True)  # Override group default
    min_selections = models.PositiveIntegerField(null=True)
    max_selections = models.PositiveIntegerField(null=True)
    
    position = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['position']
        unique_together = ['item', 'group']
    
    def __str__(self):
        return f"{self.item.name} - {self.group.name}"


class MenuTranslation(BaseModel):
    """Multi-language support for menus."""
    
    menu = models.ForeignKey(
        Menu,
        on_delete=models.CASCADE,
        related_name='translations'
    )
    language = models.CharField(max_length=10)
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['menu', 'language']
    
    def __str__(self):
        return f"{self.menu.name} ({self.language})"


class CategoryTranslation(BaseModel):
    """Multi-language support for categories."""
    
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='translations'
    )
    language = models.CharField(max_length=10)
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['category', 'language']


class MenuItemTranslation(BaseModel):
    """Multi-language support for menu items."""
    
    item = models.ForeignKey(
        MenuItem,
        on_delete=models.CASCADE,
        related_name='translations'
    )
    language = models.CharField(max_length=10)
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['item', 'language']
