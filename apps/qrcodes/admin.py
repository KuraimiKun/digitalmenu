"""QR Codes admin configuration."""
from django.contrib import admin
from .models import QRCodeDesign, QRCode, QRCodeScan, QRCodeBatch


@admin.register(QRCodeDesign)
class QRCodeDesignAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'restaurant', 'fill_color', 'back_color',
        'is_default', 'created_at'
    ]
    list_filter = ['is_default', 'restaurant']
    search_fields = ['name', 'restaurant__name']


@admin.register(QRCode)
class QRCodeAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'restaurant', 'location', 'qr_type', 'short_code',
        'scan_count', 'is_active', 'created_at'
    ]
    list_filter = ['qr_type', 'is_active', 'restaurant', 'location']
    search_fields = ['name', 'short_code']
    readonly_fields = ['short_code', 'scan_count', 'last_scanned_at']
    
    fieldsets = (
        (None, {
            'fields': ('restaurant', 'location', 'name', 'qr_type', 'is_active')
        }),
        ('Target', {
            'fields': ('menu', 'table', 'custom_url')
        }),
        ('WiFi Settings', {
            'fields': ('wifi_ssid', 'wifi_password', 'wifi_encryption'),
            'classes': ('collapse',)
        }),
        ('Design', {
            'fields': ('design', 'qr_image', 'qr_image_svg')
        }),
        ('Analytics', {
            'fields': ('short_code', 'scan_count', 'last_scanned_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(QRCodeScan)
class QRCodeScanAdmin(admin.ModelAdmin):
    list_display = [
        'qr_code', 'device_type', 'browser', 'country', 'city', 'scanned_at'
    ]
    list_filter = ['device_type', 'country', 'scanned_at']
    search_fields = ['qr_code__name', 'qr_code__short_code']
    readonly_fields = [
        'qr_code', 'user_agent', 'device_type', 'browser', 'os',
        'ip_address', 'country', 'city', 'scanned_at'
    ]


@admin.register(QRCodeBatch)
class QRCodeBatchAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'restaurant', 'location', 'qr_type', 'status',
        'generated_count', 'created_at'
    ]
    list_filter = ['status', 'qr_type', 'restaurant']
    search_fields = ['name']
    readonly_fields = ['status', 'generated_count', 'download_file']
