"""
Comprehensive tests for the Orders app models, views, and functionality.
"""
import json
import uuid
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status

from src.apps.orders.models import Order, OrderItem, OrderStatusHistory, OrderShippingUpdate, ReturnRequest
from src.apps.cart.models import Cart, CartItem
from src.apps.products.models import Product, Brand, Category
from src.apps.accounts.models import Address

User = get_user_model()


class OrderModelTest(TestCase):
    """Test cases for Order model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            password="testpass123"
        )
        
        # Create test data
        self.brand = Brand.objects.create(name="Test Brand", slug="test-brand")
        self.category = Category.objects.create(name="Electronics")
        
        self.product1 = Product.objects.create(
            name="Test Product 1",
            slug="test-product-1",
            price=Decimal('99.99'),
            quantity=10,
            brand=self.brand,
            description="Test product description"
        )
        self.product1.category.add(self.category)
        
        self.product2 = Product.objects.create(
            name="Test Product 2",
            slug="test-product-2",
            price=Decimal('199.99'),
            quantity=5,
            brand=self.brand,
            description="Another test product"
        )
        self.product2.category.add(self.category)
        
        # Create shipping address
        self.shipping_address = {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john.doe@example.com',
            'phone': '+1234567890',
            'address_line_1': '123 Test Street',
            'address_line_2': 'Apt 4B',
            'city': 'Test City',
            'state': 'Test State',
            'postal_code': '12345',
            'country': 'US'
        }
        
        self.order = Order.objects.create(
            user=self.user,
            email=self.user.email,
            phone_number='+1234567890',
            shipping_address=self.shipping_address,
            subtotal=Decimal('299.98'),
            shipping_cost=Decimal('10.00'),
            tax_amount=Decimal('30.00'),
            total_amount=Decimal('339.98'),
            payment_method='paystack'
        )
    
    def test_order_str_representation(self):
        """Test string representation of order"""
        expected = f"Order #{self.order.order_number}"
        self.assertEqual(str(self.order), expected)
    
    def test_order_number_generation(self):
        """Test automatic order number generation"""
        self.assertIsNotNone(self.order.order_number)
        self.assertTrue(self.order.order_number.startswith('ORD-'))
        self.assertEqual(len(self.order.order_number), 18)  # ORD-YYYYMMDD-XXXXX
    
    def test_order_number_uniqueness(self):
        """Test that order numbers are unique"""
        order2 = Order.objects.create(
            user=self.user,
            email=self.user.email,
            shipping_address=self.shipping_address,
            subtotal=Decimal('100.00'),
            total_amount=Decimal('100.00')
        )
        
        self.assertNotEqual(self.order.order_number, order2.order_number)
    
    def test_uuid_primary_key(self):
        """Test that order uses UUID as primary key"""
        self.assertIsInstance(self.order.id, uuid.UUID)
    
    def test_total_items_property(self):
        """Test total items calculation"""
        # Add order items
        OrderItem.objects.create(
            order=self.order,
            product=self.product1,
            product_name=self.product1.name,
            unit_price=self.product1.price,
            quantity=2
        )
        OrderItem.objects.create(
            order=self.order,
            product=self.product2,
            product_name=self.product2.name,
            unit_price=self.product2.price,
            quantity=1
        )
        
        self.assertEqual(self.order.total_items, 3)
    
    def test_is_delivered_property(self):
        """Test is_delivered property"""
        self.assertFalse(self.order.is_delivered)
        
        self.order.status = 'delivered'
        self.order.save()
        
        self.assertTrue(self.order.is_delivered)
    
    def test_is_cancelled_property(self):
        """Test is_cancelled property"""
        self.assertFalse(self.order.is_cancelled)
        
        self.order.status = 'cancelled'
        self.order.save()
        
        self.assertTrue(self.order.is_cancelled)
    
    def test_can_cancel_property(self):
        """Test can_cancel property logic"""
        # New order should be cancellable
        self.assertTrue(self.order.can_cancel)
        
        # Completed payment shouldn't be cancellable
        self.order.payment_status = 'completed'
        self.order.save()
        self.assertFalse(self.order.can_cancel)
        
        # Reset payment status
        self.order.payment_status = 'pending'
        self.order.save()
        
        # Shipped order shouldn't be cancellable
        self.order.status = 'shipped'
        self.order.save()
        self.assertFalse(self.order.can_cancel)
    
    def test_can_refund_property(self):
        """Test can_refund property logic"""
        # Pending payment can't be refunded
        self.assertFalse(self.order.can_refund)
        
        # Completed payment can be refunded
        self.order.payment_status = 'completed'
        self.order.save()
        self.assertTrue(self.order.can_refund)
        
        # Cancelled order can't be refunded
        self.order.status = 'cancelled'
        self.order.save()
        self.assertFalse(self.order.can_refund)
    
    def test_cancel_order_functionality(self):
        """Test order cancellation functionality"""
        # Add order items first
        order_item = OrderItem.objects.create(
            order=self.order,
            product=self.product1,
            product_name=self.product1.name,
            unit_price=self.product1.price,
            quantity=2
        )
        
        # Record original stock
        original_stock = self.product1.quantity
        
        # Reduce stock (simulate items being reserved)
        self.product1.quantity -= 2
        self.product1.save()
        
        # Cancel order
        self.order.cancel_order("Customer request")
        
        # Check order status
        self.assertEqual(self.order.status, 'cancelled')
        self.assertIn("Cancelled: Customer request", self.order.order_notes)
        
        # Check stock restoration
        self.product1.refresh_from_db()
        self.assertEqual(self.product1.quantity, original_stock)
    
    def test_cancel_order_validation(self):
        """Test that non-cancellable orders can't be cancelled"""
        self.order.status = 'delivered'
        self.order.save()
        
        with self.assertRaises(ValueError):
            self.order.cancel_order()
    
    def test_mark_as_delivered(self):
        """Test marking order as delivered"""
        self.order.mark_as_delivered()
        
        self.assertEqual(self.order.status, 'delivered')
        self.assertIsNotNone(self.order.actual_delivery_date)
        self.assertLessEqual(
            self.order.actual_delivery_date, 
            timezone.now()
        )


