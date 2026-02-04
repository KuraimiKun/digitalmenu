"""
Restaurant models with multi-location support.
"""
from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField
from apps.core.models import BaseModel


class Restaurant(BaseModel):
    """Main restaurant entity - represents a restaurant brand/company."""
    
    class Status(models.TextChoices):
        ACTIVE = 'active', _('Active')
        INACTIVE = 'inactive', _('Inactive')
        SUSPENDED = 'suspended', _('Suspended')
        PENDING = 'pending', _('Pending Approval')
    
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, db_index=True)
    description = models.TextField(blank=True)
    
    # Branding
    logo = models.ImageField(upload_to='restaurants/logos/', blank=True, null=True)
    cover_image = models.ImageField(upload_to='restaurants/covers/', blank=True, null=True)
    primary_color = models.CharField(max_length=7, default='#3B82F6')  # Hex color
    secondary_color = models.CharField(max_length=7, default='#1E40AF')
    font_family = models.CharField(max_length=100, default='Inter')
    
    # Contact
    email = models.EmailField(blank=True)
    phone = PhoneNumberField(blank=True, null=True)
    website = models.URLField(blank=True)
    
    # Social Media
    facebook_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    twitter_url = models.URLField(blank=True)
    
    # Settings
    default_currency = models.CharField(max_length=3, default='USD')
    default_language = models.CharField(max_length=10, default='en')
    timezone = models.CharField(max_length=50, default='UTC')
    
    # Subscription & Ownership
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='owned_restaurants'
    )
    subscription = models.ForeignKey(
        'core.Subscription',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='restaurants'
    )
    
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    is_featured = models.BooleanField(default=False)
    
    # Ordering & Features
    ordering_enabled = models.BooleanField(default=True, help_text=_('Allow customers to place orders'))
    
    # Custom domain
    custom_domain = models.CharField(max_length=255, blank=True, unique=True, null=True)
    
    @property
    def is_active(self):
        """Check if restaurant is active based on status."""
        return self.status == self.Status.ACTIVE
    
    @property
    def currency_symbol(self):
        """Get the currency symbol for the restaurant."""
        symbols = {
            'USD': '$',
            'EUR': '€',
            'GBP': '£',
            'TRY': '₺',
            'JPY': '¥',
            'CAD': 'C$',
            'AUD': 'A$',
            'INR': '₹',
            'AED': 'د.إ',
            'SAR': '﷼',
        }
        return symbols.get(self.default_currency, self.default_currency)
    
    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['status']),
            models.Index(fields=['owner']),
        ]
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
            # Ensure uniqueness
            original_slug = self.slug
            counter = 1
            while Restaurant.objects.filter(slug=self.slug).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)


class Location(BaseModel):
    """Restaurant location - supports multi-location businesses."""
    
    class Status(models.TextChoices):
        OPEN = 'open', _('Open')
        CLOSED = 'closed', _('Closed')
        TEMPORARILY_CLOSED = 'temp_closed', _('Temporarily Closed')
        COMING_SOON = 'coming_soon', _('Coming Soon')
    
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name='locations'
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, db_index=True)
    
    # Address
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default='United States')
    
    # Coordinates for maps
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    # Contact
    phone = PhoneNumberField(blank=True, null=True)
    email = models.EmailField(blank=True)
    
    # Settings
    currency = models.CharField(max_length=3, blank=True)  # Override restaurant default
    language = models.CharField(max_length=10, blank=True)
    timezone = models.CharField(max_length=50, blank=True)
    
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    is_primary = models.BooleanField(default=False)
    
    # Features
    accepts_orders = models.BooleanField(default=True)
    accepts_reservations = models.BooleanField(default=False)
    has_delivery = models.BooleanField(default=False)
    has_pickup = models.BooleanField(default=True)
    has_dine_in = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['name']
        unique_together = ['restaurant', 'slug']
        indexes = [
            models.Index(fields=['restaurant', 'status']),
        ]
    
    def __str__(self):
        return f"{self.restaurant.name} - {self.name}"
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        # Inherit defaults from restaurant if not set
        if not self.currency:
            self.currency = self.restaurant.default_currency
        if not self.language:
            self.language = self.restaurant.default_language
        if not self.timezone:
            self.timezone = self.restaurant.timezone
        super().save(*args, **kwargs)
    
    @property
    def full_address(self):
        parts = [self.address_line1]
        if self.address_line2:
            parts.append(self.address_line2)
        parts.append(f"{self.city}, {self.state} {self.postal_code}")
        parts.append(self.country)
        return ', '.join(parts)


