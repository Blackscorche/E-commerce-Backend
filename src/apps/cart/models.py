from django.db import models
from django.contrib.auth import get_user_model
from decimal import Decimal
from django.core.exceptions import ValidationError

from src.apps.products.models import Product

User = get_user_model()


class Cart(models.Model):
    """Shopping cart for users and guests"""
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='cart'
    )
    session_key = models.CharField(max_length=255, null=True, blank=True)  # For guest users
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Shopping Cart"
        verbose_name_plural = "Shopping Carts"
        ordering = ['-updated_at']
        constraints = [
            models.CheckConstraint(
                check=models.Q(user__isnull=False) | models.Q(session_key__isnull=False),
                name='cart_must_have_user_or_session'
            )
        ]
    
    def __str__(self):
        if self.user:
            return f"Cart for {self.user.email}"
        return f"Guest Cart {self.session_key}"
    
    @property
    def total_items(self):
        """Get total number of items in cart"""
        return self.items.aggregate(
            total=models.Sum('quantity')
        )['total'] or 0
    
    @property
    def subtotal(self):
        """Calculate cart subtotal"""
        total = Decimal('0.00')
        for item in self.items.all():
            total += item.total_price
        return total
    
    @property
    def total_weight(self):
        """Calculate total weight of cart items"""
        total = Decimal('0.00')
        for item in self.items.all():
            if item.product.weight:
                total += Decimal(str(item.product.weight)) * item.quantity
        return total
    
    def add_item(self, product, quantity=1):
        """Add item to cart or update quantity if exists"""
        if not product.is_available:
            raise ValidationError(f"Product {product.name} is not available")
        
        if product.stock_quantity < quantity:
            raise ValidationError(f"Only {product.stock_quantity} items available for {product.name}")
        
        cart_item, created = self.items.get_or_create(
            product=product,
            defaults={'quantity': quantity}
        )
        
        if not created:
            new_quantity = cart_item.quantity + quantity
            if product.stock_quantity < new_quantity:
                raise ValidationError(f"Only {product.stock_quantity} items available for {product.name}")
            cart_item.quantity = new_quantity
            cart_item.save()
        
        return cart_item
    
    def remove_item(self, product):
        """Remove item from cart"""
        self.items.filter(product=product).delete()
    
    def update_item_quantity(self, product, quantity):
        """Update item quantity in cart"""
        if quantity <= 0:
            self.remove_item(product)
            return None
        
        if product.stock_quantity < quantity:
            raise ValidationError(f"Only {product.stock_quantity} items available for {product.name}")
        
        cart_item = self.items.filter(product=product).first()
        if cart_item:
            cart_item.quantity = quantity
            cart_item.save()
            return cart_item
        return None
    
    def clear(self):
        """Clear all items from cart"""
        self.items.all().delete()
    
    def merge_with_cart(self, other_cart):
        """Merge items from another cart into this cart"""
        for item in other_cart.items.all():
            try:
                self.add_item(item.product, item.quantity)
            except ValidationError:
                # Skip items that can't be added due to stock issues
                pass
        other_cart.delete()


class CartItem(models.Model):
    """Individual items in a shopping cart"""
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Cart Item"
        verbose_name_plural = "Cart Items"
        ordering = ['-added_at']
        unique_together = ['cart', 'product']
    
    def __str__(self):
        return f"{self.quantity}x {self.product.name} in {self.cart}"
    
    @property
    def unit_price(self):
        """Get current unit price (with any discounts)"""
        return self.product.discounted_price
    
    @property
    def total_price(self):
        """Calculate total price for this item"""
        return self.unit_price * self.quantity
    
    @property
    def savings(self):
        """Calculate savings if product is on sale"""
        if self.product.is_on_sale:
            return (self.product.original_price - self.product.price) * self.quantity
        return Decimal('0.00')
    
    def clean(self):
        """Validate cart item"""
        if self.quantity <= 0:
            raise ValidationError("Quantity must be greater than 0")
        
        if not self.product.is_available:
            raise ValidationError(f"Product {self.product.name} is not available")
        
        if self.product.stock_quantity < self.quantity:
            raise ValidationError(
                f"Only {self.product.stock_quantity} items available for {self.product.name}"
            )
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class SavedForLater(models.Model):
    """Items saved for later purchase"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    saved_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Saved Item"
        verbose_name_plural = "Saved Items"
        ordering = ['-saved_at']
        unique_together = ['user', 'product']
    
    def __str__(self):
        return f"{self.user.email} saved {self.product.name}"
    
    def move_to_cart(self):
        """Move item from saved for later to cart"""
        cart, created = Cart.objects.get_or_create(user=self.user)
        cart_item = cart.add_item(self.product, self.quantity)
        self.delete()
        return cart_item
