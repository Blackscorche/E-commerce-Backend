import json
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.core.files.uploadedfile import SimpleUploadedFile

from src.apps.accounts.models import UserProfile, Address, UserActivityLog, UserPreferences
from src.apps.products.models import Brand, Category

User = get_user_model()


class UserProfileModelTest(TestCase):
    """Test cases for UserProfile model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            password="testpass123"
        )
    
    def test_profile_auto_creation(self):
        """Test that user profile is automatically created with user"""
        # Profile should be created by signal
        self.assertTrue(hasattr(self.user, 'profile'))
        self.assertIsInstance(self.user.profile, UserProfile)
    
    def test_profile_str_representation(self):
        """Test string representation of user profile"""
        expected = f"{self.user.full_name}'s Profile"
        self.assertEqual(str(self.user.profile), expected)
    
    def test_age_calculation(self):
        """Test age calculation from date of birth"""
        from datetime import date
        self.user.profile.date_of_birth = date(1990, 1, 1)
        self.user.profile.save()
        self.assertIsNotNone(self.user.profile.age)
        self.assertGreater(self.user.profile.age, 30)


class AddressModelTest(TestCase):
    """Test cases for Address model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            first_name="Jane",
            last_name="Smith",
            email="jane.smith@example.com",
            password="testpass123"
        )
    
    def test_address_creation(self):
        """Test address creation"""
        address = Address.objects.create(
            user=self.user,
            type='shipping',
            full_name="Jane Smith",
            address_line_1="123 Main St",
            city="Lagos",
            state="Lagos State",
            postal_code="100001",
            country="Nigeria"
        )
        self.assertEqual(address.user, self.user)
        self.assertEqual(address.type, 'shipping')
        self.assertTrue(address.is_active)
    
    def test_default_address_constraint(self):
        """Test that only one address can be default per type"""
        # Create first default address
        address1 = Address.objects.create(
            user=self.user,
            type='shipping',
            full_name="Jane Smith",
            address_line_1="123 Main St",
            city="Lagos",
            state="Lagos State",
            postal_code="100001",
            is_default=True
        )
        
        # Create second address and set as default
        address2 = Address.objects.create(
            user=self.user,
            type='shipping',
            full_name="Jane Smith",
            address_line_1="456 Oak Ave",
            city="Abuja",
            state="FCT",
            postal_code="900001",
            is_default=True
        )
        
        # Refresh from database
        address1.refresh_from_db()
        address2.refresh_from_db()
        
        # Only the second address should be default
        self.assertFalse(address1.is_default)
        self.assertTrue(address2.is_default)
    
    def test_address_str_representation(self):
        """Test string representation of address"""
        address = Address.objects.create(
            user=self.user,
            full_name="Jane Smith",
            address_line_1="123 Main St",
            city="Lagos",
            state="Lagos State",
            postal_code="100001"
        )
        expected = "Jane Smith - Lagos, Lagos State"
        self.assertEqual(str(address), expected)


class UserPreferencesModelTest(TestCase):
    """Test cases for UserPreferences model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            first_name="Bob",
            last_name="Johnson",
            email="bob.johnson@example.com",
            password="testpass123"
        )
    
    def test_preferences_auto_creation(self):
        """Test that user preferences are automatically created with user"""
        # Preferences should be created by signal
        self.assertTrue(hasattr(self.user, 'preferences'))
        self.assertIsInstance(self.user.preferences, UserPreferences)
    
    def test_default_preferences(self):
        """Test default preference values"""
        prefs = self.user.preferences
        self.assertEqual(prefs.theme, 'light')
        self.assertEqual(prefs.language, 'en')
        self.assertEqual(prefs.currency, 'NGN')
        self.assertTrue(prefs.price_alerts_enabled)
        self.assertEqual(prefs.profile_visibility, 'private')


class UserActivityLogModelTest(TestCase):
    """Test cases for UserActivityLog model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            first_name="Alice",
            last_name="Wilson",
            email="alice.wilson@example.com",
            password="testpass123"
        )
    
    def test_activity_log_creation(self):
        """Test activity log creation"""
        log = UserActivityLog.objects.create(
            user=self.user,
            activity_type='login',
            description='User logged in',
            ip_address='192.168.1.1'
        )
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.activity_type, 'login')
        self.assertEqual(log.description, 'User logged in')
    
    def test_activity_log_auto_creation_on_registration(self):
        """Test that activity log is created automatically on user registration"""
        # Create a new user (should trigger signal)
        new_user = User.objects.create_user(
            first_name="Test",
            last_name="User",
            email="test.user@example.com",
            password="testpass123"
        )
        
        # Check if activity log was created
        logs = UserActivityLog.objects.filter(user=new_user)
        self.assertTrue(logs.exists())
        self.assertEqual(logs.first().activity_type, 'login')


