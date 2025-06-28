from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html

from .forms import CustomUserChangeForm, CustomUserCreationForm
from .models import CustomUser, UserProfile, Address, UserActivityLog, UserPreferences


class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = CustomUser
    list_display = ("first_name", "last_name", "email", "is_staff", "is_active", "date_joined")
    list_filter = ("first_name", "last_name", "email", "is_staff", "is_active", "date_joined")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal information", {"fields": ("first_name", "last_name")}),
        ("Permissions", {"fields": ("is_staff", "is_active")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2", "is_staff", "is_active"),
            },
        ),
    )
    search_fields = ("first_name", "last_name", "email")
    ordering = ("first_name", "last_name", "email")
    readonly_fields = ("last_login", "date_joined")


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        'user_email', 'user_full_name', 'phone_number', 'gender', 
        'newsletter_subscribed', 'created_at'
    )
    list_filter = (
        'gender', 'newsletter_subscribed', 'sms_notifications', 
        'email_notifications', 'created_at'
    )
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'phone_number')
    filter_horizontal = ('preferred_brands', 'preferred_categories')
    readonly_fields = ('created_at', 'updated_at', 'age')
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'avatar', 'phone_number', 'date_of_birth', 'gender', 'bio')
        }),
        ('Preferences', {
            'fields': (
                'newsletter_subscribed', 'sms_notifications', 'email_notifications',
                'preferred_brands', 'preferred_categories', 'budget_range_min', 'budget_range_max'
            )
        }),
        ('Metadata', {
            'fields': ('age', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Email'
    user_email.admin_order_field = 'user__email'
    
    def user_full_name(self, obj):
        return obj.user.full_name
    user_full_name.short_description = 'Full Name'
    user_full_name.admin_order_field = 'user__first_name'


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = (
        'full_name', 'user_email', 'type', 'city', 'state', 
        'is_default', 'is_active', 'created_at'
    )
    list_filter = ('type', 'is_default', 'is_active', 'country', 'state', 'created_at')
    search_fields = (
        'user__email', 'full_name', 'company', 'address_line_1', 
        'city', 'state', 'postal_code'
    )
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('User', {
            'fields': ('user', 'type')
        }),
        ('Address Information', {
            'fields': (
                'full_name', 'company', 'address_line_1', 'address_line_2',
                'city', 'state', 'postal_code', 'country', 'phone_number'
            )
        }),
        ('Flags', {
            'fields': ('is_default', 'is_active')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User Email'
    user_email.admin_order_field = 'user__email'


@admin.register(UserActivityLog)
class UserActivityLogAdmin(admin.ModelAdmin):
    list_display = (
        'user_email', 'activity_type', 'description', 'ip_address', 'created_at'
    )
    list_filter = ('activity_type', 'created_at')
    search_fields = (
        'user__email', 'activity_type', 'description', 'ip_address'
    )
    readonly_fields = ('created_at',)
    
    fieldsets = (
        ('Activity Information', {
            'fields': ('user', 'activity_type', 'description', 'metadata')
        }),
        ('Technical Information', {
            'fields': ('ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User Email'
    user_email.admin_order_field = 'user__email'
    
    def has_add_permission(self, request):
        return False  # Activity logs should not be manually created
    
    def has_change_permission(self, request, obj=None):
        return False  # Activity logs should not be editable


@admin.register(UserPreferences)
class UserPreferencesAdmin(admin.ModelAdmin):
    list_display = (
        'user_email', 'theme', 'language', 'currency', 
        'price_alerts_enabled', 'profile_visibility', 'updated_at'
    )
    list_filter = (
        'theme', 'language', 'currency', 'price_alerts_enabled', 
        'profile_visibility', 'updated_at'
    )
    search_fields = ('user__email',)
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Display Preferences', {
            'fields': ('theme', 'language', 'currency', 'timezone')
        }),
        ('Notification Preferences', {
            'fields': (
                'price_alerts_enabled', 'deal_notifications', 
                'new_product_notifications', 'inventory_notifications'
            )
        }),
        ('Privacy Preferences', {
            'fields': (
                'profile_visibility', 'allow_reviews_display', 'allow_data_collection'
            )
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User Email'
    user_email.admin_order_field = 'user__email'


admin.site.register(CustomUser, CustomUserAdmin)
