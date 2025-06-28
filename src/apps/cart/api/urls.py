from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import CartViewSet, SavedForLaterViewSet

# Create router for API viewsets
router = DefaultRouter()
router.register(r'cart', CartViewSet, basename='cart')
router.register(r'saved-for-later', SavedForLaterViewSet, basename='saved-for-later')

urlpatterns = [
    path('', include(router.urls)),
]
