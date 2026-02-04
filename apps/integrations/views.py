"""Integration views."""
import hmac
import hashlib
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from apps.core.permissions import IsRestaurantOwner, IsRestaurantManager
from .models import (
    IntegrationProvider, RestaurantIntegration, DeliveryPlatformMenu,
    DeliveryOrder, WebhookEvent, IntegrationLog
)
from .serializers import (
    IntegrationProviderSerializer, RestaurantIntegrationSerializer,
    IntegrationCredentialsSerializer, DeliveryPlatformMenuSerializer,
    DeliveryOrderSerializer, DeliveryOrderStatusUpdateSerializer,
    WebhookEventSerializer, IntegrationLogSerializer
)


class IntegrationProviderViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for browsing available integration providers."""
    
    queryset = IntegrationProvider.objects.filter(is_active=True)
    serializer_class = IntegrationProviderSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['category', 'is_featured']
    search_fields = ['name', 'description']
    
    @action(detail=True, methods=['get'])
    def setup_instructions(self, request, pk=None):
        """Get setup instructions for a provider."""
        provider = self.get_object()
        return Response({
            'provider': provider.name,
            'required_fields': provider.required_fields,
            'optional_fields': provider.optional_fields,
            'documentation_url': provider.documentation_url,
            'webhook_events': provider.webhook_events if provider.supports_webhooks else [],
        })


class RestaurantIntegrationViewSet(viewsets.ModelViewSet):
    """ViewSet for managing restaurant integrations."""
    
    serializer_class = RestaurantIntegrationSerializer
    permission_classes = [IsAuthenticated, IsRestaurantOwner | IsRestaurantManager]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'provider__category']
    
    def get_queryset(self):
        return RestaurantIntegration.objects.filter(
            restaurant_id=self.kwargs['restaurant_pk']
        ).select_related('provider', 'connected_by')
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        from apps.restaurants.models import Restaurant
        context['restaurant'] = get_object_or_404(
            Restaurant, pk=self.kwargs['restaurant_pk']
        )
        return context
    
    @action(detail=True, methods=['post'])
    def credentials(self, request, restaurant_pk=None, pk=None):
        """Update integration credentials."""
        integration = self.get_object()
        serializer = IntegrationCredentialsSerializer(
            data=request.data,
            context={'integration': integration}
        )
        serializer.is_valid(raise_exception=True)
        
        # In production, encrypt credentials before saving
        integration.credentials = serializer.validated_data['credentials']
        integration.status = 'pending'
        integration.save()
        
        return Response({'status': 'credentials_updated'})
    
    @action(detail=True, methods=['post'])
    def connect(self, request, restaurant_pk=None, pk=None):
        """Activate the integration connection."""
        integration = self.get_object()
        
        # Validate credentials are set
        if not integration.credentials:
            return Response(
                {'error': 'Credentials must be set before connecting'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # TODO: Test connection with provider API
        integration.status = 'active'
        integration.connected_at = timezone.now()
        integration.save()
        
        # Generate webhook URL if supported
        if integration.provider.supports_webhooks:
            integration.webhook_url = request.build_absolute_uri(
                f'/api/webhooks/{integration.id}/'
            )
            integration.webhook_secret = hmac.new(
                integration.id.bytes,
                msg=b'webhook_secret',
                digestmod=hashlib.sha256
            ).hexdigest()[:32]
            integration.save()
        
        return Response({
            'status': 'connected',
            'webhook_url': integration.webhook_url if integration.provider.supports_webhooks else None
        })
    
    @action(detail=True, methods=['post'])
    def disconnect(self, request, restaurant_pk=None, pk=None):
        """Disconnect the integration."""
        integration = self.get_object()
        integration.status = 'disconnected'
        integration.save()
        
        return Response({'status': 'disconnected'})
    
    @action(detail=True, methods=['post'])
    def sync(self, request, restaurant_pk=None, pk=None):
        """Trigger a manual sync with the integration."""
        integration = self.get_object()
        
        if integration.status != 'active':
            return Response(
                {'error': 'Integration must be active to sync'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # TODO: Trigger async sync task
        from .tasks import sync_integration
        sync_integration.delay(str(integration.id))
        
        return Response({'status': 'sync_started'})
    
    @action(detail=True, methods=['get'])
    def logs(self, request, restaurant_pk=None, pk=None):
        """Get recent logs for this integration."""
        integration = self.get_object()
        logs = integration.logs.all()[:100]
        serializer = IntegrationLogSerializer(logs, many=True)
        return Response(serializer.data)


class DeliveryPlatformMenuViewSet(viewsets.ModelViewSet):
    """ViewSet for managing delivery platform menus."""
    
    serializer_class = DeliveryPlatformMenuSerializer
    permission_classes = [IsAuthenticated, IsRestaurantOwner | IsRestaurantManager]
    
    def get_queryset(self):
        return DeliveryPlatformMenu.objects.filter(
            integration_id=self.kwargs['integration_pk'],
            integration__restaurant_id=self.kwargs['restaurant_pk']
        ).select_related('menu')
    
    @action(detail=True, methods=['post'])
    def sync(self, request, restaurant_pk=None, integration_pk=None, pk=None):
        """Sync menu to delivery platform."""
        delivery_menu = self.get_object()
        
        # TODO: Trigger async menu sync
        from .tasks import sync_delivery_menu
        sync_delivery_menu.delay(str(delivery_menu.id))
        
        return Response({'status': 'sync_started'})


class DeliveryOrderViewSet(viewsets.ModelViewSet):
    """ViewSet for managing delivery orders."""
    
    serializer_class = DeliveryOrderSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'location', 'integration']
    search_fields = ['customer_name', 'external_order_number']
    ordering_fields = ['created_at', 'total']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return DeliveryOrder.objects.filter(
            integration__restaurant_id=self.kwargs['restaurant_pk']
        ).select_related('integration__provider', 'location')
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, restaurant_pk=None, pk=None):
        """Update delivery order status."""
        order = self.get_object()
        serializer = DeliveryOrderStatusUpdateSerializer(
            data=request.data,
            context={'order': order}
        )
        serializer.is_valid(raise_exception=True)
        
        old_status = order.status
        order.status = serializer.validated_data['status']
        
        if order.status == 'picked_up':
            order.actual_pickup_time = timezone.now()
        
        order.save()
        
        # TODO: Notify delivery platform of status change
        from .tasks import notify_platform_status_change
        notify_platform_status_change.delay(
            str(order.id), old_status, order.status
        )
        
        return Response({
            'status': order.status,
            'status_display': order.get_status_display()
        })


@api_view(['POST'])
@permission_classes([AllowAny])
def webhook_receiver(request, integration_id):
    """Receive webhooks from integration providers."""
    try:
        integration = RestaurantIntegration.objects.get(pk=integration_id)
    except RestaurantIntegration.DoesNotExist:
        return HttpResponse(status=404)
    
    # Verify webhook signature if configured
    if integration.webhook_secret:
        signature = request.headers.get('X-Webhook-Signature', '')
        expected = hmac.new(
            integration.webhook_secret.encode(),
            msg=request.body,
            digestmod=hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected):
            return HttpResponse(status=401)
    
    # Create webhook event record
    event = WebhookEvent.objects.create(
        integration=integration,
        event_type=request.headers.get('X-Event-Type', 'unknown'),
        event_id=request.headers.get('X-Event-ID', ''),
        payload=request.data if hasattr(request, 'data') else {},
        headers=dict(request.headers),
        status='pending'
    )
    
    # Process webhook asynchronously
    from .tasks import process_webhook
    process_webhook.delay(str(event.id))
    
    return HttpResponse(status=200)
