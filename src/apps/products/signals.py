from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from django.db.models import Avg

from .models import ProductReview, Product, InventoryAlert, PriceAlert


@receiver(post_save, sender=ProductReview)
def update_product_rating(sender, instance, created, **kwargs):
    """Update product rating when a review is added or updated"""
    if created or instance.pk:
        product = instance.product
        reviews = ProductReview.objects.filter(product=product)
        avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0
        product.rating = round(avg_rating, 2)
        product.review_count = reviews.count()
        product.save(update_fields=['rating', 'review_count'])


@receiver(post_delete, sender=ProductReview)
def update_product_rating_on_delete(sender, instance, **kwargs):
    """Update product rating when a review is deleted"""
    product = instance.product
    reviews = ProductReview.objects.filter(product=product)
    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0
    product.rating = round(avg_rating, 2)
    product.review_count = reviews.count()
    product.save(update_fields=['rating', 'review_count'])


@receiver(post_save, sender=Product)
def check_inventory_alerts(sender, instance, **kwargs):
    """Check for low stock alerts when product quantity changes"""
    try:
        alert = InventoryAlert.objects.get(product=instance)
        if alert.check_stock_level() and alert.should_send_alert():
            # Here you would implement the actual notification logic
            # For now, we'll just update the last_alert_sent timestamp
            alert.last_alert_sent = timezone.now()
            alert.save(update_fields=['last_alert_sent'])
    except InventoryAlert.DoesNotExist:
        pass


@receiver(post_save, sender=Product)
def check_price_alerts(sender, instance, **kwargs):
    """Check for price drop alerts when product price changes"""
    if 'price' in getattr(instance, '_dirty_fields', []):
        alerts = PriceAlert.objects.filter(product=instance, is_active=True)
        for alert in alerts:
            alert.check_price_drop()
