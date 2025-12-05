from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.decorators import action
from django.db.models import Count, Sum, Q
from django.contrib.auth import get_user_model
from ..models import SwapRequest, Order
from src.apps.products.models import Product
from src.apps.accounts.models import UserProfile

User = get_user_model()


def get_target_device_name(device_id):
    """Helper to get target device name from ID"""
    try:
        product = Product.objects.get(id=int(device_id))
        return product.name
    except (Product.DoesNotExist, ValueError, TypeError):
        return 'N/A'


class AdminStatsView(APIView):
    """Admin dashboard statistics"""
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        try:
            # Get recent orders
            recent_orders_data = []
            try:
                for order in Order.objects.order_by('-created_at')[:5]:
                    try:
                        recent_orders_data.append({
                            'id': str(order.id),
                            'order_number': order.order_number or f'ORD-{order.id}',
                            'user_email': order.user.email if order.user else (order.email if hasattr(order, 'email') and order.email else 'Guest'),
                            'total_amount': float(order.total_amount) if order.total_amount else 0.0,
                            'status': order.status or 'pending',
                            'created_at': order.created_at.isoformat() if order.created_at else None
                        })
                    except Exception as e:
                        print(f"Error processing order {order.id}: {str(e)}")
                        continue
            except Exception as e:
                print(f"Error fetching orders: {str(e)}")
            
            # Get recent swaps
            recent_swaps_data = []
            try:
                for swap in SwapRequest.objects.order_by('-created_at')[:5]:
                    try:
                        user_email = swap.user.email if swap.user else (swap.email if hasattr(swap, 'email') and swap.email else 'Guest')
                        recent_swaps_data.append({
                            'id': swap.id,
                            'user_email': user_email,
                            'status': swap.status or 'pending',
                            'estimated_value': float(swap.estimated_value) if swap.estimated_value else 0.0,
                            'created_at': swap.created_at.isoformat() if swap.created_at else None
                        })
                    except Exception as e:
                        print(f"Error processing swap {swap.id}: {str(e)}")
                        continue
            except Exception as e:
                print(f"Error fetching swaps: {str(e)}")
            
            # Calculate total revenue safely
            try:
                revenue_agg = Order.objects.filter(status='delivered').aggregate(total=Sum('total_amount'))
                total_revenue = float(revenue_agg['total']) if revenue_agg['total'] else 0.0
            except Exception as e:
                print(f"Error calculating revenue: {str(e)}")
                total_revenue = 0.0
            
            stats = {
                'total_users': User.objects.filter(is_staff=False).count(),
                'total_products': Product.objects.count(),
                'total_orders': Order.objects.count(),
                'total_swaps': SwapRequest.objects.count(),
                'pending_swaps': SwapRequest.objects.filter(status='pending').count(),
                'total_revenue': total_revenue,
                'recent_orders': recent_orders_data,
                'recent_swaps': recent_swaps_data
            }
            return Response(stats, status=status.HTTP_200_OK)
        except Exception as e:
            import traceback
            error_msg = str(e)
            traceback.print_exc()
            print(f"Error in AdminStatsView: {error_msg}")
            # Return minimal stats on error
            return Response({
                'total_users': 0,
                'total_products': 0,
                'total_orders': 0,
                'total_swaps': 0,
                'pending_swaps': 0,
                'total_revenue': 0,
                'recent_orders': [],
                'recent_swaps': [],
                'error': error_msg
            }, status=status.HTTP_200_OK)  # Return 200 with empty stats instead of 500


