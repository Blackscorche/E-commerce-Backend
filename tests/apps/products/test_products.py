# Enhanced tests for the gadget store products app
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from decimal import Decimal
from datetime import date

from src.apps.products.models import (
    Brand, Category, Product, ProductReview, Wishlist, WishlistItem, 
    PriceAlert, ProductComparison, InventoryAlert
)
from src.apps.products.api.serializers import (
    BrandSerializer, CategorySerializer, ProductListSerializer, 
    ProductDetailSerializer, ProductReviewSerializer
)

User = get_user_model()


class BrandModelTest(TestCase):
    def setUp(self):
        self.brand = Brand.objects.create(
            name="Apple",
            slug="apple",
            description="Apple Inc. technology company",
            website="https://apple.com",
            founded_year=1976
        )

    def test_brand_string_representation(self):
        self.assertEqual(str(self.brand), "Apple")

    def test_brand_ordering(self):
        Brand.objects.create(name="Samsung", slug="samsung")
        brands = Brand.objects.all()
        self.assertEqual(brands[0].name, "Apple")  # Alphabetical ordering


class CategoryModelTest(TestCase):
    def setUp(self):
        self.parent_category = Category.objects.create(
            name="Electronics",
            description="Electronic devices"
        )
        self.child_category = Category.objects.create(
            name="Smartphones",
            parent=self.parent_category,
            description="Mobile phones"
        )

    def test_category_string_representation(self):
        self.assertEqual(str(self.parent_category), "Electronics")

    def test_category_hierarchy(self):
        self.assertEqual(self.child_category.parent, self.parent_category)
        self.assertIn(self.child_category, self.parent_category.subcategories.all())


class ProductModelTest(TestCase):
    def setUp(self):
        self.brand = Brand.objects.create(name="Apple", slug="apple")
        self.category = Category.objects.create(name="Smartphones")
        self.product = Product.objects.create(
            name="iPhone 15 Pro",
            slug="iphone-15-pro",
            brand=self.brand,
            price=Decimal("999.99"),
            original_price=Decimal("1099.99"),
            quantity=10,
            condition="new",
            release_date=date(2023, 9, 22),
            specifications={
                "display": "6.1-inch Super Retina XDR",
                "chip": "A17 Pro",
                "storage": "128GB"
            }
        )
        self.product.category.add(self.category)

    def test_product_string_representation(self):
        self.assertEqual(str(self.product), "iPhone 15 Pro")

    def test_product_properties(self):
        self.assertTrue(self.product.is_available)
        self.assertEqual(self.product.discount_percentage, Decimal('9.09'))
        self.assertTrue(self.product.is_on_sale)

    def test_product_out_of_stock(self):
        self.product.quantity = 0
        self.product.save()
        self.assertFalse(self.product.is_available)


class ProductReviewModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            first_name="Test",
            last_name="User",
            password="testpass123"
        )
        self.brand = Brand.objects.create(name="Apple", slug="apple")
        self.category = Category.objects.create(name="Smartphones")
        self.product = Product.objects.create(
            name="iPhone 15 Pro",
            slug="iphone-15-pro",
            brand=self.brand,
            price=Decimal("999.99"),
        )
        self.product.category.add(self.category)

    def test_review_creation(self):
        review = ProductReview.objects.create(
            product=self.product,
            user=self.user,
            rating=5,
            title="Great phone!",
            review_text="Love this phone, excellent quality.",
            verified_purchase=True
        )
        self.assertEqual(str(review), "Great phone! - iPhone 15 Pro")
        self.assertEqual(review.rating, 5)

    def test_unique_review_per_user_product(self):
        ProductReview.objects.create(
            product=self.product,
            user=self.user,
            rating=5,
            title="First review",
            review_text="First review text"
        )
        
        # This should not be allowed due to unique_together constraint
        with self.assertRaises(Exception):
            ProductReview.objects.create(
                product=self.product,
                user=self.user,
                rating=4,
                title="Second review",
                review_text="Second review text"
            )


class WishlistModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            first_name="Test",
            last_name="User",
            password="testpass123"
        )
        self.brand = Brand.objects.create(name="Apple", slug="apple")
        self.category = Category.objects.create(name="Smartphones")
        self.product = Product.objects.create(
            name="iPhone 15 Pro",
            slug="iphone-15-pro",
            brand=self.brand,
            price=Decimal("999.99"),
        )
        self.product.category.add(self.category)

    def test_wishlist_creation(self):
        wishlist = Wishlist.objects.create(user=self.user)
        WishlistItem.objects.create(wishlist=wishlist, product=self.product)
        
        self.assertEqual(wishlist.total_items, 1)
        self.assertEqual(wishlist.total_value, Decimal("999.99"))
        self.assertIn(self.product, wishlist.products.all())


class PriceAlertModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            first_name="Test",
            last_name="User",
            password="testpass123"
        )
        self.brand = Brand.objects.create(name="Apple", slug="apple")
        self.product = Product.objects.create(
            name="iPhone 15 Pro",
            slug="iphone-15-pro",
            brand=self.brand,
            price=Decimal("999.99"),
        )

    def test_price_alert_creation(self):
        alert = PriceAlert.objects.create(
            user=self.user,
            product=self.product,
            target_price=Decimal("899.99")
        )
        self.assertTrue(alert.is_active)
        self.assertEqual(str(alert), "Price alert for iPhone 15 Pro at 899.99")

    def test_price_drop_check(self):
        alert = PriceAlert.objects.create(
            user=self.user,
            product=self.product,
            target_price=Decimal("899.99")
        )
        
        # Price is higher, should not trigger
        self.assertFalse(alert.check_price_drop())
        self.assertTrue(alert.is_active)
        
        # Lower the price, should trigger alert
        self.product.price = Decimal("850.00")
        self.product.save()
        alert.refresh_from_db()
        self.assertTrue(alert.check_price_drop())
        self.assertFalse(alert.is_active)


class ProductAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            first_name="Test",
            last_name="User",
            password="testpass123"
        )
        self.brand = Brand.objects.create(name="Apple", slug="apple")
        self.category = Category.objects.create(name="Smartphones")
        self.product = Product.objects.create(
            name="iPhone 15 Pro",
            slug="iphone-15-pro",
            brand=self.brand,
            price=Decimal("999.99"),
            featured=True,
            specifications={
                "display": "6.1-inch Super Retina XDR",
                "chip": "A17 Pro"
            }
        )
        self.product.category.add(self.category)
        self.product.tags.add("5g", "wireless-charging")

    def test_product_list_api(self):
        url = reverse('product-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_product_detail_api(self):
        url = reverse('product-detail', kwargs={'slug': self.product.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'iPhone 15 Pro')

    def test_product_filtering_by_brand(self):
        url = reverse('product-list')
        response = self.client.get(url, {'brand__slug': 'apple'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_product_search(self):
        url = reverse('product-list')
        response = self.client.get(url, {'search': 'iPhone'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_product_specifications_filter(self):
        url = reverse('product-list')
        response = self.client.get(url, {'specs__chip': 'A17 Pro'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_product_tags_filter(self):
        url = reverse('product-list')
        response = self.client.get(url, {'tags': '5g,wireless-charging'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_featured_products_endpoint(self):
        url = reverse('product-featured')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_product_recommendations(self):
        url = reverse('product-recommendations', kwargs={'slug': self.product.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_add_product_review_authenticated(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('product-add-review', kwargs={'slug': self.product.slug})
        data = {
            'rating': 5,
            'title': 'Great product',
            'review_text': 'Really love this phone!'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_add_product_review_unauthenticated(self):
        url = reverse('product-add-review', kwargs={'slug': self.product.slug})
        data = {
            'rating': 5,
            'title': 'Great product',
            'review_text': 'Really love this phone!'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class WishlistAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            first_name="Test",
            last_name="User",
            password="testpass123"
        )
        self.brand = Brand.objects.create(name="Apple", slug="apple")
        self.product = Product.objects.create(
            name="iPhone 15 Pro",
            slug="iphone-15-pro",
            brand=self.brand,
            price=Decimal("999.99"),
        )

    def test_add_to_wishlist_authenticated(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('wishlist-add-product')
        data = {'product_id': self.product.id}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_add_to_wishlist_unauthenticated(self):
        url = reverse('wishlist-add-product')
        data = {'product_id': self.product.id}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_remove_from_wishlist(self):
        self.client.force_authenticate(user=self.user)
        
        # Add to wishlist first
        wishlist = Wishlist.objects.create(user=self.user)
        WishlistItem.objects.create(wishlist=wishlist, product=self.product)
        
        # Remove from wishlist
        url = reverse('wishlist-remove-product')
        data = {'product_id': self.product.id}
        response = self.client.delete(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
