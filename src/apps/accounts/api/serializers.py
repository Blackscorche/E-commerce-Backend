from django.contrib.auth import get_user_model
from dj_rest_auth.serializers import LoginSerializer
from rest_framework import serializers

from allauth.account.adapter import get_adapter
from allauth.account.utils import setup_user_email

from ..models import UserProfile, Address, UserActivityLog, UserPreferences

User = get_user_model()


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile management"""
    age = serializers.ReadOnlyField()
    preferred_brands = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field='name'
    )
    preferred_categories = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field='name'
    )
    
    class Meta:
        model = UserProfile
        fields = [
            'id', 'avatar', 'phone_number', 'date_of_birth', 'gender', 'bio',
            'newsletter_subscribed', 'sms_notifications', 'email_notifications',
            'preferred_brands', 'preferred_categories', 'budget_range_min', 
            'budget_range_max', 'age', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'age']


class AddressSerializer(serializers.ModelSerializer):
    """Serializer for user addresses"""
    
    class Meta:
        model = Address
        fields = [
            'id', 'type', 'full_name', 'company', 'address_line_1', 
            'address_line_2', 'city', 'state', 'postal_code', 'country',
            'phone_number', 'is_default', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate(self, data):
        """Ensure only one default address per type per user"""
        user = self.context['request'].user
        if data.get('is_default'):
            # Check if there's already a default address of this type
            existing_default = Address.objects.filter(
                user=user,
                type=data.get('type'),
                is_default=True
            ).exclude(pk=self.instance.pk if self.instance else None)
            
            if existing_default.exists():
                # This validation will be handled by the model's save method
                pass
        return data


class UserActivityLogSerializer(serializers.ModelSerializer):
    """Serializer for user activity logs"""
    
    class Meta:
        model = UserActivityLog
        fields = [
            'id', 'activity_type', 'description', 'metadata', 
            'ip_address', 'user_agent', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class UserPreferencesSerializer(serializers.ModelSerializer):
    """Serializer for user preferences"""
    
    class Meta:
        model = UserPreferences
        fields = [
            'id', 'theme', 'language', 'currency', 'timezone',
            'price_alerts_enabled', 'deal_notifications', 
            'new_product_notifications', 'inventory_notifications',
            'profile_visibility', 'allow_reviews_display', 
            'allow_data_collection', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CustomLoginSerializer(LoginSerializer):
    username = None
    email = serializers.EmailField(required=False, allow_blank=True)
    password = serializers.CharField(style={"input_type": "password"})


class CustomRegisterSerializer(serializers.Serializer):
    """
    Modified RegisterSerializer class from dj_rest_auth
    """

    username = None
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    email = serializers.EmailField(required=True)
    password1 = serializers.CharField(write_only=True, style={"input_type": "password"})
    password2 = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate_email(self, email):
        email = get_adapter().clean_email(email)
        if email and User.objects.filter(email=email).exists():
            raise serializers.ValidationError(
                "A user is already registered with this e-mail address."
            )
        return email

    def validate_password1(self, password):
        return get_adapter().clean_password(password)

    def validate(self, data):
        if data["password1"] != data["password2"]:
            raise serializers.ValidationError("The two password fields didn't match.")
        return data

    def get_cleaned_data(self):
        return {
            "first_name": self.validated_data.get("first_name", ""),
            "last_name": self.validated_data.get("last_name", ""),
            "password1": self.validated_data.get("password1", ""),
            "email": self.validated_data.get("email", ""),
        }

    def save(self, request):
        adapter = get_adapter()
        user = adapter.new_user(request)
        self.cleaned_data = self.get_cleaned_data()
        adapter.save_user(request, user, self)
        setup_user_email(request, user, [])
        return user


class CustomUserDetailsSerializer(serializers.ModelSerializer):
    """Enhanced user details serializer with profile information"""
    profile = UserProfileSerializer(read_only=True)
    preferences = UserPreferencesSerializer(read_only=True)
    addresses_count = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'first_name', 'last_name', 'email', 'full_name', 
            'initials', 'date_joined', 'last_login', 'profile', 
            'preferences', 'addresses_count'
        ]
        read_only_fields = [
            'id', 'email', 'full_name', 'initials', 'date_joined', 
            'last_login', 'addresses_count'
        ]
    
    def get_addresses_count(self, obj):
        """Get count of user's addresses"""
        return obj.addresses.filter(is_active=True).count()


class UserAvatarUploadSerializer(serializers.ModelSerializer):
    """Serializer specifically for avatar uploads"""
    
    class Meta:
        model = UserProfile
        fields = ['avatar']
    
    def validate_avatar(self, value):
        """Validate uploaded avatar"""
        if value:
            # Validate file size (max 5MB)
            if value.size > 5 * 1024 * 1024:
                raise serializers.ValidationError("Avatar file size must be less than 5MB.")
            
            # Validate file type
            allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
            if value.content_type not in allowed_types:
                raise serializers.ValidationError(
                    "Invalid file type. Only JPEG, PNG, GIF, and WebP images are allowed."
                )
        
        return value
