from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUserManager(BaseUserManager):
    """
    Custom user model manager with email as the unique identifier
    """

    def create_user(self, first_name, last_name, email, password, **extra_fields):
        """
        Create user with the given email and password.
        """
        if not email:
            raise ValueError("The email must be set")
        first_name = first_name.capitalize()
        last_name = last_name.capitalize()
        email = self.normalize_email(email)

        user = self.model(
            first_name=first_name, last_name=last_name, email=email, **extra_fields
        )
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, first_name, last_name, email, password, **extra_fields):
        """
        Create superuser with the given email and password.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_user(first_name, last_name, email, password, **extra_fields)


class CustomUser(AbstractUser):
    username = None
    first_name = models.CharField(max_length=255, verbose_name="First name")
    last_name = models.CharField(max_length=255, verbose_name="Last name")
    email = models.EmailField(unique=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    objects = CustomUserManager()

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def initials(self):
        return f"{self.first_name[0]}{self.last_name[0]}".upper()


class UserProfile(models.Model):
    """Extended user profile for eCommerce functionality"""
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
        ('N', 'Prefer not to say'),
    ]
    
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='profiles/avatars/', null=True, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    bio = models.TextField(max_length=500, blank=True)
    
    # Preferences
    newsletter_subscribed = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=False)
    email_notifications = models.BooleanField(default=True)
    
    # Tech preferences for gadget store
    preferred_brands = models.ManyToManyField('products.Brand', blank=True)
    preferred_categories = models.ManyToManyField('products.Category', blank=True)
    budget_range_min = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    budget_range_max = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.full_name}'s Profile"
    
    @property
    def age(self):
        if self.date_of_birth:
            from django.utils import timezone
            today = timezone.now().date()
            return today.year - self.date_of_birth.year - (
                (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
            )
        return None


class Address(models.Model):
    """User addresses for shipping and billing"""
    ADDRESS_TYPES = [
        ('shipping', 'Shipping Address'),
        ('billing', 'Billing Address'),
        ('both', 'Shipping & Billing'),
    ]
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='addresses')
    type = models.CharField(max_length=10, choices=ADDRESS_TYPES, default='shipping')
    
    # Address fields
    full_name = models.CharField(max_length=255)
    company = models.CharField(max_length=255, blank=True)
    address_line_1 = models.CharField(max_length=255)
    address_line_2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default='Nigeria')
    phone_number = models.CharField(max_length=20, blank=True)
    
    # Flags
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Address"
        verbose_name_plural = "Addresses"
        ordering = ['-is_default', '-created_at']
    
    def __str__(self):
        return f"{self.full_name} - {self.city}, {self.state}"
    
    def save(self, *args, **kwargs):
        # Ensure only one default address per type per user
        if self.is_default:
            Address.objects.filter(
                user=self.user, 
                type=self.type, 
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


class UserActivityLog(models.Model):
    """Track user activities for analytics and recommendations"""
    ACTIVITY_TYPES = [
        ('login', 'User Login'),
        ('logout', 'User Logout'),
        ('product_view', 'Product Viewed'),
        ('product_search', 'Product Searched'),
        ('cart_add', 'Added to Cart'),
        ('wishlist_add', 'Added to Wishlist'),
        ('order_placed', 'Order Placed'),
        ('review_added', 'Review Added'),
        ('profile_updated', 'Profile Updated'),
    ]
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='activity_logs')
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    description = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)  # Store additional data
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "User Activity Log"
        verbose_name_plural = "User Activity Logs"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'activity_type']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.get_activity_type_display()}"


class UserPreferences(models.Model):
    """User app preferences and settings"""
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='preferences')
    
    # Display preferences
    theme = models.CharField(max_length=10, choices=[('light', 'Light'), ('dark', 'Dark')], default='light')
    language = models.CharField(max_length=10, default='en')
    currency = models.CharField(max_length=3, default='NGN')
    timezone = models.CharField(max_length=50, default='Africa/Lagos')
    
    # Shopping preferences
    price_alerts_enabled = models.BooleanField(default=True)
    deal_notifications = models.BooleanField(default=True)
    new_product_notifications = models.BooleanField(default=False)
    inventory_notifications = models.BooleanField(default=True)
    
    # Privacy preferences
    profile_visibility = models.CharField(
        max_length=10, 
        choices=[('public', 'Public'), ('private', 'Private')], 
        default='private'
    )
    allow_reviews_display = models.BooleanField(default=True)
    allow_data_collection = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "User Preferences"
        verbose_name_plural = "User Preferences"
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.user.email}'s Preferences"
