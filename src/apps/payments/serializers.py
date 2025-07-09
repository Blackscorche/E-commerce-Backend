from rest_framework import serializers
from decimal import Decimal
from .models import Payment, Transaction, PaymentMethod, PaymentWebhook, Refund, PaymentAttempt


class PaymentMethodSerializer(serializers.ModelSerializer):
    """Serializer for payment methods"""
    
    class Meta:
        model = PaymentMethod
        fields = ['id', 'name', 'provider', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']


class TransactionSerializer(serializers.ModelSerializer):
    """Serializer for transactions"""
    
    class Meta:
        model = Transaction
        fields = [
            'id', 'transaction_type', 'amount', 'status', 'reference',
            'provider_transaction_id', 'notes', 'created_at', 'updated_at',
            'processed_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'processed_at']


class PaymentSerializer(serializers.ModelSerializer):
    """Serializer for payments"""
    transactions = TransactionSerializer(many=True, read_only=True)
    order_id = serializers.SerializerMethodField()
    total_amount = serializers.SerializerMethodField()
    is_successful = serializers.SerializerMethodField()
    can_be_refunded = serializers.SerializerMethodField()
    
    class Meta:
        model = Payment
        fields = [
            'id', 'order_id', 'amount', 'currency', 'status', 'payment_method',
            'reference', 'gateway_fee', 'app_fee', 'total_amount', 'is_successful',
            'can_be_refunded', 'metadata', 'transactions', 'created_at', 
            'updated_at', 'completed_at'
        ]
        read_only_fields = [
            'id', 'reference', 'gateway_fee', 'app_fee', 'total_amount',
            'is_successful', 'can_be_refunded', 'created_at', 'updated_at',
            'completed_at'
        ]
    
    def get_order_id(self, obj):
        return obj.order.id if obj.order else None
    
    def get_total_amount(self, obj):
        return obj.total_amount
    
    def get_is_successful(self, obj):
        return obj.is_successful
    
    def get_can_be_refunded(self, obj):
        return obj.can_be_refunded()


class PaymentInitializeSerializer(serializers.Serializer):
    """Serializer for payment initialization"""
    order_id = serializers.UUIDField(required=True)
    payment_method = serializers.CharField(default='paystack')
    save_payment_method = serializers.BooleanField(default=False)
    metadata = serializers.JSONField(required=False, default=dict)
    
    def validate_order_id(self, value):
        """Validate that order exists and belongs to user"""
        from src.apps.orders.models import Order
        user = self.context['request'].user
        
        try:
            order = Order.objects.get(id=value, user=user)
            if order.status != 'pending':
                raise serializers.ValidationError("Order is not in pending status")
            return value
        except Order.DoesNotExist:
            raise serializers.ValidationError("Order not found")


class PaymentVerificationSerializer(serializers.Serializer):
    """Serializer for payment verification"""
    reference = serializers.CharField(required=True)
    
    def validate_reference(self, value):
        """Validate that payment reference exists"""
        user = self.context['request'].user
        
        try:
            payment = Payment.objects.get(reference=value, user=user)
            return value
        except Payment.DoesNotExist:
            raise serializers.ValidationError("Payment reference not found")


class RefundSerializer(serializers.ModelSerializer):
    """Serializer for refunds"""
    payment_reference = serializers.SerializerMethodField()
    
    class Meta:
        model = Refund
        fields = [
            'id', 'payment_reference', 'amount', 'refund_type', 'reason',
            'status', 'reference', 'created_at', 'updated_at', 'processed_at'
        ]
        read_only_fields = [
            'id', 'payment_reference', 'reference', 'status', 'created_at',
            'updated_at', 'processed_at'
        ]
    
    def get_payment_reference(self, obj):
        return obj.payment.reference


class RefundRequestSerializer(serializers.Serializer):
    """Serializer for refund requests"""
    payment_id = serializers.UUIDField(required=True)
    amount = serializers.DecimalField(max_digits=15, decimal_places=2, required=False)
    refund_type = serializers.ChoiceField(choices=Refund.REFUND_TYPES, default='full')
    reason = serializers.CharField(required=True, max_length=1000)
    
    def validate_payment_id(self, value):
        """Validate that payment exists and can be refunded"""
        user = self.context['request'].user
        
        try:
            payment = Payment.objects.get(id=value, user=user)
            if not payment.can_be_refunded():
                raise serializers.ValidationError("Payment cannot be refunded")
            return value
        except Payment.DoesNotExist:
            raise serializers.ValidationError("Payment not found")
    
    def validate(self, data):
        """Validate refund amount"""
        payment_id = data.get('payment_id')
        amount = data.get('amount')
        refund_type = data.get('refund_type')
        
        if payment_id:
            user = self.context['request'].user
            payment = Payment.objects.get(id=payment_id, user=user)
            
            # Calculate already refunded amount
            refunded_amount = sum(
                refund.amount for refund in payment.refunds.filter(status='completed')
            )
            
            if refund_type == 'full':
                # For full refund, amount should be remaining amount
                remaining_amount = payment.amount - refunded_amount
                if amount and amount != remaining_amount:
                    raise serializers.ValidationError(
                        f"For full refund, amount should be {remaining_amount}"
                    )
                data['amount'] = remaining_amount
            else:
                # For partial refund, validate amount
                if not amount:
                    raise serializers.ValidationError("Amount is required for partial refund")
                
                if amount <= 0:
                    raise serializers.ValidationError("Amount must be greater than 0")
                
                if amount > (payment.amount - refunded_amount):
                    raise serializers.ValidationError(
                        f"Amount cannot exceed available refund amount: {payment.amount - refunded_amount}"
                    )
        
        return data


class PaymentWebhookSerializer(serializers.ModelSerializer):
    """Serializer for payment webhooks"""
    
    class Meta:
        model = PaymentWebhook
        fields = [
            'id', 'event_type', 'data', 'processed', 'processing_error',
            'created_at', 'processed_at'
        ]
        read_only_fields = ['id', 'created_at', 'processed_at']


class PaymentAttemptSerializer(serializers.ModelSerializer):
    """Serializer for payment attempts"""
    
    class Meta:
        model = PaymentAttempt
        fields = [
            'id', 'amount', 'currency', 'payment_method', 'success',
            'error_message', 'ip_address', 'country', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class PaymentStatsSerializer(serializers.Serializer):
    """Serializer for payment statistics"""
    total_payments = serializers.IntegerField()
    successful_payments = serializers.IntegerField()
    failed_payments = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    success_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    average_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    monthly_stats = serializers.ListField(child=serializers.DictField())


class PaymentMethodStatsSerializer(serializers.Serializer):
    """Serializer for payment method statistics"""
    payment_method = serializers.CharField()
    count = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    success_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
