from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
import uuid

User = get_user_model()


class PaymentMethod(models.Model):
    """Payment methods available in the system"""
    PROVIDER_CHOICES = [
        ('paystack', 'Paystack'),
        ('stripe', 'Stripe'),
        ('flutterwave', 'Flutterwave'),
        ('bank_transfer', 'Bank Transfer'),
        ('cash', 'Cash on Delivery'),
    ]
    
    name = models.CharField(max_length=100)
    provider = models.CharField(max_length=50, choices=PROVIDER_CHOICES)
    is_active = models.BooleanField(default=True)
    configuration = models.JSONField(default=dict, blank=True)  # Store provider-specific config
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('name', 'provider')
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.provider})"


class Payment(models.Model):
    """Main payment model"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
        ('partially_refunded', 'Partially Refunded'),
    ]
    
    CURRENCY_CHOICES = [
        ('NGN', 'Nigerian Naira'),
        ('USD', 'US Dollar'),
        ('GBP', 'British Pound'),
        ('EUR', 'Euro'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    order = models.ForeignKey('orders.Order', on_delete=models.CASCADE, related_name='payments')
    
    # Payment details
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='NGN')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Provider details
    payment_method = models.CharField(max_length=50, default='paystack')
    reference = models.CharField(max_length=255, unique=True)  # Provider reference
    gateway_response = models.JSONField(default=dict, blank=True)  # Store full provider response
    
    # Fees and charges
    gateway_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    app_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['reference']),
            models.Index(fields=['created_at']),
            models.Index(fields=['status', 'created_at']),
        ]
    
    def __str__(self):
        return f"Payment {self.reference} - {self.amount} {self.currency}"
    
    def save(self, *args, **kwargs):
        if self.status == 'completed' and not self.completed_at:
            self.completed_at = timezone.now()
        super().save(*args, **kwargs)
    
    @property
    def is_successful(self):
        return self.status == 'completed'
    
    @property
    def total_amount(self):
        """Total amount including fees"""
        return self.amount + self.gateway_fee + self.app_fee
    
    def can_be_refunded(self):
        """Check if payment can be refunded"""
        return self.status in ['completed'] and self.amount > 0


class Transaction(models.Model):
    """Individual transactions within a payment"""
    TRANSACTION_TYPES = [
        ('payment', 'Payment'),
        ('refund', 'Refund'),
        ('partial_refund', 'Partial Refund'),
        ('chargeback', 'Chargeback'),
        ('verification', 'Verification'),
        ('webhook_confirmation', 'Webhook Confirmation'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='transactions')
    
    transaction_type = models.CharField(max_length=30, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Provider details
    reference = models.CharField(max_length=255)
    provider_transaction_id = models.CharField(max_length=255, blank=True)
    provider_response = models.JSONField(default=dict, blank=True)
    
    # Metadata
    notes = models.TextField(blank=True)
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='processed_transactions')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['payment', 'transaction_type']),
            models.Index(fields=['reference']),
            models.Index(fields=['status', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.transaction_type.title()} - {self.amount} ({self.status})"
    
    def save(self, *args, **kwargs):
        if self.status == 'completed' and not self.processed_at:
            self.processed_at = timezone.now()
        super().save(*args, **kwargs)


class PaymentWebhook(models.Model):
    """Store webhook events for audit and debugging"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    event_type = models.CharField(max_length=100)
    data = models.JSONField()
    signature = models.TextField()
    
    # Processing status
    processed = models.BooleanField(default=False)
    processing_error = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['event_type', 'processed']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Webhook {self.event_type} - {'Processed' if self.processed else 'Pending'}"


class PaymentAttempt(models.Model):
    """Track payment attempts for analytics and fraud detection"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payment_attempts')
    
    # Attempt details
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.CharField(max_length=3, default='NGN')
    payment_method = models.CharField(max_length=50)
    
    # Result
    success = models.BooleanField(default=False)
    error_message = models.TextField(blank=True)
    gateway_response = models.JSONField(default=dict, blank=True)
    
    # Security data
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    country = models.CharField(max_length=2, blank=True)  # ISO country code
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'success']),
            models.Index(fields=['ip_address', 'created_at']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Payment attempt by {self.user.email} - {'Success' if self.success else 'Failed'}"


class Refund(models.Model):
    """Refund model for tracking refunds"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    REFUND_TYPES = [
        ('full', 'Full Refund'),
        ('partial', 'Partial Refund'),
        ('chargeback', 'Chargeback'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='refunds')
    
    # Refund details
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    refund_type = models.CharField(max_length=20, choices=REFUND_TYPES, default='full')
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Provider details
    reference = models.CharField(max_length=255, unique=True)
    provider_refund_id = models.CharField(max_length=255, blank=True)
    gateway_response = models.JSONField(default=dict, blank=True)
    
    # Staff tracking
    requested_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='requested_refunds')
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='processed_refunds')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['payment', 'status']),
            models.Index(fields=['reference']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Refund {self.reference} - {self.amount}"
    
    def save(self, *args, **kwargs):
        if self.status == 'completed' and not self.processed_at:
            self.processed_at = timezone.now()
        super().save(*args, **kwargs)
