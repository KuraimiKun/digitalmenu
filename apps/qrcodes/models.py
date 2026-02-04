"""QR Code models for menu access."""
import uuid
import qrcode
from io import BytesIO
from django.db import models
from django.conf import settings
from django.core.files.base import ContentFile
from apps.core.models import BaseModel


class QRCodeDesign(BaseModel):
    """Custom QR code design template."""
    
    restaurant = models.ForeignKey(
        'restaurants.Restaurant',
        on_delete=models.CASCADE,
        related_name='qr_designs'
    )
    name = models.CharField(max_length=100)
    
    # QR Code styling
    fill_color = models.CharField(max_length=7, default='#000000')
    back_color = models.CharField(max_length=7, default='#FFFFFF')
    
    # Logo overlay
    logo = models.ImageField(
        upload_to='qrcodes/logos/',
        blank=True,
        null=True
    )
    logo_size_percent = models.IntegerField(
        default=20,
        help_text='Logo size as percentage of QR code'
    )
    
    # Border/Frame
    border_size = models.IntegerField(default=4)
    
    # QR Code parameters
    error_correction = models.CharField(
        max_length=1,
        choices=[
            ('L', 'Low (~7%)'),
            ('M', 'Medium (~15%)'),
            ('Q', 'Quartile (~25%)'),
            ('H', 'High (~30%)'),
        ],
        default='H'
    )
    box_size = models.IntegerField(default=10)
    
    is_default = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-is_default', 'name']
    
    def __str__(self):
        return f"{self.restaurant.name} - {self.name}"
    
    def save(self, *args, **kwargs):
        if self.is_default:
            # Ensure only one default per restaurant
            QRCodeDesign.objects.filter(
                restaurant=self.restaurant,
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


class QRCode(BaseModel):
    """Generated QR codes for menu access."""
    
    TYPE_CHOICES = [
        ('menu', 'Menu Access'),
        ('table', 'Table Order'),
        ('location', 'Location Info'),
        ('review', 'Leave Review'),
        ('wifi', 'WiFi Access'),
        ('custom', 'Custom Link'),
    ]
    
    restaurant = models.ForeignKey(
        'restaurants.Restaurant',
        on_delete=models.CASCADE,
        related_name='qr_codes'
    )
    location = models.ForeignKey(
        'restaurants.Location',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='qr_codes'
    )
    
    name = models.CharField(max_length=100)
    qr_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='menu')
    
    # Target content
    menu = models.ForeignKey(
        'menus.Menu',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='qr_codes'
    )
    table = models.ForeignKey(
        'restaurants.Table',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='qr_codes'
    )
    custom_url = models.URLField(blank=True)
    
    # WiFi specific
    wifi_ssid = models.CharField(max_length=100, blank=True)
    wifi_password = models.CharField(max_length=100, blank=True)
    wifi_encryption = models.CharField(
        max_length=10,
        choices=[('WPA', 'WPA/WPA2'), ('WEP', 'WEP'), ('', 'None')],
        default='WPA',
        blank=True
    )
    
    # Design
    design = models.ForeignKey(
        QRCodeDesign,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    # Generated images
    qr_image = models.ImageField(upload_to='qrcodes/generated/', blank=True)
    qr_image_svg = models.FileField(upload_to='qrcodes/generated/', blank=True)
    
    # Short URL for tracking
    short_code = models.CharField(max_length=10, unique=True, blank=True)
    
    # Analytics
    scan_count = models.IntegerField(default=0)
    last_scanned_at = models.DateTimeField(null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'QR Code'
        verbose_name_plural = 'QR Codes'
    
    def __str__(self):
        return f"{self.restaurant.name} - {self.name}"
    
    def save(self, *args, **kwargs):
        if not self.short_code:
            self.short_code = self._generate_short_code()
        super().save(*args, **kwargs)
    
    def _generate_short_code(self):
        """Generate a unique short code."""
        import random
        import string
        while True:
            code = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
            if not QRCode.objects.filter(short_code=code).exists():
                return code
    
    def get_target_url(self):
        """Get the URL that this QR code points to."""
        from django.urls import reverse
        
        if self.qr_type == 'custom' and self.custom_url:
            return self.custom_url
        
        base_url = settings.FRONTEND_URL
        
        if self.qr_type == 'menu':
            return f"{base_url}/m/{self.short_code}"
        elif self.qr_type == 'table':
            return f"{base_url}/t/{self.short_code}"
        elif self.qr_type == 'location':
            return f"{base_url}/l/{self.short_code}"
        elif self.qr_type == 'review':
            return f"{base_url}/r/{self.short_code}"
        elif self.qr_type == 'wifi':
            return self._generate_wifi_string()
        
        return f"{base_url}/q/{self.short_code}"
    
    def _generate_wifi_string(self):
        """Generate WiFi QR code string."""
        encryption = self.wifi_encryption or 'nopass'
        return f"WIFI:T:{encryption};S:{self.wifi_ssid};P:{self.wifi_password};;"
    
    def generate_qr_image(self):
        """Generate QR code image."""
        design = self.design or QRCodeDesign(
            fill_color='#000000',
            back_color='#FFFFFF',
            error_correction='H',
            box_size=10,
            border_size=4
        )
        
        error_correction_map = {
            'L': qrcode.constants.ERROR_CORRECT_L,
            'M': qrcode.constants.ERROR_CORRECT_M,
            'Q': qrcode.constants.ERROR_CORRECT_Q,
            'H': qrcode.constants.ERROR_CORRECT_H,
        }
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=error_correction_map.get(
                design.error_correction, qrcode.constants.ERROR_CORRECT_H
            ),
            box_size=design.box_size,
            border=design.border_size,
        )
        
        qr.add_data(self.get_target_url())
        qr.make(fit=True)
        
        img = qr.make_image(
            fill_color=design.fill_color,
            back_color=design.back_color
        )
        
        # Add logo if design has one
        if design.logo:
            from PIL import Image
            logo = Image.open(design.logo.path)
            
            # Resize logo
            qr_width, qr_height = img.size
            logo_max_size = int(qr_width * design.logo_size_percent / 100)
            logo.thumbnail((logo_max_size, logo_max_size))
            
            # Calculate position
            logo_pos = (
                (qr_width - logo.size[0]) // 2,
                (qr_height - logo.size[1]) // 2
            )
            
            # Paste logo
            img = img.convert('RGBA')
            logo = logo.convert('RGBA')
            img.paste(logo, logo_pos, logo)
        
        # Save to file
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        filename = f"qr_{self.short_code}.png"
        self.qr_image.save(filename, ContentFile(buffer.getvalue()), save=False)
        
        return self.qr_image


class QRCodeScan(models.Model):
    """Track QR code scans for analytics."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    qr_code = models.ForeignKey(
        QRCode,
        on_delete=models.CASCADE,
        related_name='scans'
    )
    
    # Device info
    user_agent = models.TextField(blank=True)
    device_type = models.CharField(max_length=20, blank=True)
    browser = models.CharField(max_length=50, blank=True)
    os = models.CharField(max_length=50, blank=True)
    
    # Location
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    
    # Session
    session_id = models.CharField(max_length=100, blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    # Referrer
    referrer = models.URLField(blank=True)
    
    scanned_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-scanned_at']
        indexes = [
            models.Index(fields=['qr_code', '-scanned_at']),
            models.Index(fields=['-scanned_at']),
        ]


class QRCodeBatch(BaseModel):
    """Batch generation of QR codes (e.g., for all tables)."""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('generating', 'Generating'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    restaurant = models.ForeignKey(
        'restaurants.Restaurant',
        on_delete=models.CASCADE,
        related_name='qr_batches'
    )
    location = models.ForeignKey(
        'restaurants.Location',
        on_delete=models.CASCADE,
        related_name='qr_batches'
    )
    
    name = models.CharField(max_length=100)
    qr_type = models.CharField(max_length=20, choices=QRCode.TYPE_CHOICES)
    design = models.ForeignKey(
        QRCodeDesign,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    # For table QR codes
    generate_for_tables = models.BooleanField(default=False)
    
    # For custom range
    prefix = models.CharField(max_length=50, blank=True)
    start_number = models.IntegerField(default=1)
    count = models.IntegerField(default=10)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    generated_count = models.IntegerField(default=0)
    
    # Output
    download_file = models.FileField(
        upload_to='qrcodes/batches/',
        blank=True,
        null=True
    )
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'QR Code Batch'
        verbose_name_plural = 'QR Code Batches'
