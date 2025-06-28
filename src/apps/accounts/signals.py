from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

from .models import UserProfile, UserPreferences, UserActivityLog

User = get_user_model()


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create UserProfile when a new user is created"""
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def create_user_preferences(sender, instance, created, **kwargs):
    """Create UserPreferences when a new user is created"""
    if created:
        UserPreferences.objects.create(user=instance)


@receiver(post_save, sender=User)
def log_user_registration(sender, instance, created, **kwargs):
    """Log user registration activity"""
    if created:
        UserActivityLog.objects.create(
            user=instance,
            activity_type='login',  # First login after registration
            description='User account created',
            metadata={'registration_method': 'email'}
        )


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Ensure profile exists and is saved when user is saved"""
    if hasattr(instance, 'profile'):
        instance.profile.save()
    else:
        # Create profile if it doesn't exist
        UserProfile.objects.get_or_create(user=instance)


@receiver(post_save, sender=User)
def save_user_preferences(sender, instance, **kwargs):
    """Ensure preferences exist and are saved when user is saved"""
    if hasattr(instance, 'preferences'):
        instance.preferences.save()
    else:
        # Create preferences if they don't exist
        UserPreferences.objects.get_or_create(user=instance)