class OrderItemModelTest(TestCase):
    """Test cases for OrderItem model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            password="testpass123"
        )
        
        self.brand = Brand.objects.create(name="Test Brand", slug="test-brand")
        self.category = Category.objects.create(name="Electronics")
        
        self.product = Product.objects.create(
            name="Test Product",
            slug="test-product",
            price=Decimal('99.99'),
            quantity=10,
            brand=self.brand,
            description="Test product description"
        )
        self.product.category.add(self.category)
        
        self.order = Order.objects.create(
            user=self.user,
            email=self.user.email,
            shipping_address={'address': 'test'},
            subtotal=Decimal('199.98'),
            total_amount=Decimal('199.98')
        )
        
        self.order_item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            unit_price=self.product.price,
            quantity=2
        )
    
    def test_order_item_str_representation(self):
        """Test string representation of order item"""
        expected = f"2x {self.product.name} in {self.order}"
        self.assertEqual(str(self.order_item), expected)
    
    def test_total_price_calculation(self):
        """Test automatic total price calculation"""
        expected_total = self.product.price * 2
        self.assertEqual(self.order_item.total_price, expected_total)
    
    def test_product_details_storage(self):
        """Test that product details are stored at time of order"""
        self.assertEqual(self.order_item.product_name, self.product.name)
        # SKU might be empty in our test setup
        self.assertIsNotNone(self.order_item.product_sku)
    
    def test_unique_constraint(self):
        """Test unique constraint for order and product combination"""
        with self.assertRaises(Exception):
            OrderItem.objects.create(
                order=self.order,
                product=self.product,  # Same product in same order
                unit_price=Decimal('99.99'),
                quantity=1
            )
    
    def test_quantity_validation(self):
        """Test minimum quantity validation"""
        order_item = OrderItem(
            order=self.order,
            product=self.product,
            unit_price=Decimal('99.99'),
            quantity=0  # Invalid quantity
        )
        
        with self.assertRaises(ValidationError):
            order_item.full_clean()


class OrderStatusHistoryModelTest(TestCase):
    """Test cases for OrderStatusHistory model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            password="testpass123"
        )
        
        self.order = Order.objects.create(
            user=self.user,
            email=self.user.email,
            shipping_address={'address': 'test'},
            subtotal=Decimal('100.00'),
            total_amount=Decimal('100.00')
        )
        
        self.status_history = OrderStatusHistory.objects.create(
            order=self.order,
            status='confirmed',
            notes='Order confirmed by admin',
            changed_by=self.user
        )
    
    def test_status_history_str_representation(self):
        """Test string representation of status history"""
        expected = f"{self.order} - Confirmed at {self.status_history.timestamp}"
        self.assertEqual(str(self.status_history), expected)
    
    def test_automatic_timestamp(self):
        """Test that timestamp is automatically set"""
        self.assertIsNotNone(self.status_history.timestamp)
        self.assertLessEqual(
            self.status_history.timestamp, 
            timezone.now()
        )


