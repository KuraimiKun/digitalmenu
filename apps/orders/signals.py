"""Order signals for status tracking and notifications."""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Order, OrderStatusHistory


@receiver(pre_save, sender=Order)
def track_status_change(sender, instance, **kwargs):
    """Track when order status changes."""
    if instance.pk:
        try:
            old_instance = Order.objects.get(pk=instance.pk)
            if old_instance.status != instance.status:
                instance._status_changed = True
                instance._old_status = old_instance.status
            else:
                instance._status_changed = False
        except Order.DoesNotExist:
            instance._status_changed = False
    else:
        instance._status_changed = True
        instance._old_status = None


@receiver(post_save, sender=Order)
def create_status_history(sender, instance, created, **kwargs):
    """Create status history entry when status changes."""
    if created or getattr(instance, '_status_changed', False):
        OrderStatusHistory.objects.create(
            order=instance,
            status=instance.status
        )


@receiver(post_save, sender=Order)
def notify_order_status(sender, instance, created, **kwargs):
    """Send notifications for order status changes."""
    if created:
        # TODO: Send order confirmation notification
        pass
    elif getattr(instance, '_status_changed', False):
        # TODO: Send status update notification
        pass