class OperatingHours(BaseModel):
    """Operating hours for a location."""
    
    class DayOfWeek(models.IntegerChoices):
        MONDAY = 0, _('Monday')
        TUESDAY = 1, _('Tuesday')
        WEDNESDAY = 2, _('Wednesday')
        THURSDAY = 3, _('Thursday')
        FRIDAY = 4, _('Friday')
        SATURDAY = 5, _('Saturday')
        SUNDAY = 6, _('Sunday')
    
    location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        related_name='operating_hours'
    )
    day_of_week = models.IntegerField(choices=DayOfWeek.choices)
    
    is_closed = models.BooleanField(default=False)
    open_time = models.TimeField(null=True, blank=True)
    close_time = models.TimeField(null=True, blank=True)
    
    # Support for multiple time slots (e.g., lunch and dinner)
    open_time_2 = models.TimeField(null=True, blank=True)
    close_time_2 = models.TimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['day_of_week']
        unique_together = ['location', 'day_of_week']
    
    def __str__(self):
        return f"{self.location.name} - {self.get_day_of_week_display()}"


class SpecialHours(BaseModel):
    """Special hours for holidays or events."""
    
    location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        related_name='special_hours'
    )
    date = models.DateField()
    name = models.CharField(max_length=100, blank=True)  # e.g., "Christmas Day"
    
    is_closed = models.BooleanField(default=False)
    open_time = models.TimeField(null=True, blank=True)
    close_time = models.TimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['date']
        unique_together = ['location', 'date']
    
    def __str__(self):
        return f"{self.location.name} - {self.date}"


class RestaurantStaff(BaseModel):
    """Staff members assigned to restaurants with roles."""
    
    class Role(models.TextChoices):
        OWNER = 'owner', _('Owner')
        MANAGER = 'manager', _('Manager')
        STAFF = 'staff', _('Staff')
    
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name='staff_members'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='restaurant_assignments'
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STAFF)
    
    # Location access (empty means all locations)
    locations = models.ManyToManyField(Location, blank=True, related_name='staff')
    
    is_active = models.BooleanField(default=True)
    invited_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['restaurant', 'user']
        ordering = ['role', 'user__first_name']
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.restaurant.name} ({self.role})"


class Table(BaseModel):
    """Tables at a location for dine-in ordering."""
    
    class Status(models.TextChoices):
        AVAILABLE = 'available', _('Available')
        OCCUPIED = 'occupied', _('Occupied')
        RESERVED = 'reserved', _('Reserved')
        UNAVAILABLE = 'unavailable', _('Unavailable')
    
    location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        related_name='tables'
    )
    number = models.CharField(max_length=20)
    name = models.CharField(max_length=100, blank=True)  # e.g., "Patio Table 1"
    capacity = models.PositiveIntegerField(default=4)
    
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.AVAILABLE)
    is_active = models.BooleanField(default=True)
    
    # Position for floor plan (optional)
    position_x = models.PositiveIntegerField(null=True, blank=True)
    position_y = models.PositiveIntegerField(null=True, blank=True)
    
    class Meta:
        ordering = ['number']
        unique_together = ['location', 'number']
    
    def __str__(self):
        return f"{self.location.name} - Table {self.number}"


