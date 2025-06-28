"""
Simple test to check orders functionality
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from src.apps.orders.models import Order
from src.apps.products.models import Product, Brand, Category

User = get_user_model()


class SimpleOrderTest(TestCase):
    """Simple order test"""
    
    def test_order_creation(self):
        """Test basic order creation"""
        user = User.objects.create_user(
            first_name="John",
            last_name="Doe", 
            email="test@example.com",
            password="testpass123"
        )
        
        order = Order.objects.create(
            user=user,
            email=user.email,
            shipping_address={'address': 'test'},
            subtotal=100.00,
            total_amount=100.00
        )
        
        self.assertIsNotNone(order.order_number)
        self.assertEqual(order.user, user)
