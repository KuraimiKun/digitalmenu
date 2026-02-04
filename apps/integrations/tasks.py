"""Integration async tasks."""
from celery import shared_task
from django.utils import timezone


@shared_task
def sync_integration(integration_id):
    """Sync data with an integration provider."""
    from .models import RestaurantIntegration, IntegrationLog
    
    try:
        integration = RestaurantIntegration.objects.get(pk=integration_id)
    except RestaurantIntegration.DoesNotExist:
        return
    
    start_time = timezone.now()
    
    try:
        provider_slug = integration.provider.slug
        
        # Route to provider-specific sync logic
        if provider_slug == 'doordash':
            sync_doordash(integration)
        elif provider_slug == 'ubereats':
            sync_ubereats(integration)
        elif provider_slug == 'grubhub':
            sync_grubhub(integration)
        # Add more providers as needed
        
        integration.last_sync_at = timezone.now()
        integration.last_sync_status = 'success'
        integration.last_sync_message = 'Sync completed successfully'
        integration.save()
        
        IntegrationLog.objects.create(
            integration=integration,
            level='info',
            action='sync',
            message='Sync completed successfully',
            duration_ms=(timezone.now() - start_time).total_seconds() * 1000
        )
        
    except Exception as e:
        integration.last_sync_at = timezone.now()
        integration.last_sync_status = 'error'
        integration.last_sync_message = str(e)
        integration.save()
        
        IntegrationLog.objects.create(
            integration=integration,
            level='error',
            action='sync',
            message=str(e),
            duration_ms=(timezone.now() - start_time).total_seconds() * 1000
        )
        raise


@shared_task
def sync_delivery_menu(delivery_menu_id):
    """Sync a menu to a delivery platform."""
    from .models import DeliveryPlatformMenu, IntegrationLog
    
    try:
        delivery_menu = DeliveryPlatformMenu.objects.select_related(
            'integration', 'menu'
        ).get(pk=delivery_menu_id)
    except DeliveryPlatformMenu.DoesNotExist:
        return
    
    integration = delivery_menu.integration
    menu = delivery_menu.menu
    
    try:
        # Get menu items to sync
        items = menu.items.filter(is_available=True).select_related('category')
        
        # Build menu data for platform
        menu_data = {
            'name': menu.name,
            'categories': [],
        }
        
        categories = {}
        for item in items:
            cat_id = str(item.category_id)
            if cat_id not in categories:
                categories[cat_id] = {
                    'name': item.category.name,
                    'items': []
                }
            categories[cat_id]['items'].append({
                'id': str(item.id),
                'name': item.name,
                'description': item.description,
                'price': float(item.price),
                'image': item.image.url if item.image else None,
            })
        
        menu_data['categories'] = list(categories.values())
        
        # TODO: Send to platform API based on provider
        provider_slug = integration.provider.slug
        
        # Simulate API call
        external_ids = {}
        for item in items:
            external_ids[str(item.id)] = f"ext_{item.id}"
        
        delivery_menu.synced_items = external_ids
        delivery_menu.is_synced = True
        delivery_menu.last_synced_at = timezone.now()
        delivery_menu.sync_errors = []
        delivery_menu.save()
        
        IntegrationLog.objects.create(
            integration=integration,
            level='info',
            action='menu_sync',
            message=f'Synced {len(items)} items to {integration.provider.name}'
        )
        
    except Exception as e:
        delivery_menu.sync_errors.append({
            'timestamp': timezone.now().isoformat(),
            'error': str(e)
        })
        delivery_menu.save()
        
        IntegrationLog.objects.create(
            integration=integration,
            level='error',
            action='menu_sync',
            message=str(e)
        )
        raise


