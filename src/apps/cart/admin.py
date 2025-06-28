from django.contrib import admin
from .models import Cart, CartItem, SavedForLater


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user_email', 'session_key', 'total_items', 'subtotal', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('user__email', 'session_key')
    readonly_fields = ('created_at', 'updated_at', 'total_items', 'subtotal')
    
    def user_email(self, obj):
        return obj.user.email if obj.user else 'Guest'
    user_email.short_description = 'User Email'
    user_email.admin_order_field = 'user__email'


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ('added_at', 'updated_at', 'unit_price', 'total_price')


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('cart_user', 'product_name', 'quantity', 'unit_price', 'total_price', 'added_at')
    list_filter = ('added_at', 'updated_at')
    search_fields = ('cart__user__email', 'product__name')
    readonly_fields = ('added_at', 'updated_at', 'unit_price', 'total_price')
    
    def cart_user(self, obj):
        return obj.cart.user.email if obj.cart.user else 'Guest'
    cart_user.short_description = 'User'
    cart_user.admin_order_field = 'cart__user__email'
    
    def product_name(self, obj):
        return obj.product.name
    product_name.short_description = 'Product'
    product_name.admin_order_field = 'product__name'


@admin.register(SavedForLater)
class SavedForLaterAdmin(admin.ModelAdmin):
    list_display = ('user_email', 'product_name', 'quantity', 'saved_at')
    list_filter = ('saved_at',)
    search_fields = ('user__email', 'product__name')
    readonly_fields = ('saved_at',)
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User Email'
    user_email.admin_order_field = 'user__email'
    
    def product_name(self, obj):
        return obj.product.name
    product_name.short_description = 'Product'
    product_name.admin_order_field = 'product__name'


# Enhance the CartAdmin with inline items
CartAdmin.inlines = [CartItemInline]