class AdminUsersView(APIView):
    """Admin user management"""
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        try:
            users = User.objects.filter(is_superuser=False).values(
                'id', 'email', 'first_name', 'last_name', 'is_staff', 'is_active', 'date_joined', 'last_login'
            )
            return Response({
                'results': list(users),
                'count': users.count()
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdminUserDetailView(APIView):
    """Admin user detail and update"""
    permission_classes = [permissions.IsAdminUser]

    def get(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            return Response({
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_staff': user.is_staff,
                'is_active': user.is_active,
                'date_joined': user.date_joined,
                'last_login': user.last_login
            }, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    def patch(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            user.first_name = request.data.get('first_name', user.first_name)
            user.last_name = request.data.get('last_name', user.last_name)
            user.email = request.data.get('email', user.email)
            user.is_staff = request.data.get('is_staff', user.is_staff)
            user.is_active = request.data.get('is_active', user.is_active)
            user.save()
            return Response({
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_staff': user.is_staff,
                'is_active': user.is_active
            }, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            user.delete()
            return Response({'message': 'User deleted'}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)


class AdminSwapsView(APIView):
    """Admin swap management - list all swaps"""
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        try:
            print(f"[ADMIN] AdminSwapsView GET request from user: {request.user}")
            status_filter = request.query_params.get('status', None)
            swaps = SwapRequest.objects.all()
            if status_filter:
                swaps = swaps.filter(status=status_filter)
            
            print(f"[ADMIN] Found {swaps.count()} swaps")
            
            swaps_data = []
            for swap in swaps.order_by('-created_at'):
                try:
                    user_email = swap.user.email if swap.user else (swap.email if swap.email else 'N/A')
                    swaps_data.append({
                        'id': swap.id,
                        'user_email': user_email,
                        'user_device': swap.user_device,
                        'estimated_value': float(swap.estimated_value) if swap.estimated_value else 0.0,
                        'final_value': float(swap.final_value) if swap.final_value else None,
                        'target_device': swap.target_device_id,
                        'target_device_name': get_target_device_name(swap.target_device_id),
                        'target_device_price': float(swap.target_device_price) if swap.target_device_price else 0.0,
                        'difference': float(swap.difference) if swap.difference else 0.0,
                        'status': swap.status,
                        'admin_notes': swap.admin_notes if swap.admin_notes else '',
                        'created_at': swap.created_at.isoformat() if swap.created_at else None,
                        'updated_at': swap.updated_at.isoformat() if swap.updated_at else None
                    })
                except Exception as e:
                    print(f"[ADMIN] Error processing swap {swap.id}: {str(e)}")
                    continue
            
            print(f"[ADMIN] Returning {len(swaps_data)} swaps")
            return Response({
                'results': swaps_data,
                'count': len(swaps_data)
            }, status=status.HTTP_200_OK)
        except Exception as e:
            import traceback
            print(f"[ADMIN] Error in AdminSwapsView: {str(e)}")
            print(traceback.format_exc())
            return Response({'error': str(e), 'detail': 'Failed to fetch swap requests'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdminSwapDetailView(APIView):
    """Admin swap detail"""
    permission_classes = [permissions.IsAdminUser]

    def get(self, request, swap_id):
        try:
            swap = SwapRequest.objects.get(id=swap_id)
            return Response({
                'id': swap.id,
                'user_email': swap.user.email if swap.user else swap.email if hasattr(swap, 'email') else 'N/A',
                'user_device': swap.user_device,
                'estimated_value': float(swap.estimated_value),
                'final_value': float(swap.final_value) if hasattr(swap, 'final_value') and swap.final_value else None,
                'target_device': swap.target_device_id,
                'target_device_name': get_target_device_name(swap.target_device_id),
                'target_device_price': float(swap.target_device_price),
                'difference': float(swap.difference),
                'status': swap.status,
                'admin_notes': swap.admin_notes if hasattr(swap, 'admin_notes') else '',
                'created_at': swap.created_at,
                'updated_at': swap.updated_at
            }, status=status.HTTP_200_OK)
        except SwapRequest.DoesNotExist:
            return Response({'error': 'Swap not found'}, status=status.HTTP_404_NOT_FOUND)


class AdminSwapApproveView(APIView):
    """Admin approve swap and set final value"""
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, swap_id):
        try:
            swap = SwapRequest.objects.get(id=swap_id)
            final_value = request.data.get('final_value')
            admin_notes = request.data.get('admin_notes', '')
            
            if not final_value:
                return Response({'error': 'final_value is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            swap.final_value = final_value
            swap.status = 'approved'
            if hasattr(swap, 'admin_notes'):
                swap.admin_notes = admin_notes
            swap.save()
            
            # TODO: Send email notification to user with final value
            # send_swap_approval_email(swap.user.email, swap.final_value)
            
            return Response({
                'id': swap.id,
                'status': swap.status,
                'final_value': float(swap.final_value),
                'message': 'Swap approved. User will be notified via email.'
            }, status=status.HTTP_200_OK)
        except SwapRequest.DoesNotExist:
            return Response({'error': 'Swap not found'}, status=status.HTTP_404_NOT_FOUND)


class AdminSwapRejectView(APIView):
    """Admin reject swap"""
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, swap_id):
        try:
            swap = SwapRequest.objects.get(id=swap_id)
            admin_notes = request.data.get('admin_notes', '')
            
            swap.status = 'rejected'
            if hasattr(swap, 'admin_notes'):
                swap.admin_notes = admin_notes
            swap.save()
            
            # TODO: Send email notification to user
            # send_swap_rejection_email(swap.user.email, admin_notes)
            
            return Response({
                'id': swap.id,
                'status': swap.status,
                'message': 'Swap rejected. User will be notified via email.'
            }, status=status.HTTP_200_OK)
        except SwapRequest.DoesNotExist:
            return Response({'error': 'Swap not found'}, status=status.HTTP_404_NOT_FOUND)


class AdminOrdersView(APIView):
    """Admin order management"""
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        try:
            status_filter = request.query_params.get('status', None)
            orders = Order.objects.all()
            if status_filter:
                orders = orders.filter(status=status_filter)
            
            orders_data = []
            for order in orders.order_by('-created_at'):
                orders_data.append({
                    'id': order.id,
                    'order_number': order.order_number,
                    'user_email': order.user.email if order.user else 'Guest',
                    'total_amount': float(order.total_amount),
                    'status': order.status,
                    'items': [{'id': item.id, 'product_name': item.product.name, 'quantity': item.quantity} for item in order.items.all()],
                    'created_at': order.created_at
                })
            
            return Response({
                'results': orders_data,
                'count': len(orders_data)
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdminOrderUpdateView(APIView):
    """Admin update order status"""
    permission_classes = [permissions.IsAdminUser]

    def patch(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id)
            new_status = request.data.get('status')
            if new_status:
                order.status = new_status
                order.save()
            return Response({
                'id': order.id,
                'status': order.status,
                'message': 'Order status updated'
            }, status=status.HTTP_200_OK)
        except Order.DoesNotExist:
            return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)

