from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Avg, F
from django.shortcuts import get_object_or_404
from django.db import models

from ..models import Brand, Category, Product, ProductReview, Wishlist, WishlistItem, PriceAlert, ProductComparison, InventoryAlert
from .serializers import (
    BrandSerializer, CategorySerializer, ProductListSerializer, ProductDetailSerializer,
    ProductReviewSerializer, WishlistSerializer, PriceAlertSerializer, ProductComparisonSerializer, InventoryAlertSerializer
)


class BrandViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for brands - read only operations
    """
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer
    lookup_field = 'slug'
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering = ['name']

    @action(detail=True, methods=['get'])
    def products(self, request, slug=None):
        """Get all products for a specific brand"""
        brand = self.get_object()
        products = Product.objects.filter(brand=brand)
        
        # Apply filtering
        search = request.query_params.get('search', None)
        if search:
            products = products.filter(
                Q(name__icontains=search) | Q(description__icontains=search)
            )
        
        serializer = ProductListSerializer(products, many=True, context={'request': request})
        return Response(serializer.data)


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for categories - read only operations
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering = ['name']


class ProductViewSet(viewsets.ModelViewSet):
    """
    ViewSet for products with full CRUD operations and advanced filtering
    """
    queryset = Product.objects.select_related('brand').prefetch_related('category', 'tags')
    lookup_field = 'slug'
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    filter_backends = [filters.SearchFilter, filters.OrderingFilter, DjangoFilterBackend]
    search_fields = ['name', 'description', 'model_number', 'brand__name', 'category__name']
    ordering_fields = ['name', 'price', 'rating', 'review_count', 'release_date', 'created_at']
    ordering = ['-created_at']
    
    filterset_fields = {
        'brand__slug': ['exact'],
        'category__name': ['exact', 'icontains'],
        'condition': ['exact'],
        'featured': ['exact'],
        'price': ['gte', 'lte'],
        'rating': ['gte'],
        'release_date': ['gte', 'lte'],
    }

    def get_serializer_class(self):
        if self.action == 'list':
            return ProductListSerializer
        return ProductDetailSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by specifications
        specs_filter = {}
        for key, value in self.request.query_params.items():
            if key.startswith('specs__'):
                spec_key = key.replace('specs__', '')
                specs_filter[f'specifications__{spec_key}'] = value
        
        if specs_filter:
            queryset = queryset.filter(**specs_filter)
        
        # Filter by tags/features
        tags = self.request.query_params.get('tags', None)
        if tags:
            tag_list = tags.split(',')
            queryset = queryset.filter(tags__name__in=tag_list).distinct()
        
        # Filter by stock status
        in_stock = self.request.query_params.get('in_stock', None)
        if in_stock and in_stock.lower() == 'true':
            queryset = queryset.filter(quantity__gt=0)
        
        return queryset

    @action(detail=True, methods=['get'])
    def reviews(self, request, slug=None):
        """Get all reviews for a specific product"""
        product = self.get_object()
        reviews = ProductReview.objects.filter(product=product).order_by('-created_at')
        serializer = ProductReviewSerializer(reviews, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def add_review(self, request, slug=None):
        """Add a review for a product"""
        product = self.get_object()
        
        # Check if user already reviewed this product
        if ProductReview.objects.filter(product=product, user=request.user).exists():
            return Response(
                {'error': 'You have already reviewed this product.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = ProductReviewSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            review = serializer.save(user=request.user, product=product)
            
            # Update product rating and review count
            reviews = ProductReview.objects.filter(product=product)
            avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0
            product.rating = round(avg_rating, 2)
            product.review_count = reviews.count()
            product.save()
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def recommendations(self, request, slug=None):
        """Get product recommendations based on current product"""
        product = self.get_object()
        
        # Simple recommendation: products from same categories and brand
        similar_products = Product.objects.filter(
            Q(category__in=product.category.all()) | Q(brand=product.brand)
        ).exclude(id=product.id).distinct()[:6]
        
        serializer = ProductListSerializer(similar_products, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def featured(self, request):
        """Get featured products"""
        featured_products = self.get_queryset().filter(featured=True)[:8]
        serializer = ProductListSerializer(featured_products, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def deals(self, request):
        """Get products on sale/discount"""
        deals = self.get_queryset().filter(original_price__isnull=False, original_price__gt=F('price'))[:10]
        serializer = ProductListSerializer(deals, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def new_arrivals(self, request):
        """Get newly released products"""
        from datetime import date, timedelta
        thirty_days_ago = date.today() - timedelta(days=30)
        new_products = self.get_queryset().filter(release_date__gte=thirty_days_ago).order_by('-release_date')[:8]
        serializer = ProductListSerializer(new_products, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def top_rated(self, request):
        """Get top rated products"""
        top_rated = self.get_queryset().filter(rating__gte=4.5).order_by('-rating', '-review_count')[:8]
        serializer = ProductListSerializer(top_rated, many=True, context={'request': request})
        return Response(serializer.data)


class WishlistViewSet(viewsets.ModelViewSet):
    """
    ViewSet for user wishlists
    """
    serializer_class = WishlistSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Wishlist.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['post'])
    def add_product(self, request):
        """Add a product to user's wishlist"""
        product_id = request.data.get('product_id')
        if not product_id:
            return Response(
                {'error': 'product_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        product = get_object_or_404(Product, id=product_id)
        wishlist, created = Wishlist.objects.get_or_create(user=request.user)
        
        wishlist_item, item_created = WishlistItem.objects.get_or_create(
            wishlist=wishlist,
            product=product
        )
        
        if item_created:
            return Response(
                {'message': 'Product added to wishlist'},
                status=status.HTTP_201_CREATED
            )
        else:
            return Response(
                {'message': 'Product already in wishlist'},
                status=status.HTTP_200_OK
            )

    @action(detail=False, methods=['delete'])
    def remove_product(self, request):
        """Remove a product from user's wishlist"""
        product_id = request.data.get('product_id')
        if not product_id:
            return Response(
                {'error': 'product_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            wishlist = Wishlist.objects.get(user=request.user)
            wishlist_item = WishlistItem.objects.get(
                wishlist=wishlist,
                product_id=product_id
            )
            wishlist_item.delete()
            return Response(
                {'message': 'Product removed from wishlist'},
                status=status.HTTP_200_OK
            )
        except (Wishlist.DoesNotExist, WishlistItem.DoesNotExist):
            return Response(
                {'error': 'Product not found in wishlist'},
                status=status.HTTP_404_NOT_FOUND
            )


class PriceAlertViewSet(viewsets.ModelViewSet):
    """
    ViewSet for price alerts
    """
    serializer_class = PriceAlertSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return PriceAlert.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        product_id = self.request.data.get('product_id')
        product = get_object_or_404(Product, id=product_id)
        serializer.save(user=self.request.user, product=product)


class ProductComparisonViewSet(viewsets.ModelViewSet):
    """
    ViewSet for product comparisons
    """
    serializer_class = ProductComparisonSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ProductComparison.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def add_product(self, request, pk=None):
        """Add a product to comparison"""
        comparison = self.get_object()
        product_id = request.data.get('product_id')
        
        if not product_id:
            return Response(
                {'error': 'product_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        product = get_object_or_404(Product, id=product_id)
        
        if comparison.products.count() >= 4:  # Limit to 4 products
            return Response(
                {'error': 'Maximum 4 products can be compared'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        comparison.products.add(product)
        return Response({'message': 'Product added to comparison'})

    @action(detail=True, methods=['delete'])
    def remove_product(self, request, pk=None):
        """Remove a product from comparison"""
        comparison = self.get_object()
        product_id = request.data.get('product_id')
        
        if not product_id:
            return Response(
                {'error': 'product_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            product = Product.objects.get(id=product_id)
            comparison.products.remove(product)
            return Response({'message': 'Product removed from comparison'})
        except Product.DoesNotExist:
            return Response(
                {'error': 'Product not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class InventoryAlertViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for inventory alerts (admin only)
    """
    serializer_class = InventoryAlertSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Only allow staff to view inventory alerts
        if self.request.user.is_staff:
            return InventoryAlert.objects.all()
        return InventoryAlert.objects.none()

    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        """Get products with low stock alerts"""
        if not request.user.is_staff:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        low_stock_alerts = InventoryAlert.objects.filter(
            product__quantity__lte=models.F('low_stock_threshold')
        )
        serializer = self.get_serializer(low_stock_alerts, many=True)
        return Response(serializer.data)
