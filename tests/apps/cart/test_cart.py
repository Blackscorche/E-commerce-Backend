"""
Comprehensive tests for the Cart app models, views, and functionality.
"""
import json
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from rest_framework.test import APITestCase
from rest_framework import status

from src.apps.cart.models import Cart, CartItem, SavedForLater
from src.apps.products.models import Product, Brand, Category

User = get_user_model()


class CartModelTest(TestCase):
    """Test cases for Cart model"""
    
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
            original_price=Decimal('249.99'),
            quantity=5,
            brand=self.brand,
            description="Another test product"
        )
        self.product2.category.add(self.category)
    
    def test_cart_auto_creation_for_user(self):
        """Test that cart is automatically created for user by signal"""
        self.assertTrue(hasattr(self.user, 'cart'))
        self.assertIsInstance(self.user.cart, Cart)
    
    def test_cart_str_representation(self):
        """Test string representation of cart"""
        cart = self.user.cart
        expected = f"Cart for {self.user.email}"
        self.assertEqual(str(cart), expected)
    
    def test_guest_cart_creation(self):
        """Test guest cart creation with session key"""
        guest_cart = Cart.objects.create(session_key="test_session_123")
        expected = "Guest Cart test_session_123"
        self.assertEqual(str(guest_cart), expected)
    
    def test_cart_constraint_validation(self):
        """Test that cart must have either user or session key"""
        # This should raise a database error due to constraint
        with self.assertRaises(Exception):
            Cart.objects.create()  # No user or session_key
    
    def test_add_item_to_cart(self):
        """Test adding items to cart"""
        cart = self.user.cart
        
        # Add item
        cart_item = cart.add_item(self.product1, 2)
        
        self.assertEqual(cart_item.quantity, 2)
        self.assertEqual(cart_item.product, self.product1)
        self.assertEqual(cart.total_items, 2)
    
    def test_add_existing_item_increases_quantity(self):
        """Test adding existing item increases quantity"""
        cart = self.user.cart
        
        # Add item first time
        cart.add_item(self.product1, 2)
        
        # Add same item again
        cart.add_item(self.product1, 3)
        
        cart_item = cart.items.get(product=self.product1)
        self.assertEqual(cart_item.quantity, 5)
        self.assertEqual(cart.total_items, 5)
    
    def test_add_item_stock_validation(self):
        """Test that adding items validates stock availability"""
        cart = self.user.cart
        
        # Try to add more than available stock
        with self.assertRaises(ValidationError):
            cart.add_item(self.product1, 15)  # Only 10 in stock
    
    def test_add_unavailable_product(self):
        """Test adding unavailable product raises error"""
        cart = self.user.cart
        self.product1.quantity = 0
        self.product1.save()
        
        with self.assertRaises(ValidationError):
            cart.add_item(self.product1, 1)
    
    def test_update_item_quantity(self):
        """Test updating item quantity in cart"""
        cart = self.user.cart
        cart.add_item(self.product1, 2)
        
        # Update quantity
        updated_item = cart.update_item_quantity(self.product1, 5)
        
        self.assertEqual(updated_item.quantity, 5)
        self.assertEqual(cart.total_items, 5)
    
    def test_update_item_quantity_to_zero_removes_item(self):
        """Test updating quantity to 0 removes item"""
        cart = self.user.cart
        cart.add_item(self.product1, 2)
        
        # Update to 0
        result = cart.update_item_quantity(self.product1, 0)
        
        self.assertIsNone(result)
        self.assertEqual(cart.total_items, 0)
        self.assertFalse(cart.items.filter(product=self.product1).exists())
    
    def test_remove_item_from_cart(self):
        """Test removing item from cart"""
        cart = self.user.cart
        cart.add_item(self.product1, 2)
        cart.add_item(self.product2, 1)
        
        # Remove one item
        cart.remove_item(self.product1)
        
        self.assertFalse(cart.items.filter(product=self.product1).exists())
        self.assertEqual(cart.total_items, 1)
    
    def test_clear_cart(self):
        """Test clearing all items from cart"""
        cart = self.user.cart
        cart.add_item(self.product1, 2)
        cart.add_item(self.product2, 1)
        
        cart.clear()
        
        self.assertEqual(cart.total_items, 0)
        self.assertEqual(cart.items.count(), 0)
    
    def test_cart_subtotal_calculation(self):
        """Test cart subtotal calculation"""
        cart = self.user.cart
        cart.add_item(self.product1, 2)  # 2 * 99.99 = 199.98
        cart.add_item(self.product2, 1)  # 1 * 199.99 = 199.99
        
        expected_subtotal = Decimal('399.97')
        self.assertEqual(cart.subtotal, expected_subtotal)
    
    def test_cart_total_weight_calculation(self):
        """Test cart total weight calculation"""
        cart = self.user.cart
        
        # Set weights in specifications
        self.product1.specifications = {'weight': 1.5}
        self.product1.save()
        self.product2.specifications = {'weight': 2.0}
        self.product2.save()
        
        cart.add_item(self.product1, 2)  # 2 * 1.5 = 3.0
        cart.add_item(self.product2, 1)  # 1 * 2.0 = 2.0
        
        expected_weight = Decimal('5.0')
        self.assertEqual(cart.total_weight, expected_weight)
    
    def test_merge_carts(self):
        """Test merging two carts"""
        # Create another user with cart
        user2 = User.objects.create_user(
            first_name="Jane",
            last_name="Smith",
            email="jane.smith@example.com",
            password="testpass123"
        )
        
        # Add items to both carts
        self.user.cart.add_item(self.product1, 2)
        user2.cart.add_item(self.product1, 1)  # Same product
        user2.cart.add_item(self.product2, 2)  # Different product
        
        # Merge user2's cart into user1's cart
        self.user.cart.merge_with_cart(user2.cart)
        
        # Check results
        item1 = self.user.cart.items.get(product=self.product1)
        item2 = self.user.cart.items.get(product=self.product2)
        
        self.assertEqual(item1.quantity, 3)  # 2 + 1
        self.assertEqual(item2.quantity, 2)
        self.assertEqual(self.user.cart.total_items, 5)
        
        # user2's cart should be deleted
        self.assertFalse(Cart.objects.filter(user=user2).exists())


