"""Integrations admin configuration."""
from django.contrib import admin
from .models import (
    IntegrationProvider, RestaurantIntegration, DeliveryPlatformMenu,
    DeliveryOrder, WebhookEvent, POSIntegration, PaymentGatewayConfig,
    IntegrationLog
)


@admin.register(IntegrationProvider)
class IntegrationProviderAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'is_active', 'is_featured', 'supports_webhooks']
    list_filter = ['category', 'is_active', 'is_featured']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(RestaurantIntegration)
class RestaurantIntegrationAdmin(admin.ModelAdmin):
    list_display = [
        'restaurant', 'provider', 'status', 'last_sync_at',
        'connected_at', 'connected_by'
    ]
    list_filter = ['status', 'provider', 'provider__category']
    search_fields = ['restaurant__name', 'provider__name']
    readonly_fields = ['webhook_url', 'webhook_secret', 'connected_at']


@admin.register(DeliveryPlatformMenu)
class DeliveryPlatformMenuAdmin(admin.ModelAdmin):
    list_display = ['integration', 'menu', 'is_synced', 'last_synced_at']
    list_filter = ['is_synced']


@admin.register(DeliveryOrder)
class DeliveryOrderAdmin(admin.ModelAdmin):
    list_display = [
        'external_order_number', 'integration', 'location', 'status',
        'customer_name', 'total', 'created_at'
    ]
    list_filter = ['status', 'integration__provider', 'location']
    search_fields = ['external_order_number', 'customer_name', 'customer_phone']
    readonly_fields = ['raw_payload']


@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
    list_display = [
        'event_type', 'integration', 'status', 'retry_count',
        'created_at', 'processed_at'
    ]
    list_filter = ['status', 'event_type', 'integration__provider']
    readonly_fields = ['payload', 'headers']


@admin.register(POSIntegration)
class POSIntegrationAdmin(admin.ModelAdmin):
    list_display = ['integration', 'sync_sales', 'sync_inventory', 'last_sales_sync']


@admin.register(PaymentGatewayConfig)
class PaymentGatewayConfigAdmin(admin.ModelAdmin):
    list_display = [
        'integration', 'accept_credit_cards', 'accept_digital_wallets',
        'auto_capture'
    ]


@admin.register(IntegrationLog)
class IntegrationLogAdmin(admin.ModelAdmin):
    list_display = ['integration', 'level', 'action', 'message', 'duration_ms', 'created_at']
    list_filter = ['level', 'action', 'integration__provider']
    search_fields = ['message']
    readonly_fields = ['request_data', 'response_data']
