from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status, viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from ..models import UserProfile, Address, UserActivityLog, UserPreferences
from .serializers import (
    UserProfileSerializer, AddressSerializer, UserActivityLogSerializer,
    UserPreferencesSerializer, UserAvatarUploadSerializer, CustomUserDetailsSerializer
)

User = get_user_model()


class UserProfileViewSet(viewsets.ModelViewSet):
    """ViewSet for user profile management"""
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    def get_queryset(self):
        return UserProfile.objects.filter(user=self.request.user)
    
    def get_object(self):
        """Get or create user profile"""
        profile, created = UserProfile.objects.get_or_create(user=self.request.user)
        return profile
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def upload_avatar(self, request):
        """Upload user avatar"""
        profile = self.get_object()
        serializer = UserAvatarUploadSerializer(profile, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            # Log activity
            UserActivityLog.objects.create(
                user=request.user,
                activity_type='profile_updated',
                description='Avatar uploaded',
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['delete'])
    def remove_avatar(self, request):
        """Remove user avatar"""
        profile = self.get_object()
        if profile.avatar:
            profile.avatar.delete()
            profile.save()
            # Log activity
            UserActivityLog.objects.create(
                user=request.user,
                activity_type='profile_updated',
                description='Avatar removed',
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            return Response({'message': 'Avatar removed successfully'}, status=status.HTTP_200_OK)
        return Response({'message': 'No avatar to remove'}, status=status.HTTP_400_BAD_REQUEST)
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class AddressViewSet(viewsets.ModelViewSet):
    """ViewSet for user address management"""
    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['type', 'is_default', 'is_active']
    ordering_fields = ['created_at', 'is_default']
    ordering = ['-is_default', '-created_at']
    
    def get_queryset(self):
        return Address.objects.filter(user=self.request.user, is_active=True)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        """Set address as default"""
        address = self.get_object()
        # Remove default from other addresses of the same type
        Address.objects.filter(
            user=request.user,
            type=address.type,
            is_default=True
        ).exclude(pk=address.pk).update(is_default=False)
        
        address.is_default = True
        address.save()
        
        return Response({'message': f'Address set as default {address.type} address'})
    
    @action(detail=False, methods=['get'])
    def defaults(self, request):
        """Get default addresses"""
        defaults = Address.objects.filter(
            user=request.user,
            is_default=True,
            is_active=True
        )
        serializer = self.get_serializer(defaults, many=True)
        return Response(serializer.data)


class UserActivityLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for user activity logs (read-only)"""
    serializer_class = UserActivityLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['activity_type']
    search_fields = ['description']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return UserActivityLog.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get activity summary"""
        queryset = self.get_queryset()
        
        # Get activity counts by type
        activity_counts = {}
        for choice in UserActivityLog.ACTIVITY_TYPES:
            activity_type = choice[0]
            count = queryset.filter(activity_type=activity_type).count()
            activity_counts[activity_type] = count
        
        # Get recent activities (last 30 days)
        thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
        recent_count = queryset.filter(created_at__gte=thirty_days_ago).count()
        
        return Response({
            'total_activities': queryset.count(),
            'recent_activities_30_days': recent_count,
            'activity_counts': activity_counts,
            'last_activity': queryset.first().created_at if queryset.exists() else None
        })


class UserPreferencesViewSet(viewsets.ModelViewSet):
    """ViewSet for user preferences management"""
    serializer_class = UserPreferencesSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return UserPreferences.objects.filter(user=self.request.user)
    
    def get_object(self):
        """Get or create user preferences"""
        preferences, created = UserPreferences.objects.get_or_create(user=self.request.user)
        return preferences
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    def update(self, request, *args, **kwargs):
        """Override update to log activity"""
        response = super().update(request, *args, **kwargs)
        
        # Log activity
        UserActivityLog.objects.create(
            user=request.user,
            activity_type='profile_updated',
            description='Preferences updated',
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        return response
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for user management (read-only for now)"""
    serializer_class = CustomUserDetailsSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return User.objects.filter(id=self.request.user.id)
    
    def get_object(self):
        return self.request.user
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user details"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def log_activity(self, request):
        """Log user activity"""
        activity_type = request.data.get('activity_type')
        description = request.data.get('description', '')
        metadata = request.data.get('metadata', {})
        
        if not activity_type or activity_type not in dict(UserActivityLog.ACTIVITY_TYPES):
            return Response(
                {'error': 'Invalid or missing activity_type'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        UserActivityLog.objects.create(
            user=request.user,
            activity_type=activity_type,
            description=description,
            metadata=metadata,
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        return Response({'message': 'Activity logged successfully'})
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