class CartItemModelTest(TestCase):
    """Test cases for CartItem model"""
    
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
            original_price=Decimal('119.99'),
            quantity=10,
            brand=self.brand,
            description="Test product description"
        )
        self.product.category.add(self.category)
        
        self.cart = self.user.cart
        self.cart_item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=2
        )
    
    def test_cart_item_str_representation(self):
        """Test string representation of cart item"""
        expected = f"2x {self.product.name} in {self.cart}"
        self.assertEqual(str(self.cart_item), expected)
    
    def test_unit_price_property(self):
        """Test unit price property returns discounted price"""
        self.assertEqual(self.cart_item.unit_price, self.product.discounted_price)
    
    def test_total_price_calculation(self):
        """Test total price calculation for cart item"""
        expected_total = self.product.price * 2
        self.assertEqual(self.cart_item.total_price, expected_total)
    
    def test_savings_calculation_on_sale(self):
        """Test savings calculation when product is on sale"""
        expected_savings = (self.product.original_price - self.product.price) * 2
        self.assertEqual(self.cart_item.savings, expected_savings)
    
    def test_savings_calculation_not_on_sale(self):
        """Test savings when product is not on sale"""
        self.product.original_price = None
        self.product.save()
        self.assertEqual(self.cart_item.savings, Decimal('0.00'))
    
    def test_cart_item_validation_positive_quantity(self):
        """Test cart item validation for positive quantity"""
        self.cart_item.quantity = 0
        with self.assertRaises(ValidationError):
            self.cart_item.full_clean()
    
    def test_cart_item_validation_product_availability(self):
        """Test cart item validation for product availability"""
        self.product.quantity = 0
        self.product.save()
        
        with self.assertRaises(ValidationError):
            self.cart_item.full_clean()
    
    def test_cart_item_validation_stock_limit(self):
        """Test cart item validation for stock limits"""
        self.cart_item.quantity = 15  # More than available stock (10)
        
        with self.assertRaises(ValidationError):
            self.cart_item.full_clean()
    
    def test_cart_item_unique_constraint(self):
        """Test unique constraint for cart and product combination"""
        with self.assertRaises(Exception):
            CartItem.objects.create(
                cart=self.cart,
                product=self.product,  # Same product in same cart
                quantity=1
            )


