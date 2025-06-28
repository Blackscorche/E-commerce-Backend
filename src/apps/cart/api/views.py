from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter

from ..models import Cart, CartItem, SavedForLater
from .serializers import (
    CartSerializer, CartItemSerializer, AddToCartSerializer,
    UpdateCartItemSerializer, SavedForLaterSerializer, CartSummarySerializer
)
from src.apps.products.models import Product
from src.apps.accounts.models import UserActivityLog


class CartViewSet(viewsets.ModelViewSet):
    """ViewSet for shopping cart management"""
    serializer_class = CartSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Cart.objects.filter(user=self.request.user)
    
    def get_object(self):
        """Get or create cart for current user"""
        cart, created = Cart.objects.get_or_create(user=self.request.user)
        return cart
    
    def list(self, request):
        """Get current user's cart"""
        cart = self.get_object()
        serializer = self.get_serializer(cart)
        return Response(serializer.data)
    
    def perform_create(self, serializer):
        """This shouldn't be called as we auto-create carts"""
        pass
    
    @action(detail=False, methods=['post'])
    def add_item(self, request):
        """Add item to cart"""
        serializer = AddToCartSerializer(data=request.data)
        if serializer.is_valid():
            cart = self.get_object()
            product = Product.objects.get(id=serializer.validated_data['product_id'])
            quantity = serializer.validated_data['quantity']
            
            try:
                cart_item = cart.add_item(product, quantity)
                
                # Log activity
                UserActivityLog.objects.create(
                    user=request.user,
                    activity_type='cart_add',
                    description=f'Added {product.name} to cart',
                    metadata={
                        'product_id': product.id,
                        'product_name': product.name,
                        'quantity': quantity,
                        'price': str(product.discounted_price)
                    },
                    ip_address=self.get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )
                
                item_serializer = CartItemSerializer(cart_item)
                return Response(item_serializer.data, status=status.HTTP_201_CREATED)
            
            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['patch'])
    def update_item(self, request):
        """Update cart item quantity"""
        product_id = request.data.get('product_id')
        if not product_id:
            return Response({'error': 'product_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = UpdateCartItemSerializer(data=request.data)
        if serializer.is_valid():
            cart = self.get_object()
            product = get_object_or_404(Product, id=product_id)
            quantity = serializer.validated_data['quantity']
            
            try:
                if quantity == 0:
                    cart.remove_item(product)
                    return Response({'message': 'Item removed from cart'})
                else:
                    cart_item = cart.update_item_quantity(product, quantity)
                    if cart_item:
                        item_serializer = CartItemSerializer(cart_item)
                        return Response(item_serializer.data)
                    else:
                        return Response({'error': 'Item not found in cart'}, status=status.HTTP_404_NOT_FOUND)
            
            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['delete'])
    def remove_item(self, request):
        """Remove item from cart"""
        product_id = request.query_params.get('product_id')
        if not product_id:
            return Response({'error': 'product_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        cart = self.get_object()
        product = get_object_or_404(Product, id=product_id)
        cart.remove_item(product)
        
        return Response({'message': 'Item removed from cart'})
    
    @action(detail=False, methods=['delete'])
    def clear(self, request):
        """Clear all items from cart"""
        cart = self.get_object()
        cart.clear()
        return Response({'message': 'Cart cleared'})
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get cart summary"""
        cart = self.get_object()
        serializer = CartSummarySerializer(cart)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def validate_stock(self, request):
        """Validate that all cart items are still in stock"""
        cart = self.get_object()
        issues = []
        
        for item in cart.items.all():
            if not item.product.is_available:
                issues.append({
                    'item_id': item.id,
                    'product_name': item.product.name,
                    'issue': 'Product is no longer available'
                })
            elif item.product.stock_quantity < item.quantity:
                issues.append({
                    'item_id': item.id,
                    'product_name': item.product.name,
                    'issue': f'Only {item.product.stock_quantity} items available',
                    'available_quantity': item.product.stock_quantity
                })
        
        return Response({
            'is_valid': len(issues) == 0,
            'issues': issues
        })
    
    @action(detail=False, methods=['post'])
    def save_for_later(self, request):
        """Save a cart item for later"""
        cart = self.get_object()
        product_id = request.data.get('product_id')
        
        if not product_id:
            return Response(
                {'error': 'product_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from ...products.models import Product
            from ..models import SavedForLater
            
            product = Product.objects.get(id=product_id)
            cart_item = cart.items.get(product=product)
            
            # Create saved for later item
            saved_item, created = SavedForLater.objects.get_or_create(
                user=request.user,
                product=product,
                defaults={'quantity': cart_item.quantity}
            )
            
            if not created:
                saved_item.quantity += cart_item.quantity
                saved_item.save()
            
            # Remove from cart
            cart_item.delete()
            
            # Log activity
            UserActivityLog.objects.create(
                user=request.user,
                activity_type='cart_save_for_later',
                description=f'Saved {product.name} for later',
                metadata={
                    'product_id': product.id,
                    'product_name': product.name,
                    'quantity': saved_item.quantity
                }
            )
            
            from .serializers import SavedForLaterSerializer
            return Response(
                SavedForLaterSerializer(saved_item).data,
                status=status.HTTP_201_CREATED
            )
            
        except Product.DoesNotExist:
            return Response(
                {'error': 'Product not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except cart.items.model.DoesNotExist:
            return Response(
                {'error': 'Item not in cart'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class SavedForLaterViewSet(viewsets.ModelViewSet):
    """ViewSet for saved for later items"""
    serializer_class = SavedForLaterSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ['saved_at']
    ordering = ['-saved_at']
    
    def get_queryset(self):
        return SavedForLater.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def move_to_cart(self, request, pk=None):
        """Move item from saved for later to cart"""
        saved_item = self.get_object()
        
        try:
            cart_item = saved_item.move_to_cart()
            
            # Log activity
            UserActivityLog.objects.create(
                user=request.user,
                activity_type='cart_add',
                description=f'Moved {saved_item.product.name} from saved to cart',
                metadata={
                    'product_id': saved_item.product.id,
                    'product_name': saved_item.product.name,
                    'quantity': saved_item.quantity,
                    'source': 'saved_for_later'
                },
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            cart_serializer = CartItemSerializer(cart_item)
            return Response(cart_serializer.data, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