@shared_task
def process_webhook(event_id):
    """Process an incoming webhook event."""
    from .models import WebhookEvent, DeliveryOrder, IntegrationLog
    
    try:
        event = WebhookEvent.objects.select_related(
            'integration'
        ).get(pk=event_id)
    except WebhookEvent.DoesNotExist:
        return
    
    event.status = 'processing'
    event.save()
    
    try:
        provider_slug = event.integration.provider.slug
        event_type = event.event_type
        payload = event.payload
        
        # Route to handler based on event type
        if event_type == 'order.created':
            handle_new_order(event.integration, payload)
        elif event_type == 'order.updated':
            handle_order_update(event.integration, payload)
        elif event_type == 'order.cancelled':
            handle_order_cancellation(event.integration, payload)
        
        event.status = 'processed'
        event.processed_at = timezone.now()
        event.save()
        
    except Exception as e:
        event.status = 'failed'
        event.error_message = str(e)
        event.retry_count += 1
        event.save()
        
        IntegrationLog.objects.create(
            integration=event.integration,
            level='error',
            action='webhook_processing',
            message=f'Failed to process {event.event_type}: {e}'
        )
        raise


@shared_task
def notify_platform_status_change(order_id, old_status, new_status):
    """Notify delivery platform of order status change."""
    from .models import DeliveryOrder, IntegrationLog
    
    try:
        order = DeliveryOrder.objects.select_related(
            'integration'
        ).get(pk=order_id)
    except DeliveryOrder.DoesNotExist:
        return
    
    integration = order.integration
    
    try:
        # TODO: Call platform API to update status
        provider_slug = integration.provider.slug
        
        IntegrationLog.objects.create(
            integration=integration,
            level='info',
            action='status_update',
            message=f'Notified {integration.provider.name} of status change: {old_status} -> {new_status}'
        )
        
    except Exception as e:
        IntegrationLog.objects.create(
            integration=integration,
            level='error',
            action='status_update',
            message=f'Failed to notify platform: {e}'
        )
        raise


def handle_new_order(integration, payload):
    """Handle incoming order from delivery platform."""
    from .models import DeliveryOrder
    from apps.restaurants.models import Location
    
    # Extract order data from payload (format varies by provider)
    location = Location.objects.filter(
        restaurant=integration.restaurant
    ).first()
    
    order = DeliveryOrder.objects.create(
        integration=integration,
        location=location,
        external_order_id=payload.get('order_id', ''),
        external_order_number=payload.get('order_number', ''),
        customer_name=payload.get('customer', {}).get('name', ''),
        customer_phone=payload.get('customer', {}).get('phone', ''),
        delivery_address=payload.get('delivery_address', {}),
        special_instructions=payload.get('special_instructions', ''),
        items=payload.get('items', []),
        subtotal=payload.get('subtotal', 0),
        delivery_fee=payload.get('delivery_fee', 0),
        platform_fee=payload.get('platform_fee', 0),
        tax=payload.get('tax', 0),
        tip=payload.get('tip', 0),
        total=payload.get('total', 0),
        estimated_pickup_time=payload.get('estimated_pickup_time'),
        estimated_delivery_time=payload.get('estimated_delivery_time'),
        raw_payload=payload,
        status='received'
    )
    
    return order


def handle_order_update(integration, payload):
    """Handle order update from delivery platform."""
    from .models import DeliveryOrder
    
    try:
        order = DeliveryOrder.objects.get(
            integration=integration,
            external_order_id=payload.get('order_id')
        )
        
        # Update order fields
        if 'estimated_pickup_time' in payload:
            order.estimated_pickup_time = payload['estimated_pickup_time']
        if 'estimated_delivery_time' in payload:
            order.estimated_delivery_time = payload['estimated_delivery_time']
        
        order.save()
        
    except DeliveryOrder.DoesNotExist:
        pass


def handle_order_cancellation(integration, payload):
    """Handle order cancellation from delivery platform."""
    from .models import DeliveryOrder
    
    try:
        order = DeliveryOrder.objects.get(
            integration=integration,
            external_order_id=payload.get('order_id')
        )
        order.status = 'cancelled'
        order.save()
        
        # Also cancel internal order if exists
        if order.internal_order:
            order.internal_order.status = 'cancelled'
            order.internal_order.save()
            
    except DeliveryOrder.DoesNotExist:
        pass


# Provider-specific sync functions
def sync_doordash(integration):
    """Sync with DoorDash."""
    # TODO: Implement DoorDash API integration
    pass


def sync_ubereats(integration):
    """Sync with Uber Eats."""
    # TODO: Implement Uber Eats API integration
    pass


def sync_grubhub(integration):
    """Sync with Grubhub."""
    # TODO: Implement Grubhub API integration
    pass