class SavedForLaterModelTest(TestCase):
    """Test cases for SavedForLater model"""
    
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
        
        self.saved_item = SavedForLater.objects.create(
            user=self.user,
            product=self.product,
            quantity=2
        )
    
    def test_saved_item_str_representation(self):
        """Test string representation of saved item"""
        expected = f"{self.user.email} saved {self.product.name}"
        self.assertEqual(str(self.saved_item), expected)
    
    def test_move_to_cart(self):
        """Test moving saved item to cart"""
        cart_item = self.saved_item.move_to_cart()
        
        # Check cart item was created
        self.assertEqual(cart_item.product, self.product)
        self.assertEqual(cart_item.quantity, 2)
        self.assertEqual(cart_item.cart, self.user.cart)
        
        # Check saved item was deleted
        self.assertFalse(SavedForLater.objects.filter(id=self.saved_item.id).exists())
    
    def test_saved_item_unique_constraint(self):
        """Test unique constraint for user and product combination"""
        with self.assertRaises(Exception):
            SavedForLater.objects.create(
                user=self.user,
                product=self.product,  # Same product for same user
                quantity=1
            )


class CartAPITest(APITestCase):
    """Test cases for Cart API endpoints"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            password="testpass123"
        )
        
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
    
    def test_add_item_to_cart_authenticated(self):
        """Test adding item to cart for authenticated user"""
        self.client.force_authenticate(user=self.user)
        
        url = '/api/cart/cart/add_item/'
        data = {
            'product_id': self.product1.id,
            'quantity': 2
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['quantity'], 2)
        self.assertEqual(response.data['product']['id'], self.product1.id)
        
        # Verify item was added to cart
        cart_item = self.user.cart.items.get(product=self.product1)
        self.assertEqual(cart_item.quantity, 2)
    
    def test_add_item_invalid_product(self):
        """Test adding invalid product returns error"""
        self.client.force_authenticate(user=self.user)
        
        url = '/api/cart/cart/add_item/'
        data = {
            'product_id': 99999,  # Non-existent product
            'quantity': 1
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_add_item_insufficient_stock(self):
        """Test adding more items than available stock"""
        self.client.force_authenticate(user=self.user)
        
        url = '/api/cart/cart/add_item/'
        data = {
            'product_id': self.product1.id,
            'quantity': 15  # More than available stock (10)
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_update_cart_item(self):
        """Test updating cart item quantity"""
        self.client.force_authenticate(user=self.user)
        
        # Add item first
        self.user.cart.add_item(self.product1, 2)
        
        url = '/api/cart/cart/update_item/'
        data = {
            'product_id': self.product1.id,
            'quantity': 5
        }
        
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['quantity'], 5)
        
        # Verify update
        cart_item = self.user.cart.items.get(product=self.product1)
        self.assertEqual(cart_item.quantity, 5)
    
    def test_remove_cart_item(self):
        """Test removing item from cart"""
        self.client.force_authenticate(user=self.user)
        
        # Add item first
        self.user.cart.add_item(self.product1, 2)
        
        url = f'/api/cart/cart/remove_item/?product_id={self.product1.id}'
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify item was removed
        self.assertFalse(self.user.cart.items.filter(product=self.product1).exists())
    
    def test_clear_cart(self):
        """Test clearing entire cart"""
        self.client.force_authenticate(user=self.user)
        
        # Add multiple items
        self.user.cart.add_item(self.product1, 2)
        self.user.cart.add_item(self.product2, 1)
        
        url = '/api/cart/cart/clear/'
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify cart is empty
        self.assertEqual(self.user.cart.total_items, 0)
    
    def test_get_cart_summary(self):
        """Test getting cart summary"""
        self.client.force_authenticate(user=self.user)
        
        # Add items to cart
        self.user.cart.add_item(self.product1, 2)
        self.user.cart.add_item(self.product2, 1)
        
        url = '/api/cart/cart/summary/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_items'], 3)
        self.assertIn('subtotal', response.data)
        self.assertIn('total_weight', response.data)
    
    def test_validate_cart_stock(self):
        """Test cart stock validation"""
        self.client.force_authenticate(user=self.user)
        
        # Add items to cart
        self.user.cart.add_item(self.product1, 5)
        
        # Reduce product stock
        self.product1.quantity = 3
        self.product1.save()
        
        url = '/api/cart/cart/validate_stock/'
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['is_valid'])
        self.assertEqual(len(response.data['issues']), 1)
    
    def test_save_item_for_later(self):
        """Test saving cart item for later"""
        self.client.force_authenticate(user=self.user)
        
        # Add item to cart first
        self.user.cart.add_item(self.product1, 2)
        
        url = '/api/cart/cart/save_for_later/'
        data = {'product_id': self.product1.id}
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify item was moved to saved for later
        self.assertTrue(SavedForLater.objects.filter(
            user=self.user, 
            product=self.product1
        ).exists())
        self.assertFalse(self.user.cart.items.filter(product=self.product1).exists())
    
    def test_get_saved_items(self):
        """Test getting saved for later items"""
        self.client.force_authenticate(user=self.user)
        
        # Create saved items
        SavedForLater.objects.create(user=self.user, product=self.product1, quantity=2)
        SavedForLater.objects.create(user=self.user, product=self.product2, quantity=1)
        
        url = '/api/cart/saved-for-later/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
    
    def test_move_saved_item_to_cart(self):
        """Test moving saved item back to cart"""
        self.client.force_authenticate(user=self.user)
        
        # Create saved item
        saved_item = SavedForLater.objects.create(
            user=self.user, 
            product=self.product1, 
            quantity=2
        )
        
        url = f'/api/cart/saved-for-later/{saved_item.id}/move_to_cart/'
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify item was moved to cart
        self.assertTrue(self.user.cart.items.filter(product=self.product1).exists())
        self.assertFalse(SavedForLater.objects.filter(id=saved_item.id).exists())
    
    def test_unauthenticated_cart_access_fails(self):
        """Test that unauthenticated users cannot access cart endpoints"""
        url = '/api/cart/cart/summary/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class CartSignalTest(TestCase):
    """Test cases for cart signals"""
    
    def test_cart_created_on_user_creation(self):
        """Test that cart is automatically created when user is created"""
        user = User.objects.create_user(
            first_name="Test",
            last_name="User",
            email="test@example.com",
            password="testpass123"
        )
        
        # Cart should be created by signal
        self.assertTrue(hasattr(user, 'cart'))
        self.assertIsInstance(user.cart, Cart)
    
    def test_cart_updated_on_item_change(self):
        """Test that cart timestamp is updated when items change"""
        user = User.objects.create_user(
            first_name="Test",
            last_name="User", 
            email="test@example.com",
            password="testpass123"
        )
        
        brand = Brand.objects.create(name="Test Brand", slug="test-brand")
        category = Category.objects.create(name="Electronics")
        
        product = Product.objects.create(
            name="Test Product",
            slug="test-product",
            price=Decimal('99.99'),
            quantity=10,
            brand=brand,
            description="Test product description"
        )
        product.category.add(category)
        
        cart = user.cart
        original_updated_at = cart.updated_at
        
        # Add item to cart
        cart.add_item(product, 1)
        
        # Cart should have updated timestamp
        cart.refresh_from_db()
        self.assertGreater(cart.updated_at, original_updated_at)
