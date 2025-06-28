from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model

from .models import Cart, CartItem

User = get_user_model()


@receiver(post_save, sender=User)
def create_user_cart(sender, instance, created, **kwargs):
    """Create cart when a new user is created"""
    if created:
        Cart.objects.create(user=instance)


@receiver(post_save, sender=CartItem)
def update_cart_timestamp(sender, instance, **kwargs):
    """Update cart timestamp when cart item is modified"""
    instance.cart.save()


@receiver(post_delete, sender=CartItem)
def update_cart_timestamp_on_delete(sender, instance, **kwargs):
    """Update cart timestamp when cart item is deleted"""
    try:
        instance.cart.save()
    except Cart.DoesNotExist:
        pass  # Cart was already deleted