class RestaurantTheme(BaseModel):
    """Comprehensive theme settings for restaurant menus."""
    
    class LayoutStyle(models.TextChoices):
        MODERN = 'modern', _('Modern Minimal')
        ELEGANT = 'elegant', _('Elegant & Luxurious')
        CASUAL = 'casual', _('Casual & Fun')
        CLASSIC = 'classic', _('Classic Traditional')
        DARK = 'dark', _('Dark Mode')
        VIBRANT = 'vibrant', _('Vibrant & Bold')
    
    class HeaderStyle(models.TextChoices):
        FULL_IMAGE = 'full_image', _('Full Width Image')
        SPLIT = 'split', _('Split Image & Text')
        MINIMAL = 'minimal', _('Minimal Logo Only')
        GRADIENT = 'gradient', _('Gradient Background')
        VIDEO = 'video', _('Video Background')
    
    class CardStyle(models.TextChoices):
        ELEVATED = 'elevated', _('Elevated Cards')
        FLAT = 'flat', _('Flat Design')
        BORDERED = 'bordered', _('Bordered Cards')
        GLASSMORPHISM = 'glassmorphism', _('Glass Effect')
        NEUMORPHISM = 'neumorphism', _('Soft 3D Effect')
    
    restaurant = models.OneToOneField(
        Restaurant,
        on_delete=models.CASCADE,
        related_name='theme'
    )
    
    # Layout & Style
    layout_style = models.CharField(
        max_length=20, 
        choices=LayoutStyle.choices, 
        default=LayoutStyle.MODERN
    )
    header_style = models.CharField(
        max_length=20,
        choices=HeaderStyle.choices,
        default=HeaderStyle.FULL_IMAGE
    )
    card_style = models.CharField(
        max_length=20,
        choices=CardStyle.choices,
        default=CardStyle.ELEVATED
    )
    
    # Colors - Primary Palette
    primary_color = models.CharField(max_length=7, default='#E11D48')  # Rose-600
    secondary_color = models.CharField(max_length=7, default='#1E293B')  # Slate-800
    accent_color = models.CharField(max_length=7, default='#F59E0B')  # Amber-500
    
    # Background Colors
    background_color = models.CharField(max_length=7, default='#FFFFFF')
    surface_color = models.CharField(max_length=7, default='#F8FAFC')  # Slate-50
    card_background = models.CharField(max_length=7, default='#FFFFFF')
    
    # Text Colors
    text_primary = models.CharField(max_length=7, default='#0F172A')  # Slate-900
    text_secondary = models.CharField(max_length=7, default='#64748B')  # Slate-500
    text_on_primary = models.CharField(max_length=7, default='#FFFFFF')
    
    # Typography
    heading_font = models.CharField(max_length=100, default='Playfair Display')
    body_font = models.CharField(max_length=100, default='Inter')
    price_font = models.CharField(max_length=100, default='DM Sans')
    
    # Font Sizes
    heading_size = models.CharField(max_length=10, default='2.5rem')
    subheading_size = models.CharField(max_length=10, default='1.5rem')
    body_size = models.CharField(max_length=10, default='1rem')
    
    # Spacing & Radius
    border_radius = models.CharField(max_length=10, default='1rem')
    card_shadow = models.CharField(max_length=100, default='0 4px 20px rgba(0,0,0,0.08)')
    
    # Hero Section
    hero_image = models.ImageField(upload_to='themes/heroes/', blank=True, null=True)
    hero_video_url = models.URLField(blank=True)
    hero_overlay_opacity = models.PositiveIntegerField(default=40)  # 0-100
    hero_text_color = models.CharField(max_length=7, default='#FFFFFF')
    hero_height = models.CharField(max_length=10, default='60vh')
    
    # Display Options
    show_prices = models.BooleanField(default=True)
    show_images = models.BooleanField(default=True)
    show_descriptions = models.BooleanField(default=True)
    show_allergens = models.BooleanField(default=True)
    show_calories = models.BooleanField(default=False)
    show_dietary_badges = models.BooleanField(default=True)
    show_popular_badge = models.BooleanField(default=True)
    show_search = models.BooleanField(default=True)
    show_category_images = models.BooleanField(default=True)
    
    # Animation & Effects
    enable_animations = models.BooleanField(default=True)
    animation_style = models.CharField(max_length=20, default='fade-up')
    enable_parallax = models.BooleanField(default=False)
    enable_smooth_scroll = models.BooleanField(default=True)
    
    # Cart & Ordering
    enable_cart = models.BooleanField(default=True)
    cart_position = models.CharField(max_length=20, default='bottom-right')
    floating_cart_button = models.BooleanField(default=True)
    
    # Social & Contact
    show_social_links = models.BooleanField(default=True)
    show_contact_info = models.BooleanField(default=True)
    show_location_map = models.BooleanField(default=False)
    
    # Custom CSS/JS
    custom_css = models.TextField(blank=True)
    custom_header_html = models.TextField(blank=True)
    custom_footer_html = models.TextField(blank=True)
    
    # Presets
    preset_name = models.CharField(max_length=50, blank=True)
    
    class Meta:
        verbose_name = 'Restaurant Theme'
        verbose_name_plural = 'Restaurant Themes'
    
    def __str__(self):
        return f"{self.restaurant.name} Theme"
    
    def get_google_fonts_url(self):
        """Generate Google Fonts URL for the selected fonts."""
        fonts = set([self.heading_font, self.body_font, self.price_font])
        font_families = []
        for font in fonts:
            if font and font not in ['Inter', 'system-ui']:
                font_families.append(font.replace(' ', '+') + ':wght@300;400;500;600;700')
        
        if font_families:
            return f"https://fonts.googleapis.com/css2?family={'&family='.join(font_families)}&display=swap"
        return ""
    
    @classmethod
    def get_preset(cls, preset_name):
        """Return preset theme settings."""
        presets = {
            'modern_minimal': {
                'layout_style': 'modern',
                'header_style': 'minimal',
                'card_style': 'elevated',
                'primary_color': '#0F172A',
                'secondary_color': '#64748B',
                'accent_color': '#3B82F6',
                'heading_font': 'Inter',
                'body_font': 'Inter',
            },
            'elegant_luxury': {
                'layout_style': 'elegant',
                'header_style': 'full_image',
                'card_style': 'bordered',
                'primary_color': '#B8860B',
                'secondary_color': '#1A1A1A',
                'accent_color': '#D4AF37',
                'heading_font': 'Playfair Display',
                'body_font': 'Cormorant Garamond',
                'border_radius': '0.25rem',
            },
            'casual_fun': {
                'layout_style': 'casual',
                'header_style': 'gradient',
                'card_style': 'flat',
                'primary_color': '#FF6B6B',
                'secondary_color': '#4ECDC4',
                'accent_color': '#FFE66D',
                'heading_font': 'Fredoka One',
                'body_font': 'Nunito',
                'border_radius': '1.5rem',
            },
            'dark_mode': {
                'layout_style': 'dark',
                'header_style': 'minimal',
                'card_style': 'glassmorphism',
                'primary_color': '#818CF8',
                'secondary_color': '#A78BFA',
                'accent_color': '#34D399',
                'background_color': '#0F172A',
                'surface_color': '#1E293B',
                'card_background': '#334155',
                'text_primary': '#F8FAFC',
                'text_secondary': '#94A3B8',
                'heading_font': 'Space Grotesk',
                'body_font': 'Inter',
            },
            'vibrant_bold': {
                'layout_style': 'vibrant',
                'header_style': 'gradient',
                'card_style': 'neumorphism',
                'primary_color': '#EC4899',
                'secondary_color': '#8B5CF6',
                'accent_color': '#06B6D4',
                'heading_font': 'Montserrat',
                'body_font': 'Poppins',
            },
        }
        return presets.get(preset_name, {})
