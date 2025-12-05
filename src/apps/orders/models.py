import uuid
from django.db import models
from django.contrib.auth import get_user_model
from decimal import Decimal
from django.utils import timezone
from django.core.validators import MinValueValidator

from src.apps.products.models import Product
from src.apps.accounts.models import Address

User = get_user_model()


class Order(models.Model):
    """Customer orders"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'), 
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    # Order identification
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_number = models.CharField(max_length=20, unique=True, db_index=True)
    
    # Customer information
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    email = models.EmailField()  # Store email at time of order
    phone_number = models.CharField(max_length=20, blank=True)
    
    # Order status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    
    # Addresses (stored at time of order)
    shipping_address = models.JSONField()  # Store complete address details
    billing_address = models.JSONField(null=True, blank=True)  # If different from shipping
    
    # Financial information
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Payment information
    payment_method = models.CharField(max_length=50, default='paystack')
    payment_reference = models.CharField(max_length=255, blank=True)
    paystack_reference = models.CharField(max_length=255, blank=True)
    
    # Shipping information
    estimated_delivery_date = models.DateField(null=True, blank=True)
    actual_delivery_date = models.DateTimeField(null=True, blank=True)
    tracking_number = models.CharField(max_length=100, blank=True)
    courier_service = models.CharField(max_length=100, blank=True)
    
    # Special instructions
    special_instructions = models.TextField(blank=True)
    
    # Metadata
    order_notes = models.TextField(blank=True)  # Internal notes
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Order"
        verbose_name_plural = "Orders"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order_number']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['payment_status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Order #{self.order_number}"
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        super().save(*args, **kwargs)
    
    @staticmethod
    def generate_order_number():
        """Generate unique order number"""
        import random
        import string
        from django.utils import timezone
        
        # Format: ORD-YYYYMMDD-XXXXX
        date_str = timezone.now().strftime('%Y%m%d')
        random_str = ''.join(random.choices(string.digits, k=5))
        order_number = f"ORD-{date_str}-{random_str}"
        
        # Ensure uniqueness
        while Order.objects.filter(order_number=order_number).exists():
            random_str = ''.join(random.choices(string.digits, k=5))
            order_number = f"ORD-{date_str}-{random_str}"
        
        return order_number
    
    @property
    def total_items(self):
        """Get total number of items in order"""
        return self.items.aggregate(
            total=models.Sum('quantity')
        )['total'] or 0
    
    @property
    def is_delivered(self):
        """Check if order is delivered"""
        return self.status == 'delivered'
    
    @property
    def is_cancelled(self):
        """Check if order is cancelled"""
        return self.status == 'cancelled'
    
    @property
    def can_cancel(self):
        """Check if order can be cancelled"""
        return self.status in ['pending', 'confirmed'] and self.payment_status != 'completed'
    
    @property
    def can_refund(self):
        """Check if order can be refunded"""
        return self.payment_status == 'completed' and self.status not in ['cancelled', 'refunded']
    
    def cancel_order(self, reason=""):
        """Cancel the order and update stock"""
        if not self.can_cancel:
            raise ValueError("Order cannot be cancelled")
        
        self.status = 'cancelled'
        self.order_notes += f"\nCancelled: {reason}" if reason else "\nCancelled by user"
        self.save()
        
        # Restore stock for all items
        for item in self.items.all():
            item.product.quantity += item.quantity
            item.product.save()
    
    def mark_as_delivered(self):
        """Mark order as delivered"""
        self.status = 'delivered'
        self.actual_delivery_date = timezone.now()
        self.save()


class OrderItem(models.Model):
    """Individual items in an order"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    
    # Product details at time of order (in case product details change)
    product_name = models.CharField(max_length=255)
    product_sku = models.CharField(max_length=100, blank=True)
    product_image = models.URLField(blank=True)
    
    # Pricing
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Order Item"
        verbose_name_plural = "Order Items"
        ordering = ['id']
        unique_together = ['order', 'product']
    
    def __str__(self):
        return f"{self.quantity}x {self.product_name} in {self.order}"
    
    def save(self, *args, **kwargs):
        # Calculate total price
        self.total_price = self.unit_price * self.quantity
        
        # Store product details at time of order
        if self.product:
            self.product_name = self.product.name
            self.product_sku = getattr(self.product, 'sku', '')
            if self.product.picture:
                self.product_image = self.product.picture.url
        
        super().save(*args, **kwargs)


class OrderStatusHistory(models.Model):
    """Track order status changes"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='status_history')
    status = models.CharField(max_length=20, choices=Order.STATUS_CHOICES)
    notes = models.TextField(blank=True)
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Order Status History"
        verbose_name_plural = "Order Status Histories"
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.order} - {self.get_status_display()} at {self.timestamp}"


class OrderShippingUpdate(models.Model):
    """Shipping updates and tracking information"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='shipping_updates')
    update_type = models.CharField(max_length=50, choices=[
        ('shipped', 'Shipped'),
        ('in_transit', 'In Transit'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('exception', 'Exception'),
    ])
    message = models.TextField()
    location = models.CharField(max_length=255, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Shipping Update"
        verbose_name_plural = "Shipping Updates"
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.order} - {self.update_type} at {self.timestamp}"


class ReturnRequest(models.Model):
    """Customer return requests"""
    
    RETURN_REASONS = [
        ('defective', 'Defective Product'),
        ('damaged', 'Damaged in Shipping'),
        ('wrong_item', 'Wrong Item Sent'),
        ('not_as_described', 'Not as Described'),
        ('changed_mind', 'Changed Mind'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
    ]
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='return_requests')
    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE, null=True, blank=True)
    
    reason = models.CharField(max_length=20, choices=RETURN_REASONS)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    requested_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    admin_notes = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Return Request"
        verbose_name_plural = "Return Requests"
        ordering = ['-requested_at']
    
    def __str__(self):
        return f"Return request for {self.order}"

class SwapRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='swap_requests', null=True, blank=True)
    email = models.EmailField(blank=True, null=True, help_text="Email for non-logged-in users")
    user_device = models.JSONField(default=dict)
    estimated_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    final_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Final value set by admin after inspection")
    target_device_id = models.CharField(max_length=120, blank=True, default='')
    target_device_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    difference = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    admin_notes = models.TextField(blank=True, help_text="Admin notes about the swap")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-created_at',)
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        email = self.user.email if self.user else (self.email or 'No email')
        return f"Swap {self.id} - {email} - {self.status}"
