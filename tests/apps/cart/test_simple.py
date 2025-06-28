"""
Simple test to check cart functionality
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from src.apps.cart.models import Cart
from src.apps.products.models import Product, Brand, Category

User = get_user_model()


class SimpleCartTest(TestCase):
    """Simple cart test"""
    
    def test_cart_creation(self):
        """Test basic cart creation"""
        user = User.objects.create_user(
            first_name="John",
            last_name="Doe", 
            email="test@example.com",
            password="testpass123"
        )
        
        # Cart should be auto-created via signal
        self.assertTrue(hasattr(user, 'cart'))
        self.assertIsInstance(user.cart, Cart)
