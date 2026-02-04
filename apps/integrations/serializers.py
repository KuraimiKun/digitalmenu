"""Integration serializers."""
from rest_framework import serializers
from .models import (
    IntegrationProvider, RestaurantIntegration, DeliveryPlatformMenu,
    DeliveryOrder, WebhookEvent, POSIntegration, PaymentGatewayConfig,
    IntegrationLog
)


class IntegrationProviderSerializer(serializers.ModelSerializer):
    """Serializer for integration providers."""
    
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    
    class Meta:
        model = IntegrationProvider
        fields = [
            'id', 'name', 'slug', 'category', 'category_display',
            'description', 'logo', 'website_url', 'documentation_url',
            'required_fields', 'optional_fields', 'supports_webhooks',
            'webhook_events', 'is_featured'
        ]


class RestaurantIntegrationSerializer(serializers.ModelSerializer):
    """Serializer for restaurant integrations."""
    
    provider = IntegrationProviderSerializer(read_only=True)
    provider_id = serializers.UUIDField(write_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    connected_by_name = serializers.CharField(
        source='connected_by.get_full_name', read_only=True
    )
    
    class Meta:
        model = RestaurantIntegration
        fields = [
            'id', 'restaurant', 'provider', 'provider_id', 'status',
            'status_display', 'configuration', 'sync_menu', 'sync_prices',
            'sync_availability', 'price_markup_percentage', 'location_mappings',
            'last_sync_at', 'last_sync_status', 'webhook_url',
            'connected_by_name', 'connected_at', 'created_at'
        ]
        read_only_fields = [
            'id', 'restaurant', 'status', 'last_sync_at', 'last_sync_status',
            'webhook_url', 'connected_at', 'created_at'
        ]
    
    def create(self, validated_data):
        provider_id = validated_data.pop('provider_id')
        validated_data['provider_id'] = provider_id
        validated_data['restaurant'] = self.context['restaurant']
        validated_data['connected_by'] = self.context['request'].user
        return super().create(validated_data)


class IntegrationCredentialsSerializer(serializers.Serializer):
    """Serializer for updating integration credentials."""
    
    credentials = serializers.JSONField()
    
    def validate_credentials(self, value):
        integration = self.context.get('integration')
        if integration:
            provider = integration.provider
            for field in provider.required_fields:
                if field not in value:
                    raise serializers.ValidationError(
                        f"Missing required field: {field}"
                    )
        return value


class DeliveryPlatformMenuSerializer(serializers.ModelSerializer):
    """Serializer for delivery platform menus."""
    
    menu_name = serializers.CharField(source='menu.name', read_only=True)
    
    class Meta:
        model = DeliveryPlatformMenu
        fields = [
            'id', 'integration', 'menu', 'menu_name', 'external_menu_id',
            'is_synced', 'last_synced_at', 'synced_items', 'sync_errors'
        ]
        read_only_fields = [
            'id', 'external_menu_id', 'is_synced', 'last_synced_at',
            'synced_items', 'sync_errors'
        ]


class DeliveryOrderSerializer(serializers.ModelSerializer):
    """Serializer for delivery orders."""
    
    provider_name = serializers.CharField(
        source='integration.provider.name', read_only=True
    )
    location_name = serializers.CharField(source='location.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = DeliveryOrder
        fields = [
            'id', 'integration', 'provider_name', 'location', 'location_name',
            'external_order_id', 'external_order_number', 'status', 'status_display',
            'customer_name', 'customer_phone', 'delivery_address',
            'special_instructions', 'items', 'subtotal', 'delivery_fee',
            'platform_fee', 'tax', 'tip', 'total', 'estimated_pickup_time',
            'estimated_delivery_time', 'actual_pickup_time', 'internal_order',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class DeliveryOrderStatusUpdateSerializer(serializers.Serializer):
    """Serializer for updating delivery order status."""
    
    status = serializers.ChoiceField(choices=DeliveryOrder.STATUS_CHOICES)
    
    def validate_status(self, value):
        order = self.context.get('order')
        if order:
            valid_transitions = {
                'received': ['confirmed', 'cancelled'],
                'confirmed': ['preparing', 'cancelled'],
                'preparing': ['ready', 'cancelled'],
                'ready': ['picked_up'],
                'picked_up': ['delivered'],
            }
            if value not in valid_transitions.get(order.status, []):
                raise serializers.ValidationError(
                    f"Cannot transition from {order.status} to {value}"
                )
        return value


class WebhookEventSerializer(serializers.ModelSerializer):
    """Serializer for webhook events."""
    
    class Meta:
        model = WebhookEvent
        fields = [
            'id', 'integration', 'event_type', 'event_id', 'status',
            'processed_at', 'error_message', 'retry_count', 'created_at'
        ]


class POSIntegrationSerializer(serializers.ModelSerializer):
    """Serializer for POS integration config."""
    
    class Meta:
        model = POSIntegration
        fields = [
            'id', 'integration', 'terminals', 'sync_sales', 'sync_inventory',
            'sync_employees', 'item_mappings', 'category_mappings',
            'modifier_mappings', 'last_sales_sync', 'last_inventory_sync'
        ]
        read_only_fields = ['id', 'last_sales_sync', 'last_inventory_sync']


class PaymentGatewayConfigSerializer(serializers.ModelSerializer):
    """Serializer for payment gateway config."""
    
    class Meta:
        model = PaymentGatewayConfig
        fields = [
            'id', 'integration', 'accept_credit_cards', 'accept_debit_cards',
            'accept_digital_wallets', 'auto_capture', 'capture_delay_hours',
            'stripe_account_id', 'stripe_publishable_key', 'square_location_id',
            'pass_processing_fee_to_customer', 'processing_fee_percentage',
            'processing_fee_fixed'
        ]
        read_only_fields = ['id']
        extra_kwargs = {
            'stripe_publishable_key': {'write_only': True},
        }


class IntegrationLogSerializer(serializers.ModelSerializer):
    """Serializer for integration logs."""
    
    class Meta:
        model = IntegrationLog
        fields = [
            'id', 'level', 'action', 'message', 'duration_ms', 'created_at'
        ]
