from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Order, OrderStatusHistory


@receiver(pre_save, sender=Order)
def track_status_change(sender, instance, **kwargs):
    """Track order status changes"""
    if instance.pk:  # Only for existing orders
        try:
            old_instance = Order.objects.get(pk=instance.pk)
            # Store the old status to compare after save
            instance._old_status = old_instance.status
        except Order.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(post_save, sender=Order)
def create_status_history(sender, instance, created, **kwargs):
    """Create status history for order creation and status changes"""
    if created:
        # Create initial status history when order is created
        OrderStatusHistory.objects.create(
            order=instance,
            status=instance.status,
            notes="Order created"
        )
    else:
        # Check if status changed
        old_status = getattr(instance, '_old_status', None)
        if old_status and old_status != instance.status:
            OrderStatusHistory.objects.create(
                order=instance,
                status=instance.status,
                notes=f"Status changed from {old_status} to {instance.status}"
            )


@receiver(post_save, sender=Order)
def update_delivery_date_on_delivery(sender, instance, **kwargs):
    """Update actual delivery date when order status changes to delivered"""
    if instance.status == 'delivered' and not instance.actual_delivery_date:
        instance.actual_delivery_date = timezone.now()
        # Avoid infinite recursion by using update instead of save
        Order.objects.filter(pk=instance.pk).update(
            actual_delivery_date=instance.actual_delivery_date
        )
