from rest_framework import serializers
from decimal import Decimal

from ..models import Cart, CartItem, SavedForLater
from src.apps.products.api.serializers import ProductSerializer
from src.apps.products.models import Product


class CartItemSerializer(serializers.ModelSerializer):
    """Serializer for cart items"""
    product = ProductSerializer(read_only=True)
    product_id = serializers.IntegerField(write_only=True)
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    savings = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = CartItem
        fields = [
            'id', 'product', 'product_id', 'quantity', 'unit_price', 
            'total_price', 'savings', 'added_at', 'updated_at'
        ]
        read_only_fields = ['id', 'added_at', 'updated_at']
    
    def validate_product_id(self, value):
        """Validate that product exists and is available"""
        try:
            product = Product.objects.get(id=value)
            if not product.is_available:
                raise serializers.ValidationError("This product is not available")
            return value
        except Product.DoesNotExist:
            raise serializers.ValidationError("Product not found")
    
    def validate_quantity(self, value):
        """Validate quantity"""
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than 0")
        return value
    
    def validate(self, data):
        """Validate that enough stock is available"""
        if 'product_id' in data and 'quantity' in data:
            product = Product.objects.get(id=data['product_id'])
            if product.stock_quantity < data['quantity']:
                raise serializers.ValidationError(
                    f"Only {product.stock_quantity} items available for {product.name}"
                )
        return data


class CartSerializer(serializers.ModelSerializer):
    """Serializer for shopping cart"""
    items = CartItemSerializer(many=True, read_only=True)
    total_items = serializers.IntegerField(read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    total_weight = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    total_savings = serializers.SerializerMethodField()
    
    class Meta:
        model = Cart
        fields = [
            'id', 'items', 'total_items', 'subtotal', 'total_weight',
            'total_savings', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_total_savings(self, obj):
        """Calculate total savings across all cart items"""
        total = Decimal('0.00')
        for item in obj.items.all():
            total += item.savings
        return total


class AddToCartSerializer(serializers.Serializer):
    """Serializer for adding items to cart"""
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(default=1, min_value=1)
    
    def validate_product_id(self, value):
        """Validate that product exists and is available"""
        try:
            product = Product.objects.get(id=value)
            if not product.is_available:
                raise serializers.ValidationError("This product is not available")
            return value
        except Product.DoesNotExist:
            raise serializers.ValidationError("Product not found")
    
    def validate(self, data):
        """Validate that enough stock is available"""
        product = Product.objects.get(id=data['product_id'])
        if product.stock_quantity < data['quantity']:
            raise serializers.ValidationError(
                f"Only {product.stock_quantity} items available for {product.name}"
            )
        return data


class UpdateCartItemSerializer(serializers.Serializer):
    """Serializer for updating cart item quantity"""
    quantity = serializers.IntegerField(min_value=0)
    
    def validate(self, data):
        """Validate that enough stock is available"""
        if hasattr(self, 'instance') and self.instance:
            product = self.instance.product
            if data['quantity'] > 0 and product.stock_quantity < data['quantity']:
                raise serializers.ValidationError(
                    f"Only {product.stock_quantity} items available for {product.name}"
                )
        return data


class SavedForLaterSerializer(serializers.ModelSerializer):
    """Serializer for saved for later items"""
    product = ProductSerializer(read_only=True)
    product_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = SavedForLater
        fields = [
            'id', 'product', 'product_id', 'quantity', 'saved_at'
        ]
        read_only_fields = ['id', 'saved_at']
    
    def validate_product_id(self, value):
        """Validate that product exists"""
        try:
            Product.objects.get(id=value)
            return value
        except Product.DoesNotExist:
            raise serializers.ValidationError("Product not found")


class CartSummarySerializer(serializers.Serializer):
    """Serializer for cart summary information"""
    total_items = serializers.IntegerField()
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_weight = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_savings = serializers.DecimalField(max_digits=10, decimal_places=2)
    has_items = serializers.BooleanField()
    
    def to_representation(self, instance):
        """Custom representation for cart summary"""
        if isinstance(instance, Cart):
            return {
                'total_items': instance.total_items,
                'subtotal': instance.subtotal,
                'total_weight': instance.total_weight,
                'total_savings': sum(item.savings for item in instance.items.all()),
                'has_items': instance.total_items > 0
            }
        return super().to_representation(instance)
