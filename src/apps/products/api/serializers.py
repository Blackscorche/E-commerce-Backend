from rest_framework import serializers
from taggit.serializers import TagListSerializerField, TaggitSerializer

from ..models import (
    Brand, Category, Product, ProductReview, Wishlist, WishlistItem, 
    PriceAlert, ProductComparison, InventoryAlert
)


class BrandSerializer(serializers.ModelSerializer):
    product_count = serializers.SerializerMethodField()

    class Meta:
        model = Brand
        fields = ('id', 'name', 'slug', 'logo', 'description', 'website', 'founded_year', 'product_count')

    def get_product_count(self, obj):
        return obj.products.count()


class CategorySerializer(serializers.ModelSerializer):
    product_count = serializers.SerializerMethodField()
    parent = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Category
        fields = ('id', 'name', 'parent', 'icon', 'description', 'product_count')

    def get_product_count(self, obj):
        return obj.product_set.count()


class ProductListSerializer(TaggitSerializer, serializers.ModelSerializer):
    brand = BrandSerializer(read_only=True)
    category = CategorySerializer(many=True, read_only=True)
    tags = TagListSerializerField()
    discount_percentage = serializers.ReadOnlyField()
    is_on_sale = serializers.ReadOnlyField()
    in_stock = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            'id', 'name', 'slug', 'brand', 'model_number', 'price', 'original_price',
            'discount_percentage', 'is_on_sale', 'quantity', 'in_stock', 'featured',
            'condition', 'rating', 'review_count', 'release_date', 'warranty_months',
            'description', 'picture', 'category', 'tags'
        )

    def get_in_stock(self, obj):
        return obj.is_available


class ProductDetailSerializer(TaggitSerializer, serializers.ModelSerializer):
    brand = BrandSerializer(read_only=True)
    category = CategorySerializer(many=True, read_only=True)
    tags = TagListSerializerField()
    discount_percentage = serializers.ReadOnlyField()
    is_on_sale = serializers.ReadOnlyField()
    in_stock = serializers.SerializerMethodField()
    reviews_summary = serializers.SerializerMethodField()
    estimated_delivery = serializers.SerializerMethodField()
    price_history = serializers.SerializerMethodField()
    color_variants = serializers.SerializerMethodField()
    eco_friendly = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            'id', 'name', 'slug', 'brand', 'model_number', 'price', 'original_price',
            'discount_percentage', 'is_on_sale', 'quantity', 'in_stock', 'featured',
            'condition', 'rating', 'review_count', 'release_date', 'warranty_months',
            'description', 'picture', 'category', 'specifications', 'tags',
            'reviews_summary', 'estimated_delivery', 'price_history', 'color_variants',
            'eco_friendly', 'created_at', 'updated_at'
        )

    def get_in_stock(self, obj):
        return obj.is_available

    def get_reviews_summary(self, obj):
        reviews = obj.reviews.all()
        if not reviews.exists():
            return {
                'average_rating': 0,
                'total_reviews': 0,
                'rating_breakdown': {'5': 0, '4': 0, '3': 0, '2': 0, '1': 0}
            }
        
        rating_breakdown = {'5': 0, '4': 0, '3': 0, '2': 0, '1': 0}
        for review in reviews:
            rating_breakdown[str(review.rating)] += 1
        
        return {
            'average_rating': obj.rating,
            'total_reviews': obj.review_count,
            'rating_breakdown': rating_breakdown
        }

    def get_estimated_delivery(self, obj):
        if obj.is_available:
            return "2-3 business days"
        return "Out of stock"

    def get_price_history(self, obj):
        """Simple price history - could be expanded with actual historical data"""
        history = []
        if obj.original_price and obj.original_price != obj.price:
            history.append({
                'date': obj.created_at.date().isoformat(),
                'price': str(obj.original_price)
            })
        history.append({
            'date': obj.updated_at.date().isoformat(),
            'price': str(obj.price)
        })
        return history

    def get_color_variants(self, obj):
        """Placeholder for color variants - would need additional model"""
        return [
            {
                'name': 'Default',
                'hex': '#000000',
                'available': True
            }
        ]

    def get_eco_friendly(self, obj):
        """Check if product has eco-friendly tags"""
        return obj.tags.filter(name__in=['eco-friendly', 'sustainable', 'recycled']).exists()


class ProductReviewSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    product = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = ProductReview
        fields = (
            'id', 'product', 'user', 'rating', 'title', 'review_text',
            'verified_purchase', 'helpful_count', 'created_at', 'updated_at'
        )
        read_only_fields = ('user', 'product', 'helpful_count', 'created_at', 'updated_at')


class WishlistItemSerializer(serializers.ModelSerializer):
    product = ProductListSerializer(read_only=True)
    added_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = WishlistItem
        fields = ('id', 'product', 'added_at')


class WishlistSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    products = WishlistItemSerializer(source='wishlist_items', many=True, read_only=True)
    total_items = serializers.ReadOnlyField()
    total_value = serializers.ReadOnlyField()

    class Meta:
        model = Wishlist
        fields = ('id', 'user', 'products', 'total_items', 'total_value', 'created_at')


class PriceAlertSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    product = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = PriceAlert
        fields = (
            'id', 'user', 'product', 'target_price', 'is_active',
            'created_at', 'notified_at'
        )
        read_only_fields = ('user', 'product', 'notified_at')


# For backward compatibility, keep the original ProductSerializer
class ProductSerializer(ProductDetailSerializer):
    """Alias for ProductDetailSerializer to maintain backward compatibility"""
    pass


class ProductComparisonSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    products = ProductListSerializer(many=True, read_only=True)
    product_count = serializers.ReadOnlyField()

    class Meta:
        model = ProductComparison
        fields = ('id', 'user', 'name', 'products', 'product_count', 'created_at')


class InventoryAlertSerializer(serializers.ModelSerializer):
    product = serializers.StringRelatedField(read_only=True)
    check_stock_level = serializers.ReadOnlyField()
    should_send_alert = serializers.ReadOnlyField()

    class Meta:
        model = InventoryAlert
        fields = (
            'id', 'product', 'low_stock_threshold', 'auto_reorder',
            'last_alert_sent', 'check_stock_level', 'should_send_alert'
        )
