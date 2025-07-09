from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

from .views import (
    UserProfileViewSet, AddressViewSet, UserActivityLogViewSet,
    UserPreferencesViewSet, UserViewSet, CustomRegisterView
)

router = DefaultRouter()
router.register(r'profile', UserProfileViewSet, basename='profile')
router.register(r'addresses', AddressViewSet, basename='address')
router.register(r'activity-logs', UserActivityLogViewSet, basename='activity-log')
router.register(r'preferences', UserPreferencesViewSet, basename='preferences')
router.register(r'users', UserViewSet, basename='user')

urlpatterns = [
    # JWT Authentication only
    path("auth/login/", TokenObtainPairView.as_view(), name="login"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/token/verify/", TokenVerifyView.as_view(), name="token_verify"),
    path("auth/register/", CustomRegisterView.as_view(), name="register"),
    
    # API endpoints
    path("api/", include(router.urls)),
]