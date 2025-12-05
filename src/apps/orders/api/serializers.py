from rest_framework import serializers
from decimal import Decimal

from ..models import Order, OrderItem, OrderStatusHistory, OrderShippingUpdate, ReturnRequest, SwapRequest
from src.apps.products.api.serializers import ProductSerializer
from src.apps.accounts.models import Address


class OrderItemSerializer(serializers.ModelSerializer):
    """Serializer for order items"""
    product = ProductSerializer(read_only=True)
    
    class Meta:
        model = OrderItem
        fields = [
            'id', 'product', 'product_name', 'product_sku', 'product_image',
            'unit_price', 'quantity', 'total_price', 'created_at'
        ]
        read_only_fields = ['id', 'total_price', 'created_at']


class OrderStatusHistorySerializer(serializers.ModelSerializer):
    """Serializer for order status history"""
    changed_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = OrderStatusHistory
        fields = [
            'id', 'status', 'notes', 'changed_by_name', 'timestamp'
        ]
        read_only_fields = ['id', 'timestamp']
    
    def get_changed_by_name(self, obj):
        if obj.changed_by:
            return obj.changed_by.full_name
        return 'System'


class OrderShippingUpdateSerializer(serializers.ModelSerializer):
    """Serializer for shipping updates"""
    
    class Meta:
        model = OrderShippingUpdate
        fields = [
            'id', 'update_type', 'message', 'location', 'timestamp'
        ]
        read_only_fields = ['id', 'timestamp']


class OrderSerializer(serializers.ModelSerializer):
    """Serializer for orders"""
    items = OrderItemSerializer(many=True, read_only=True)
    status_history = OrderStatusHistorySerializer(many=True, read_only=True)
    shipping_updates = OrderShippingUpdateSerializer(many=True, read_only=True)
    total_items = serializers.IntegerField(read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'user_email', 'user_name', 'email', 'phone_number',
            'status', 'payment_status', 'shipping_address', 'billing_address',
            'subtotal', 'shipping_cost', 'tax_amount', 'discount_amount', 'total_amount',
            'payment_method', 'payment_reference', 'paystack_reference',
            'estimated_delivery_date', 'actual_delivery_date', 'tracking_number',
            'courier_service', 'special_instructions', 'order_notes',
            'items', 'status_history', 'shipping_updates', 'total_items',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'order_number', 'user_email', 'user_name', 'total_items',
            'created_at', 'updated_at'
        ]


class CreateOrderSerializer(serializers.Serializer):
    """Serializer for creating orders from cart"""
    shipping_address_id = serializers.IntegerField()
    billing_address_id = serializers.IntegerField(required=False)
    payment_method = serializers.CharField(default='paystack')
    special_instructions = serializers.CharField(required=False, allow_blank=True)
    
    def validate_shipping_address_id(self, value):
        """Validate shipping address belongs to user"""
        user = self.context['request'].user
        try:
            address = Address.objects.get(id=value, user=user, is_active=True)
            return value
        except Address.DoesNotExist:
            raise serializers.ValidationError("Invalid shipping address")
    
    def validate_billing_address_id(self, value):
        """Validate billing address belongs to user"""
        if value:
            user = self.context['request'].user
            try:
                address = Address.objects.get(id=value, user=user, is_active=True)
                return value
            except Address.DoesNotExist:
                raise serializers.ValidationError("Invalid billing address")
        return value


class OrderSummarySerializer(serializers.ModelSerializer):
    """Simplified order serializer for listings"""
    total_items = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'status', 'payment_status', 'total_amount',
            'total_items', 'created_at', 'estimated_delivery_date'
        ]
        read_only_fields = ['id', 'total_items', 'created_at']


class ReturnRequestSerializer(serializers.ModelSerializer):
    """Serializer for return requests"""
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    product_name = serializers.CharField(source='order_item.product_name', read_only=True)
    
    class Meta:
        model = ReturnRequest
        fields = [
            'id', 'order', 'order_number', 'order_item', 'product_name',
            'reason', 'description', 'status', 'requested_at', 'processed_at',
            'refund_amount', 'admin_notes'
        ]
        read_only_fields = [
            'id', 'order_number', 'product_name', 'status', 'requested_at',
            'processed_at', 'refund_amount', 'admin_notes'
        ]
    
    def validate_order(self, value):
        """Validate order belongs to user"""
        user = self.context['request'].user
        if value.user != user:
            raise serializers.ValidationError("Invalid order")
        if not value.can_refund:
            raise serializers.ValidationError("This order cannot be returned")
        return value


class OrderUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating order status (admin only)"""
    
    class Meta:
        model = Order
        fields = [
            'status', 'payment_status', 'tracking_number', 'courier_service',
            'estimated_delivery_date', 'order_notes'
        ]
    
    def update(self, instance, validated_data):
        """Update order and create status history"""
        old_status = instance.status
        instance = super().update(instance, validated_data)
        
        # Create status history if status changed
        if old_status != instance.status:
            OrderStatusHistory.objects.create(
                order=instance,
                status=instance.status,
                notes=f"Status changed from {old_status} to {instance.status}",
                changed_by=self.context['request'].user
            )
        
        return instance

class SwapRequestSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True, required=False)
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    
    class Meta:
        model = SwapRequest
        fields = [
            'id',
            'user',
            'user_email',
            'email',
            'user_device',
            'estimated_value',
            'final_value',
            'target_device_id',
            'target_device_price',
            'difference',
            'status',
            'admin_notes',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'status', 'created_at', 'updated_at', 'final_value', 'admin_notes']
    
    def validate(self, data):
        """Ensure email is provided if user is not authenticated"""
        request = self.context.get('request', None)
        user = None
        if request and hasattr(request, 'user'):
            try:
                user = request.user if request.user.is_authenticated else None
            except:
                user = None
        
        email = data.get('email', '') or ''
        
        # If no user and no email, raise validation error
        if not user and not email:
            raise serializers.ValidationError({'email': 'Email is required when not logged in.'})
        
        return data
