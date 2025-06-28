from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import OrderViewSet, ReturnRequestViewSet

# Create router for API viewsets
router = DefaultRouter()
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'returns', ReturnRequestViewSet, basename='return-request')

urlpatterns = [
    path('', include(router.urls)),
]
