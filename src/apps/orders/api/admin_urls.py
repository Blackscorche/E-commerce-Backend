from django.urls import path
from .admin_views import (
    AdminStatsView, AdminUsersView, AdminUserDetailView,
    AdminSwapsView, AdminSwapDetailView, AdminSwapApproveView, AdminSwapRejectView,
    AdminOrdersView, AdminOrderUpdateView
)

urlpatterns = [
    path('stats/', AdminStatsView.as_view(), name='admin-stats'),
    path('users/', AdminUsersView.as_view(), name='admin-users'),
    path('users/<int:user_id>/', AdminUserDetailView.as_view(), name='admin-user-detail'),
    path('swaps/', AdminSwapsView.as_view(), name='admin-swaps'),
    path('swaps/<int:swap_id>/', AdminSwapDetailView.as_view(), name='admin-swap-detail'),
    path('swaps/<int:swap_id>/approve/', AdminSwapApproveView.as_view(), name='admin-swap-approve'),
    path('swaps/<int:swap_id>/reject/', AdminSwapRejectView.as_view(), name='admin-swap-reject'),
    path('orders/', AdminOrdersView.as_view(), name='admin-orders'),
    path('orders/<int:order_id>/', AdminOrderUpdateView.as_view(), name='admin-order-update'),
]

