from django.db import models
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

from taggit.managers import TaggableManager

User = get_user_model()


# Create your models here.
class Brand(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    logo = models.ImageField(upload_to="brands/logos", null=True, blank=True)
    description = models.TextField(blank=True)
    website = models.URLField(blank=True)
    founded_year = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='subcategories')
    icon = models.ImageField(upload_to="categories/icons", null=True, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ('name',)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("products:category", kwargs={"name": self.name})


class Product(models.Model):
    CONDITION_CHOICES = [
        ('new', 'New'),
        ('refurbished', 'Refurbished'),
        ('open_box', 'Open Box'),
        ('used', 'Used'),
    ]

    category = models.ManyToManyField(Category, blank=False)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='products')
    tags = TaggableManager(blank=True)  # Features: wireless, waterproof, etc.
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=200, unique=True)
    model_number = models.CharField(max_length=100, blank=True)
    description = models.TextField(max_length=500, default="Empty description.")
    picture = models.ImageField(upload_to="products/images", null=True, blank=True)
    price = models.DecimalField(decimal_places=2, max_digits=20, default=0)
    original_price = models.DecimalField(decimal_places=2, max_digits=20, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=10)  # available quantity
    featured = models.BooleanField(default=False)  # is product featured?
    release_date = models.DateField(null=True, blank=True)
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default='new')
    warranty_months = models.PositiveIntegerField(default=12)
    specifications = models.JSONField(default=dict, blank=True)  # Technical specs
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    review_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name

    @property
    def is_featured(self):
        return self.featured

    @property
    def is_available(self):
        return self.quantity > 0

    @property
    def discount_percentage(self):
        if self.original_price and self.original_price > self.price:
            return round(((self.original_price - self.price) / self.original_price) * 100, 2)
        return 0

    @property
    def is_on_sale(self):
        return self.original_price and self.original_price > self.price

    @property
    def stock_quantity(self):
        """Alias for quantity field used by cart models"""
        return self.quantity
    
    @property
    def discounted_price(self):
        """Get current price (considering original_price for sales)"""
        return self.price
    
    @property
    def weight(self):
        """Default weight property for shipping calculations"""
        # If specifications contain weight, return it, otherwise default to 0.5kg
        if isinstance(self.specifications, dict):
            return Decimal(str(self.specifications.get('weight', 0.5)))
        return Decimal('0.5')


class ProductReview(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    title = models.CharField(max_length=200)
    review_text = models.TextField()
    verified_purchase = models.BooleanField(default=False)
    helpful_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('product', 'user')
        ordering = ('-created_at',)

    def __str__(self):
        return f"{self.title} - {self.product.name}"


class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlists')
    products = models.ManyToManyField(Product, through='WishlistItem')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user',)

    def __str__(self):
        return f"{self.user.email}'s Wishlist"

    @property
    def total_items(self):
        return self.products.count()

    @property
    def total_value(self):
        return sum(item.product.price for item in self.wishlist_items.all())


class WishlistItem(models.Model):
    wishlist = models.ForeignKey(Wishlist, on_delete=models.CASCADE, related_name='wishlist_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('wishlist', 'product')

    def __str__(self):
        return f"{self.product.name} in {self.wishlist.user.email}'s wishlist"


class PriceAlert(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='price_alerts')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='price_alerts')
    target_price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    notified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('user', 'product')

    def __str__(self):
        return f"Price alert for {self.product.name} at {self.target_price}"

    def check_price_drop(self):
        """Check if product price has dropped to target price"""
        if self.product.price <= self.target_price and self.is_active:
            # This would trigger a notification (implementation depends on your notification system)
            from django.utils import timezone
            self.notified_at = timezone.now()
            self.is_active = False
            self.save()
            return True
        return False


class ProductComparison(models.Model):
    """Model for comparing products side by side"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comparisons')
    products = models.ManyToManyField(Product, limit_choices_to={'category': 'same'})
    name = models.CharField(max_length=200, default="My Comparison")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at',)

    def __str__(self):
        return f"{self.user.email}'s comparison: {self.name}"

    @property
    def product_count(self):
        return self.products.count()


class InventoryAlert(models.Model):
    """Model for inventory management alerts"""
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='inventory_alert')
    low_stock_threshold = models.PositiveIntegerField(default=5)
    auto_reorder = models.BooleanField(default=False)
    last_alert_sent = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Inventory alert for {self.product.name}"

    def check_stock_level(self):
        """Check if stock is below threshold"""
        return self.product.quantity <= self.low_stock_threshold

    def should_send_alert(self):
        """Check if alert should be sent (not sent in last 24 hours)"""
        from django.utils import timezone
        from datetime import timedelta
        
        if not self.last_alert_sent:
            return True
        
        return timezone.now() - self.last_alert_sent > timedelta(hours=24)