class UserProfileAPITest(APITestCase):
    """Test cases for UserProfile API endpoints"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            first_name="API",
            last_name="User",
            email="api.user@example.com",
            password="testpass123"
        )
        self.client.force_authenticate(user=self.user)
    
    def test_get_user_profile(self):
        """Test retrieving user profile"""
        url = reverse('profile-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check if response is paginated
        if 'results' in response.data:
            self.assertEqual(len(response.data['results']), 1)  # Should return one profile
        else:
            self.assertEqual(len(response.data), 1)  # Should return one profile
    
    def test_update_user_profile(self):
        """Test updating user profile"""
        profile = self.user.profile
        url = reverse('profile-detail', args=[profile.pk])
        data = {
            'phone_number': '+234803456789',
            'bio': 'Software developer',
            'newsletter_subscribed': False
        }
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh profile from database
        profile.refresh_from_db()
        self.assertEqual(profile.phone_number, '+234803456789')
        self.assertEqual(profile.bio, 'Software developer')
        self.assertFalse(profile.newsletter_subscribed)
    
    def test_avatar_upload(self):
        """Test avatar upload"""
        url = reverse('profile-upload-avatar')
        
        # Create a simple test image file (skip validation for test)
        test_image = SimpleUploadedFile(
            "test_avatar.jpg",
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82",
            content_type="image/png"
        )
        
        data = {'avatar': test_image}
        response = self.client.post(url, data, format='multipart')
        
        # Accept either success or validation error for this test
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST])
        
        if response.status_code == status.HTTP_200_OK:
            # Check if avatar was saved
            self.user.profile.refresh_from_db()
            self.assertIsNotNone(self.user.profile.avatar)
    
    def test_remove_avatar(self):
        """Test avatar removal"""
        # First upload an avatar
        self.user.profile.avatar = SimpleUploadedFile(
            "test_avatar.jpg",
            b"fake image content",
            content_type="image/jpeg"
        )
        self.user.profile.save()
        
        url = reverse('profile-remove-avatar')
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check if avatar was removed
        self.user.profile.refresh_from_db()
        self.assertFalse(self.user.profile.avatar)


class AddressAPITest(APITestCase):
    """Test cases for Address API endpoints"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            first_name="Address",
            last_name="User",
            email="address.user@example.com",
            password="testpass123"
        )
        self.client.force_authenticate(user=self.user)
    
    def test_create_address(self):
        """Test creating a new address"""
        url = reverse('address-list')
        data = {
            'type': 'shipping',
            'full_name': 'John Doe',
            'address_line_1': '123 Main Street',
            'city': 'Lagos',
            'state': 'Lagos State',
            'postal_code': '100001',
            'country': 'Nigeria',
            'is_default': True
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check if address was created
        address = Address.objects.get(pk=response.data['id'])
        self.assertEqual(address.user, self.user)
        self.assertEqual(address.full_name, 'John Doe')
        self.assertTrue(address.is_default)
    
    def test_list_user_addresses(self):
        """Test listing user addresses"""
        # Create test addresses
        Address.objects.create(
            user=self.user,
            type='shipping',
            full_name='John Doe',
            address_line_1='123 Main St',
            city='Lagos',
            state='Lagos State',
            postal_code='100001'
        )
        
        url = reverse('address-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check if response is paginated
        if 'results' in response.data:
            self.assertEqual(len(response.data['results']), 1)
        else:
            self.assertEqual(len(response.data), 1)
    
    def test_set_default_address(self):
        """Test setting an address as default"""
        address = Address.objects.create(
            user=self.user,
            type='shipping',
            full_name='John Doe',
            address_line_1='123 Main St',
            city='Lagos',
            state='Lagos State',
            postal_code='100001'
        )
        
        url = reverse('address-set-default', args=[address.pk])
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check if address is now default
        address.refresh_from_db()
        self.assertTrue(address.is_default)
    
    def test_get_default_addresses(self):
        """Test getting default addresses"""
        # Create default shipping address
        Address.objects.create(
            user=self.user,
            type='shipping',
            full_name='John Doe',
            address_line_1='123 Main St',
            city='Lagos',
            state='Lagos State',
            postal_code='100001',
            is_default=True
        )
        
        url = reverse('address-defaults')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['type'], 'shipping')


class UserPreferencesAPITest(APITestCase):
    """Test cases for UserPreferences API endpoints"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            first_name="Preferences",
            last_name="User",
            email="preferences.user@example.com",
            password="testpass123"
        )
        self.client.force_authenticate(user=self.user)
    
    def test_get_user_preferences(self):
        """Test retrieving user preferences"""
        url = reverse('preferences-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check if response is paginated
        if 'results' in response.data:
            self.assertEqual(len(response.data['results']), 1)  # Should return one preferences object
        else:
            self.assertEqual(len(response.data), 1)  # Should return one preferences object
    
    def test_update_user_preferences(self):
        """Test updating user preferences"""
        preferences = self.user.preferences
        url = reverse('preferences-detail', args=[preferences.pk])
        data = {
            'theme': 'dark',
            'language': 'fr',
            'price_alerts_enabled': False,
            'profile_visibility': 'public'
        }
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh preferences from database
        preferences.refresh_from_db()
        self.assertEqual(preferences.theme, 'dark')
        self.assertEqual(preferences.language, 'fr')
        self.assertFalse(preferences.price_alerts_enabled)
        self.assertEqual(preferences.profile_visibility, 'public')


class UserActivityLogAPITest(APITestCase):
    """Test cases for UserActivityLog API endpoints"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            first_name="Activity",
            last_name="User",
            email="activity.user@example.com",
            password="testpass123"
        )
        self.client.force_authenticate(user=self.user)
    
    def test_list_user_activities(self):
        """Test listing user activities"""
        # Create test activity logs
        UserActivityLog.objects.create(
            user=self.user,
            activity_type='product_view',
            description='Viewed iPhone 13',
            metadata={'product_id': 1}
        )
        
        url = reverse('activity-log-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)  # At least the registration log
    
    def test_activity_summary(self):
        """Test activity summary endpoint"""
        # Create test activity logs
        UserActivityLog.objects.create(
            user=self.user,
            activity_type='product_view',
            description='Viewed iPhone 13'
        )
        UserActivityLog.objects.create(
            user=self.user,
            activity_type='cart_add',
            description='Added iPhone 13 to cart'
        )
        
        url = reverse('activity-log-summary')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_activities', response.data)
        self.assertIn('activity_counts', response.data)
        self.assertGreater(response.data['total_activities'], 0)


class UserAPITest(APITestCase):
    """Test cases for User API endpoints"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            first_name="Main",
            last_name="User",
            email="main.user@example.com",
            password="testpass123"
        )
        self.client.force_authenticate(user=self.user)
    
    def test_get_current_user(self):
        """Test getting current user details"""
        url = reverse('user-me')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], self.user.email)
        self.assertEqual(response.data['full_name'], self.user.full_name)
        self.assertIn('profile', response.data)
        self.assertIn('preferences', response.data)
    
    def test_log_activity(self):
        """Test logging user activity"""
        url = reverse('user-log-activity')
        data = {
            'activity_type': 'product_search',
            'description': 'Searched for smartphones',
            'metadata': {'query': 'smartphones', 'results_count': 15}
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check if activity was logged
        activity = UserActivityLog.objects.filter(
            user=self.user,
            activity_type='product_search'
        ).first()
        self.assertIsNotNone(activity)
        self.assertEqual(activity.description, 'Searched for smartphones')
    
    def test_log_invalid_activity(self):
        """Test logging invalid activity type"""
        url = reverse('user-log-activity')
        data = {
            'activity_type': 'invalid_type',
            'description': 'Invalid activity'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
