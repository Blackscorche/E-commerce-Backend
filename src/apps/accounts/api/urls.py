from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    UserProfileViewSet, AddressViewSet, UserActivityLogViewSet,
    UserPreferencesViewSet, UserViewSet
)

# Create router for API viewsets
router = DefaultRouter()
router.register(r'profile', UserProfileViewSet, basename='profile')
router.register(r'addresses', AddressViewSet, basename='address')
router.register(r'activity-logs', UserActivityLogViewSet, basename='activity-log')
router.register(r'preferences', UserPreferencesViewSet, basename='preferences')
router.register(r'users', UserViewSet, basename='user')

urlpatterns = [
    # Authentication URLs
    path("auth/", include("dj_rest_auth.urls")),
    path("auth/register/", include("dj_rest_auth.registration.urls")),
    
    # API endpoints
    path("api/", include(router.urls)),
]
