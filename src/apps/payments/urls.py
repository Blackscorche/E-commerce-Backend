
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create router for API viewsets
router = DefaultRouter()
router.register(r'payments', views.PaymentViewSet, basename='payment')

urlpatterns = [
    # RESTful API endpoints
    path('api/', include(router.urls)),
    
    # Webhook endpoint (must be publicly accessible)
    path('webhook/paystack/', views.paystack_webhook, name='paystack_webhook'),
    
    # Legacy endpoints (deprecated)
    path('initialize-payment/', views.initialize_payment, name='initialize_payment'),
    path('verify-payment/', views.verify_payment, name='verify_payment'),
]
