from django.contrib import admin

from .models import (
    Brand, Category, Product, ProductReview, Wishlist, WishlistItem, 
    PriceAlert, ProductComparison, InventoryAlert
)


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'website', 'founded_year')
    list_filter = ('founded_year',)
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent')
    list_filter = ('parent',)
    search_fields = ('name', 'description')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'brand',
        'price',
        'original_price',
        'quantity',
        'condition',
        'featured',
        'rating',
        'review_count',
    )
    list_filter = (
        'brand',
        'condition',
        'featured',
        'release_date',
        'created_at',
    )
    list_editable = (
        'price',
        'original_price',
        'quantity',
        'featured',
    )
    search_fields = ('name', 'model_number', 'description')
    filter_horizontal = ('category',)
    readonly_fields = ('rating', 'review_count', 'created_at', 'updated_at')

    # sets up slug to be generated from product name
    prepopulated_fields = {'slug': ('name',)}

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'brand', 'model_number', 'category', 'description')
        }),
        ('Pricing & Inventory', {
            'fields': ('price', 'original_price', 'quantity', 'condition')
        }),
        ('Product Details', {
            'fields': ('picture', 'release_date', 'warranty_months', 'specifications', 'tags')
        }),
        ('Status & Metrics', {
            'fields': ('featured', 'rating', 'review_count')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ('title', 'product', 'user', 'rating', 'verified_purchase', 'created_at')
    list_filter = ('rating', 'verified_purchase', 'created_at')
    search_fields = ('title', 'review_text', 'product__name', 'user__email')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ('user', 'total_items', 'created_at')
    search_fields = ('user__email', 'user__first_name', 'user__last_name')
    readonly_fields = ('total_items', 'total_value', 'created_at', 'updated_at')


@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ('wishlist', 'product', 'added_at')
    list_filter = ('added_at',)
    search_fields = ('product__name', 'wishlist__user__email')


@admin.register(PriceAlert)
class PriceAlertAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'target_price', 'is_active', 'created_at', 'notified_at')
    list_filter = ('is_active', 'created_at', 'notified_at')
    search_fields = ('user__email', 'product__name')
    readonly_fields = ('notified_at',)


@admin.register(ProductComparison)
class ProductComparisonAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'product_count', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__email', 'name')
    filter_horizontal = ('products',)
    readonly_fields = ('product_count', 'created_at')


@admin.register(InventoryAlert)
class InventoryAlertAdmin(admin.ModelAdmin):
    list_display = ('product', 'low_stock_threshold', 'auto_reorder', 'check_stock_level', 'last_alert_sent')
    list_filter = ('auto_reorder', 'last_alert_sent')
    search_fields = ('product__name',)
    readonly_fields = ('check_stock_level', 'should_send_alert')
