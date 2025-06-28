from django.shortcuts import get_object_or_404
from django.db import transaction
from rest_framework import status, viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from decimal import Decimal

from ..models import Order, OrderItem, ReturnRequest
from .serializers import (
    OrderSerializer, OrderSummarySerializer, CreateOrderSerializer,
    ReturnRequestSerializer, OrderUpdateSerializer
)
from src.apps.cart.models import Cart
from src.apps.accounts.models import Address, UserActivityLog
from src.apps.products.models import Product


class OrderViewSet(viewsets.ModelViewSet):
    """ViewSet for order management"""
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'payment_status']
    search_fields = ['order_number']
    ordering_fields = ['created_at', 'total_amount']
    ordering = ['-created_at']
    lookup_field = 'order_number'
    
    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related(
            'items__product', 'status_history', 'shipping_updates'
        )
    
    def get_serializer_class(self):
        if self.action == 'list':
            return OrderSummarySerializer
        elif self.action == 'create':
            return CreateOrderSerializer
        elif self.action in ['update', 'partial_update'] and self.request.user.is_staff:
            return OrderUpdateSerializer
        return OrderSerializer
    
    def create(self, request):
        """Create order from cart"""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            return self._create_order_from_cart(request, serializer.validated_data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @transaction.atomic
    def _create_order_from_cart(self, request, validated_data):
        """Create order from user's cart"""
        user = request.user
        
        # Get user's cart
        try:
            cart = Cart.objects.get(user=user)
        except Cart.DoesNotExist:
            return Response({'error': 'Cart not found'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not cart.items.exists():
            return Response({'error': 'Cart is empty'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get addresses
        shipping_address = get_object_or_404(
            Address, id=validated_data['shipping_address_id'], user=user, is_active=True
        )
        billing_address = None
        if validated_data.get('billing_address_id'):
            billing_address = get_object_or_404(
                Address, id=validated_data['billing_address_id'], user=user, is_active=True
            )
        
        # Validate stock availability
        for item in cart.items.all():
            if not item.product.is_available:
                return Response({
                    'error': f'Product {item.product.name} is no longer available'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if item.product.stock_quantity < item.quantity:
                return Response({
                    'error': f'Only {item.product.stock_quantity} items available for {item.product.name}'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Calculate totals
        subtotal = cart.subtotal
        shipping_cost = self._calculate_shipping_cost(cart, shipping_address)
        tax_amount = self._calculate_tax(subtotal)
        total_amount = subtotal + shipping_cost + tax_amount
        
        # Create order
        order = Order.objects.create(
            user=user,
            email=user.email,
            phone_number=getattr(user.profile, 'phone_number', ''),
            shipping_address=self._serialize_address(shipping_address),
            billing_address=self._serialize_address(billing_address) if billing_address else None,
            subtotal=subtotal,
            shipping_cost=shipping_cost,
            tax_amount=tax_amount,
            total_amount=total_amount,
            payment_method=validated_data.get('payment_method', 'paystack'),
            special_instructions=validated_data.get('special_instructions', '')
        )
        
        # Create order items and update stock
        for cart_item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                unit_price=cart_item.unit_price,
                quantity=cart_item.quantity
            )
            
            # Update product stock
            cart_item.product.quantity -= cart_item.quantity
            cart_item.product.save()
        
        # Clear cart
        cart.clear()
        
        # Log activity
        UserActivityLog.objects.create(
            user=user,
            activity_type='order_placed',
            description=f'Order {order.order_number} placed',
            metadata={
                'order_id': str(order.id),
                'order_number': order.order_number,
                'total_amount': str(order.total_amount),
                'total_items': order.total_items
            },
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        serializer = OrderSerializer(order)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def _calculate_shipping_cost(self, cart, address):
        """Calculate shipping cost based on cart and address"""
        # Simple shipping calculation - can be enhanced
        base_shipping = Decimal('1000.00')  # Base shipping cost in Naira
        
        # Free shipping for orders over 50,000 Naira
        if cart.subtotal >= Decimal('50000.00'):
            return Decimal('0.00')
        
        # Weight-based shipping
        weight_cost = cart.total_weight * Decimal('100.00')  # 100 Naira per kg
        
        return base_shipping + weight_cost
    
    def _calculate_tax(self, subtotal):
        """Calculate tax amount"""
        # VAT is 7.5% in Nigeria
        return subtotal * Decimal('0.075')
    
    def _serialize_address(self, address):
        """Serialize address to JSON"""
        if not address:
            return None
        
        return {
            'full_name': address.full_name,
            'company': address.company,
            'address_line_1': address.address_line_1,
            'address_line_2': address.address_line_2,
            'city': address.city,
            'state': address.state,
            'postal_code': address.postal_code,
            'country': address.country,
            'phone_number': address.phone_number
        }
    
    @action(detail=True, methods=['post'], url_path='cancel_order')
    def cancel_order_action(self, request, order_number=None):
        """Cancel an order"""
        order = self.get_object()
        
        if not order.can_cancel:
            return Response({
                'error': 'Order cannot be cancelled'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        reason = request.data.get('reason', 'Cancelled by customer')
        
        try:
            order.cancel_order(reason)
            return Response({'message': 'Order cancelled successfully'})
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def tracking(self, request, order_number=None):
        """Get order tracking information"""
        order = self.get_object()
        
        tracking_info = {
            'order_number': order.order_number,
            'status': order.status,
            'tracking_number': order.tracking_number,
            'courier_service': order.courier_service,
            'estimated_delivery_date': order.estimated_delivery_date,
            'actual_delivery_date': order.actual_delivery_date,
            'shipping_updates': []
        }
        
        for update in order.shipping_updates.all():
            tracking_info['shipping_updates'].append({
                'type': update.update_type,
                'message': update.message,
                'location': update.location,
                'timestamp': update.timestamp
            })
        
        return Response(tracking_info)
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get order summary statistics"""
        queryset = self.get_queryset()
        
        summary = {
            'total_orders': queryset.count(),
            'pending_orders': queryset.filter(status='pending').count(),
            'delivered_orders': queryset.filter(status='delivered').count(),
            'completed_orders': queryset.filter(status='delivered').count(),
            'total_spent': sum(order.total_amount for order in queryset),
            'recent_orders': []
        }
        
        # Get recent orders
        recent = queryset[:5]
        for order in recent:
            summary['recent_orders'].append({
                'order_number': order.order_number,
                'status': order.status,
                'total_amount': order.total_amount,
                'created_at': order.created_at
            })
        
        return Response(summary)
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class ReturnRequestViewSet(viewsets.ModelViewSet):
    """ViewSet for return requests"""
    serializer_class = ReturnRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['status', 'reason']
    ordering_fields = ['requested_at']
    ordering = ['-requested_at']
    
    def get_queryset(self):
        return ReturnRequest.objects.filter(order__user=self.request.user)
    
    def perform_create(self, serializer):
        # The order validation is handled in the serializer
        serializer.save()
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def approve(self, request, pk=None):
        """Approve return request (admin only)"""
        return_request = self.get_object()
        return_request.status = 'approved'
        return_request.save()
        
        return Response({'message': 'Return request approved'})
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def reject(self, request, pk=None):
        """Reject return request (admin only)"""
        return_request = self.get_object()
        return_request.status = 'rejected'
        return_request.admin_notes = request.data.get('reason', '')
        return_request.save()
        
        return Response({'message': 'Return request rejected'})
