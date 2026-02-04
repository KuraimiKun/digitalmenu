"""Integration signals for automated actions."""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone


@receiver(post_save, sender='integrations.DeliveryOrder')
def create_internal_order_from_delivery(sender, instance, created, **kwargs):
    """Create internal order when delivery order is received."""
    if created and not instance.internal_order:
        from apps.orders.models import Order, OrderItem
        
        # Create internal order
        order = Order.objects.create(
            restaurant=instance.integration.restaurant,
            location=instance.location,
            order_type='delivery',
            status='confirmed',
            customer_name=instance.customer_name,
            customer_phone=instance.customer_phone,
            delivery_address=instance.delivery_address.get('formatted', ''),
            special_instructions=instance.special_instructions,
            subtotal=instance.subtotal,
            tax=instance.tax,
            delivery_fee=instance.delivery_fee,
            total=instance.total,
            payment_status='paid',
            source='delivery_platform',
        )
        
        # Link to delivery order
        instance.internal_order = order
        instance.save(update_fields=['internal_order'])


@receiver(pre_save, sender='integrations.RestaurantIntegration')
def set_connected_timestamp(sender, instance, **kwargs):
    """Set connected timestamp when status changes to active."""
    if instance.pk:
        try:
            old_instance = sender.objects.get(pk=instance.pk)
            if old_instance.status != 'active' and instance.status == 'active':
                instance.connected_at = timezone.now()
        except sender.DoesNotExist:
            pass