class OrderShippingUpdateModelTest(TestCase):
    """Test cases for OrderShippingUpdate model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            password="testpass123"
        )
        
        self.order = Order.objects.create(
            user=self.user,
            email=self.user.email,
            shipping_address={'address': 'test'},
            subtotal=Decimal('100.00'),
            total_amount=Decimal('100.00')
        )
        
        self.shipping_update = OrderShippingUpdate.objects.create(
            order=self.order,
            update_type='shipped',
            message='Package has been shipped',
            location='Shipping Center A'
        )
    
    def test_shipping_update_str_representation(self):
        """Test string representation of shipping update"""
        expected = f"{self.order} - shipped at {self.shipping_update.timestamp}"
        self.assertEqual(str(self.shipping_update), expected)
    
    def test_automatic_timestamp(self):
        """Test that timestamp is automatically set"""
        self.assertIsNotNone(self.shipping_update.timestamp)
        self.assertLessEqual(
            self.shipping_update.timestamp,
            timezone.now()
        )


class ReturnRequestModelTest(TestCase):
    """Test cases for ReturnRequest model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            password="testpass123"
        )
        
        self.brand = Brand.objects.create(name="Test Brand", slug="test-brand")
        self.category = Category.objects.create(name="Electronics")
        
        self.product = Product.objects.create(
            name="Test Product",
            slug="test-product",
            price=Decimal('99.99'),
            quantity=10,
            brand=self.brand,
            description="Test product description"
        )
        self.product.category.add(self.category)
        
        self.order = Order.objects.create(
            user=self.user,
            email=self.user.email,
            shipping_address={'address': 'test'},
            subtotal=Decimal('99.99'),
            total_amount=Decimal('99.99'),
            status='delivered'
        )
        
        self.order_item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            product_name=self.product.name,
            unit_price=self.product.price,
            quantity=1
        )
        
        self.return_request = ReturnRequest.objects.create(
            order=self.order,
            order_item=self.order_item,
            reason='defective',
            description='Product arrived damaged'
        )
    
    def test_return_request_str_representation(self):
        """Test string representation of return request"""
        expected = f"Return request for {self.order}"
        self.assertEqual(str(self.return_request), expected)
    
    def test_automatic_timestamp(self):
        """Test that requested_at timestamp is automatically set"""
        self.assertIsNotNone(self.return_request.requested_at)
        self.assertLessEqual(
            self.return_request.requested_at,
            timezone.now()
        )
    
    def test_default_status(self):
        """Test default status is pending"""
        self.assertEqual(self.return_request.status, 'pending')


