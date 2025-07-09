# views.py
import hashlib
import hmac
import json
import logging
import requests
from decimal import Decimal
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework import status, viewsets, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView

from src.apps.orders.models import Order
from src.apps.cart.models import Cart
from .models import Payment, PaymentMethod, Transaction, PaymentWebhook
from .serializers import PaymentSerializer, TransactionSerializer

logger = logging.getLogger(__name__)


class PaystackService:
    """Service class for Paystack API interactions"""
    
    BASE_URL = "https://api.paystack.co"
    
    @classmethod
    def get_headers(cls):
        """Get API headers with authentication"""
        return {
            "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json",
        }
    
    @classmethod
    def verify_webhook_signature(cls, payload, signature):
        """Verify webhook signature for security"""
        expected_signature = hmac.new(
            settings.PAYSTACK_SECRET_KEY.encode('utf-8'),
            payload,
            hashlib.sha512
        ).hexdigest()
        return hmac.compare_digest(expected_signature, signature)
    
    @classmethod
    def initialize_transaction(cls, email, amount, order_id, customer_data=None, metadata=None):
        """Initialize a payment transaction"""
        url = f"{cls.BASE_URL}/transaction/initialize"
        
        data = {
            "amount": int(float(amount) * 100),  # Convert to kobo
            "email": email,
            "reference": f"order_{order_id}_{Order.objects.get(id=order_id).id}",
            "callback_url": f"{settings.FRONTEND_URL}/payment/callback/",
            "metadata": {
                "order_id": order_id,
                "custom_fields": [
                    {
                        "display_name": "Order ID",
                        "variable_name": "order_id",
                        "value": order_id
                    }
                ],
                **(metadata or {})
            }
        }
        
        # Add customer data if provided
        if customer_data:
            data["customer"] = customer_data
        
        try:
            response = requests.post(url, json=data, headers=cls.get_headers(), timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Paystack initialization error: {e}")
            raise Exception(f"Payment initialization failed: {str(e)}")
    
    @classmethod
    def verify_transaction(cls, reference):
        """Verify a payment transaction"""
        url = f"{cls.BASE_URL}/transaction/verify/{reference}"
        
        try:
            response = requests.get(url, headers=cls.get_headers(), timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Paystack verification error: {e}")
            raise Exception(f"Payment verification failed: {str(e)}")
    
    @classmethod
    def create_customer(cls, email, first_name, last_name, phone=None):
        """Create a customer in Paystack"""
        url = f"{cls.BASE_URL}/customer"
        
        data = {
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
        }
        
        if phone:
            data["phone"] = phone
        
        try:
            response = requests.post(url, json=data, headers=cls.get_headers(), timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Paystack customer creation error: {e}")
            return None
    
    @classmethod
    def create_plan(cls, name, amount, interval="monthly"):
        """Create a subscription plan"""
        url = f"{cls.BASE_URL}/plan"
        
        data = {
            "name": name,
            "amount": int(float(amount) * 100),
            "interval": interval,
        }
        
        try:
            response = requests.post(url, json=data, headers=cls.get_headers(), timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Paystack plan creation error: {e}")
            raise Exception(f"Plan creation failed: {str(e)}")


class PaymentViewSet(viewsets.ModelViewSet):
    """ViewSet for payment management"""
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Payment.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['post'])
    def initialize(self, request):
        """Initialize a payment"""
        try:
            order_id = request.data.get('order_id')
            if not order_id:
                return Response(
                    {'error': 'Order ID is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get order
            try:
                order = Order.objects.get(id=order_id, user=request.user)
            except Order.DoesNotExist:
                return Response(
                    {'error': 'Order not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            if order.status != 'pending':
                return Response(
                    {'error': 'Order is not in pending status'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create customer data
            customer_data = {
                "email": request.user.email,
                "first_name": request.user.first_name,
                "last_name": request.user.last_name,
            }
            
            # Add phone if available
            if hasattr(request.user, 'profile') and request.user.profile.phone_number:
                customer_data["phone"] = request.user.profile.phone_number
            
            # Create metadata
            metadata = {
                "user_id": request.user.id,
                "order_total": str(order.total_amount),
                "order_items": len(order.items.all()),
            }
            
            # Initialize payment with Paystack
            paystack_response = PaystackService.initialize_transaction(
                email=request.user.email,
                amount=order.total_amount,
                order_id=order_id,
                customer_data=customer_data,
                metadata=metadata
            )
            
            if paystack_response.get('status'):
                # Create payment record
                payment = Payment.objects.create(
                    user=request.user,
                    order=order,
                    amount=order.total_amount,
                    currency='NGN',
                    payment_method='paystack',
                    reference=paystack_response['data']['reference'],
                    status='pending'
                )
                
                # Create transaction record
                Transaction.objects.create(
                    payment=payment,
                    transaction_type='payment',
                    amount=order.total_amount,
                    reference=paystack_response['data']['reference'],
                    status='pending',
                    provider_response=paystack_response
                )
                
                return Response({
                    'status': 'success',
                    'payment_id': payment.id,
                    'authorization_url': paystack_response['data']['authorization_url'],
                    'access_code': paystack_response['data']['access_code'],
                    'reference': paystack_response['data']['reference'],
                })
            else:
                return Response(
                    {'error': paystack_response.get('message', 'Payment initialization failed')},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Exception as e:
            logger.error(f"Payment initialization error: {e}")
            return Response(
                {'error': 'Payment initialization failed'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def verify(self, request):
        """Verify a payment"""
        try:
            reference = request.data.get('reference')
            if not reference:
                return Response(
                    {'error': 'Payment reference is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get payment record
            try:
                payment = Payment.objects.get(reference=reference, user=request.user)
            except Payment.DoesNotExist:
                return Response(
                    {'error': 'Payment not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            if payment.status == 'completed':
                return Response({
                    'status': 'success',
                    'message': 'Payment already verified',
                    'payment': PaymentSerializer(payment).data
                })
            
            # Verify with Paystack
            paystack_response = PaystackService.verify_transaction(reference)
            
            if paystack_response.get('status') and paystack_response['data']['status'] == 'success':
                # Update payment status
                payment.status = 'completed'
                payment.save()
                
                # Update order status
                order = payment.order
                order.status = 'confirmed'
                order.save()
                
                # Create transaction record
                Transaction.objects.create(
                    payment=payment,
                    transaction_type='verification',
                    amount=Decimal(paystack_response['data']['amount']) / 100,  # Convert from kobo
                    reference=reference,
                    status='completed',
                    provider_response=paystack_response
                )
                
                # Clear user's cart
                Cart.objects.filter(user=request.user).delete()
                
                return Response({
                    'status': 'success',
                    'message': 'Payment verified successfully',
                    'payment': PaymentSerializer(payment).data,
                    'order_id': order.id
                })
            else:
                payment.status = 'failed'
                payment.save()
                
                return Response(
                    {'error': 'Payment verification failed'},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Exception as e:
            logger.error(f"Payment verification error: {e}")
            return Response(
                {'error': 'Payment verification failed'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def history(self, request):
        """Get payment history for the user"""
        payments = self.get_queryset().order_by('-created_at')
        page = self.paginate_queryset(payments)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(payments, many=True)
        return Response(serializer.data)


@csrf_exempt
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def paystack_webhook(request):
    """Handle Paystack webhooks securely"""
    try:
        # Get signature from headers
        signature = request.META.get('HTTP_X_PAYSTACK_SIGNATURE')
        if not signature:
            logger.warning("Webhook received without signature")
            return HttpResponse("Missing signature", status=400)
        
        # Verify signature
        payload = request.body
        if not PaystackService.verify_webhook_signature(payload, signature):
            logger.warning("Invalid webhook signature")
            return HttpResponse("Invalid signature", status=400)
        
        # Parse webhook data
        try:
            data = json.loads(payload.decode('utf-8'))
        except json.JSONDecodeError:
            logger.error("Invalid JSON in webhook payload")
            return HttpResponse("Invalid JSON", status=400)
        
        # Log webhook
        webhook = PaymentWebhook.objects.create(
            event_type=data.get('event'),
            data=data,
            signature=signature,
            processed=False
        )
        
        # Process webhook based on event type
        event = data.get('event')
        event_data = data.get('data', {})
        
        if event == 'charge.success':
            # Handle successful payment
            reference = event_data.get('reference')
            if reference:
                try:
                    payment = Payment.objects.get(reference=reference)
                    if payment.status != 'completed':
                        payment.status = 'completed'
                        payment.save()
                        
                        # Update order
                        order = payment.order
                        order.status = 'confirmed'
                        order.save()
                        
                        # Create transaction record
                        Transaction.objects.create(
                            payment=payment,
                            transaction_type='webhook_confirmation',
                            amount=Decimal(event_data.get('amount', 0)) / 100,
                            reference=reference,
                            status='completed',
                            provider_response=data
                        )
                        
                        logger.info(f"Payment {reference} confirmed via webhook")
                except Payment.DoesNotExist:
                    logger.warning(f"Payment with reference {reference} not found")
        
        elif event == 'charge.failed':
            # Handle failed payment
            reference = event_data.get('reference')
            if reference:
                try:
                    payment = Payment.objects.get(reference=reference)
                    payment.status = 'failed'
                    payment.save()
                    
                    logger.info(f"Payment {reference} failed via webhook")
                except Payment.DoesNotExist:
                    logger.warning(f"Payment with reference {reference} not found")
        
        # Mark webhook as processed
        webhook.processed = True
        webhook.save()
        
        return HttpResponse("OK", status=200)
        
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        return HttpResponse("Server error", status=500)


# Legacy endpoints for backward compatibility
@require_http_methods(["POST"])
@csrf_exempt
@login_required
def initialize_payment(request):
    """Legacy endpoint - deprecated, use PaymentViewSet.initialize instead"""
    logger.warning("Legacy initialize_payment endpoint used")
    return JsonResponse({"message": "Please use /api/payments/initialize/ endpoint"}, status=410)


@require_http_methods(["GET"])
@csrf_exempt
@login_required
def verify_payment(request):
    """Legacy endpoint - deprecated, use PaymentViewSet.verify instead"""
    logger.warning("Legacy verify_payment endpoint used")
    return JsonResponse({"message": "Please use /api/payments/verify/ endpoint"}, status=410)
