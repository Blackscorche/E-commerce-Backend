from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    BrandViewSet, CategoryViewSet, ProductViewSet, WishlistViewSet, 
    PriceAlertViewSet, ProductComparisonViewSet, InventoryAlertViewSet
)

router = DefaultRouter()
router.register(r'brands', BrandViewSet, basename='brand')
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'wishlist', WishlistViewSet, basename='wishlist')
router.register(r'price-alerts', PriceAlertViewSet, basename='price-alert')
router.register(r'product-comparison', ProductComparisonViewSet, basename='comparison')
router.register(r'inventory-alerts', InventoryAlertViewSet, basename='inventory-alert')
router.register(r'', ProductViewSet, basename='products')  # Empty prefix MUST be last

urlpatterns = [
    path('', include(router.urls))
]
