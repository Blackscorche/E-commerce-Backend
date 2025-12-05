from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import OrderViewSet, ReturnRequestViewSet, SwapRequestViewSet, SwapCreateView, SwapListView
from .admin_views import (
    AdminStatsView, AdminUsersView, AdminUserDetailView,
    AdminSwapsView, AdminSwapDetailView, AdminSwapApproveView, AdminSwapRejectView,
    AdminOrdersView, AdminOrderUpdateView
)

# Create router for API viewsets
router = DefaultRouter()
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'returns', ReturnRequestViewSet, basename='return-request')
router.register(r'swaps', SwapRequestViewSet, basename='swap')

urlpatterns = [
    path('swap/create', SwapCreateView.as_view(), name='swap-create'),
    path('swap/my', SwapListView.as_view(), name='swap-list'),
    path('', include(router.urls)),
]
