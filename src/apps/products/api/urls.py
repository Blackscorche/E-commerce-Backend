from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    BrandViewSet, CategoryViewSet, ProductViewSet, WishlistViewSet, 
    PriceAlertViewSet, ProductComparisonViewSet, InventoryAlertViewSet
)

router = DefaultRouter()
router.register('brands', BrandViewSet)
router.register('categories', CategoryViewSet)
router.register('products', ProductViewSet)
router.register('wishlist', WishlistViewSet, basename='wishlist')
router.register('price-alerts', PriceAlertViewSet, basename='price-alert')
router.register('comparisons', ProductComparisonViewSet, basename='comparison')
router.register('inventory-alerts', InventoryAlertViewSet, basename='inventory-alert')

urlpatterns = [
    path('', include(router.urls))
]
