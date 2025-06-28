

from django.urls import path
from . import views

urlpatterns = [
    path('initialize-payment/', views.initialize_payment, name='initialize_payment'),
    path('verify-payment/', views.verify_payment, name='verify_payment'),
]