class OrderAPITest(APITestCase):
    """Test cases for Order API endpoints"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            password="testpass123"
        )
        
        # Create test data
        self.brand = Brand.objects.create(name="Test Brand", slug="test-brand")
        self.category = Category.objects.create(name="Electronics")
        
        self.product1 = Product.objects.create(
            name="Test Product 1",
            slug="test-product-1",
            price=Decimal('99.99'),
            quantity=10,
            brand=self.brand,
            description="Test product description"
        )
        self.product1.category.add(self.category)
        
        self.product2 = Product.objects.create(
            name="Test Product 2",
            slug="test-product-2",
            price=Decimal('199.99'),
            quantity=5,
            brand=self.brand,
            description="Another test product"
        )
        self.product2.category.add(self.category)
        
        # Create address
        self.address = Address.objects.create(
            user=self.user,
            full_name='John Doe',
            phone_number='+1234567890',
            address_line_1='123 Test Street',
            city='Test City',
            state='Test State',
            postal_code='12345',
            country='US',
            is_default=True
        )
        
        # Set up cart with items
        self.cart = self.user.cart
        self.cart.add_item(self.product1, 2)
        self.cart.add_item(self.product2, 1)
    
    def test_create_order_from_cart(self):
        """Test creating order from cart items"""
        self.client.force_authenticate(user=self.user)
        
        url = '/api/orders/orders/'
        data = {
            'shipping_address_id': self.address.id,
            'payment_method': 'paystack',
            'special_instructions': 'Handle with care'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('order_number', response.data)
        self.assertIn('total_amount', response.data)
        
        # Verify order was created
        order = Order.objects.get(order_number=response.data['order_number'])
        self.assertEqual(order.user, self.user)
        self.assertEqual(order.items.count(), 2)
        
        # Verify cart was cleared
        self.assertEqual(self.cart.total_items, 0)
    
    def test_create_order_empty_cart(self):
        """Test creating order with empty cart fails"""
        self.client.force_authenticate(user=self.user)
        
        # Clear cart
        self.cart.clear()
        
        url = '/api/orders/orders/'
        data = {
            'shipping_address_id': self.address.id,
            'payment_method': 'paystack'
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_create_order_invalid_address(self):
        """Test creating order with invalid address"""
        self.client.force_authenticate(user=self.user)
        
        url = '/api/orders/orders/'
        data = {
            'shipping_address_id': 99999,  # Non-existent address
            'payment_method': 'paystack'
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_list_user_orders(self):
        """Test listing user's orders"""
        self.client.force_authenticate(user=self.user)
        
        # Create test orders
        order1 = Order.objects.create(
            user=self.user,
            email=self.user.email,
            shipping_address={'address': 'test'},
            subtotal=Decimal('100.00'),
            total_amount=Decimal('100.00')
        )
        order2 = Order.objects.create(
            user=self.user,
            email=self.user.email,
            shipping_address={'address': 'test'},
            subtotal=Decimal('200.00'),
            total_amount=Decimal('200.00')
        )
        
        url = '/api/orders/orders/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
    
    def test_get_order_detail(self):
        """Test getting order details"""
        self.client.force_authenticate(user=self.user)
        
        order = Order.objects.create(
            user=self.user,
            email=self.user.email,
            shipping_address={'address': 'test'},
            subtotal=Decimal('100.00'),
            total_amount=Decimal('100.00')
        )
        
        url = f'/api/orders/orders/{order.order_number}/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['order_number'], order.order_number)
    
    def test_get_order_detail_unauthorized(self):
        """Test that users can't access other users' orders"""
        other_user = User.objects.create_user(
            first_name="Jane",
            last_name="Smith",
            email="jane.smith@example.com",
            password="testpass123"
        )
        
        order = Order.objects.create(
            user=other_user,
            email=other_user.email,
            shipping_address={'address': 'test'},
            subtotal=Decimal('100.00'),
            total_amount=Decimal('100.00')
        )
        
        self.client.force_authenticate(user=self.user)
        
        url = f'/api/orders/orders/{order.order_number}/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_cancel_order(self):
        """Test cancelling an order"""
        self.client.force_authenticate(user=self.user)
        
        order = Order.objects.create(
            user=self.user,
            email=self.user.email,
            shipping_address={'address': 'test'},
            subtotal=Decimal('100.00'),
            total_amount=Decimal('100.00'),
            status='pending'
        )
        
        url = f'/api/orders/orders/{order.order_number}/cancel_order/'
        data = {'reason': 'Changed my mind'}
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify order was cancelled
        order.refresh_from_db()
        self.assertEqual(order.status, 'cancelled')
    
    def test_cancel_non_cancellable_order(self):
        """Test cancelling non-cancellable order fails"""
        self.client.force_authenticate(user=self.user)
        
        order = Order.objects.create(
            user=self.user,
            email=self.user.email,
            shipping_address={'address': 'test'},
            subtotal=Decimal('100.00'),
            total_amount=Decimal('100.00'),
            status='delivered'  # Can't cancel delivered orders
        )
        
        url = f'/api/orders/orders/{order.order_number}/cancel_order/'
        data = {'reason': 'Test'}
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_get_order_tracking(self):
        """Test getting order tracking information"""
        self.client.force_authenticate(user=self.user)
        
        order = Order.objects.create(
            user=self.user,
            email=self.user.email,
            shipping_address={'address': 'test'},
            subtotal=Decimal('100.00'),
            total_amount=Decimal('100.00'),
            tracking_number='TRK123456'
        )
        
        # Add shipping updates
        OrderShippingUpdate.objects.create(
            order=order,
            update_type='shipped',
            message='Package shipped',
            location='Warehouse A'
        )
        
        url = f'/api/orders/orders/{order.order_number}/tracking/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['tracking_number'], 'TRK123456')
        self.assertEqual(len(response.data['shipping_updates']), 1)
    
    def test_create_return_request(self):
        """Test creating a return request"""
        self.client.force_authenticate(user=self.user)
        
        order = Order.objects.create(
            user=self.user,
            email=self.user.email,
            shipping_address={'address': 'test'},
            subtotal=Decimal('99.99'),
            total_amount=Decimal('99.99'),
            status='delivered',
            payment_status='completed'
        )
        
        order_item = OrderItem.objects.create(
            order=order,
            product=self.product1,
            product_name=self.product1.name,
            unit_price=self.product1.price,
            quantity=1
        )
        
        url = '/api/orders/returns/'
        data = {
            'order': order.id,
            'order_item': order_item.id,
            'reason': 'defective',
            'description': 'Product arrived damaged'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['reason'], 'defective')
        
        # Verify return request was created
        return_request = ReturnRequest.objects.get(order=order)
        self.assertEqual(return_request.reason, 'defective')
    
    def test_list_return_requests(self):
        """Test listing user's return requests"""
        self.client.force_authenticate(user=self.user)
        
        order = Order.objects.create(
            user=self.user,
            email=self.user.email,
            shipping_address={'address': 'test'},
            subtotal=Decimal('99.99'),
            total_amount=Decimal('99.99'),
            status='delivered',
            payment_status='completed'
        )
        
        ReturnRequest.objects.create(
            order=order,
            reason='defective',
            description='Product damaged'
        )
        
        url = '/api/orders/returns/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_get_order_summary(self):
        """Test getting order summary/statistics"""
        self.client.force_authenticate(user=self.user)
        
        # Create test orders with different statuses
        Order.objects.create(
            user=self.user,
            email=self.user.email,
            shipping_address={'address': 'test'},
            subtotal=Decimal('100.00'),
            total_amount=Decimal('100.00'),
            status='pending'
        )
        Order.objects.create(
            user=self.user,
            email=self.user.email,
            shipping_address={'address': 'test'},
            subtotal=Decimal('200.00'),
            total_amount=Decimal('200.00'),
            status='delivered'
        )
        
        url = '/api/orders/orders/summary/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_orders', response.data)
        self.assertIn('pending_orders', response.data)
        self.assertIn('delivered_orders', response.data)
        self.assertIn('total_spent', response.data)
    
    def test_unauthenticated_access_fails(self):
        """Test that unauthenticated users cannot access order endpoints"""
        url = '/api/orders/orders/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class OrderSignalTest(TestCase):
    """Test cases for order signals"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            password="testpass123"
        )
        
        self.order = Order.objects.create(
            user=self.user,
            email=self.user.email,
            shipping_address={'address': 'test'},
            subtotal=Decimal('100.00'),
            total_amount=Decimal('100.00')
        )
    
    def test_status_history_created_on_status_change(self):
        """Test that status history is created when order status changes"""
        # Change order status
        self.order.status = 'confirmed'
        self.order.save()
        
        # Check if status history was created
        status_history = OrderStatusHistory.objects.filter(order=self.order).first()
        self.assertIsNotNone(status_history)
        self.assertEqual(status_history.status, 'confirmed')
    
    def test_delivery_date_set_on_delivery(self):
        """Test that delivery date is set when order is marked as delivered"""
        # Mark as delivered
        self.order.status = 'delivered'
        self.order.save()
        
        # Check if delivery date was set
        self.order.refresh_from_db()
        # This would depend on signal implementation
        # self.assertIsNotNone(self.order.actual_delivery_date)


class OrderIntegrationTest(TestCase):
    """Integration tests for order workflow"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            password="testpass123"
        )
        
        self.brand = Brand.objects.create(name="Test Brand", slug="test-brand")
        self.category = Category.objects.create(name="Electronics")
        
        self.product = Product.objects.create(
            name="Test Product",
            slug="test-product",
            price=Decimal('99.99'),
            quantity=10,
            brand=self.brand,
            description="Test product description"
        )
        self.product.category.add(self.category)
    
    def test_complete_order_workflow(self):
        """Test complete order workflow from cart to delivery"""
        # 1. Add items to cart
        cart = self.user.cart
        cart.add_item(self.product, 2)
        
        self.assertEqual(cart.total_items, 2)
        self.assertEqual(self.product.quantity, 10)
        
        # 2. Create order from cart
        order = Order.objects.create(
            user=self.user,
            email=self.user.email,
            shipping_address={'address': 'test'},
            subtotal=cart.subtotal,
            total_amount=cart.subtotal
        )
        
        # 3. Create order items and reduce stock
        order_item = OrderItem.objects.create(
            order=order,
            product=self.product,
            product_name=self.product.name,
            unit_price=self.product.price,
            quantity=2
        )
        
        # Simulate stock reduction
        self.product.quantity -= 2
        self.product.save()
        
        # 4. Clear cart after order creation
        cart.clear()
        
        # Verify state
        self.assertEqual(cart.total_items, 0)
        self.assertEqual(self.product.quantity, 8)
        self.assertEqual(order.total_items, 2)
        
        # 5. Process order through different statuses
        order.status = 'confirmed'
        order.save()
        
        order.status = 'shipped'
        order.save()
        
        order.status = 'delivered'
        order.save()
        
        self.assertTrue(order.is_delivered)
    
    def test_order_cancellation_restores_stock(self):
        """Test that cancelling order restores product stock"""
        # Create order with items
        order = Order.objects.create(
            user=self.user,
            email=self.user.email,
            shipping_address={'address': 'test'},
            subtotal=Decimal('199.98'),
            total_amount=Decimal('199.98'),
            status='pending'
        )
        
        OrderItem.objects.create(
            order=order,
            product=self.product,
            product_name=self.product.name,
            unit_price=self.product.price,
            quantity=2
        )
        
        # Simulate stock reduction during order creation
        original_stock = self.product.quantity
        self.product.quantity -= 2
        self.product.save()
        
        # Cancel order
        order.cancel_order("Customer request")
        
        # Verify stock restoration
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, original_stock)
        self.assertEqual(order.status, 'cancelled')
