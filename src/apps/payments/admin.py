from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import PaymentMethod, Payment, Transaction, PaymentWebhook, Refund, PaymentAttempt
import json


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ['name', 'provider', 'is_active', 'created_at']
    list_filter = ['provider', 'is_active']
    search_fields = ['name', 'provider']
    readonly_fields = ['created_at', 'updated_at']


class TransactionInline(admin.TabularInline):
    model = Transaction
    extra = 0
    readonly_fields = ['id', 'created_at', 'updated_at', 'processed_at']
    fields = ['transaction_type', 'amount', 'status', 'reference', 'provider_transaction_id', 'notes']


class RefundInline(admin.TabularInline):
    model = Refund
    extra = 0
    readonly_fields = ['id', 'created_at', 'updated_at', 'processed_at']
    fields = ['amount', 'refund_type', 'reason', 'status', 'reference']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'reference', 'user_email', 'order_link', 'amount', 'currency', 
        'status', 'payment_method', 'created_at'
    ]
    list_filter = ['status', 'payment_method', 'currency', 'created_at']
    search_fields = ['reference', 'user__email', 'order__id']
    readonly_fields = [
        'id', 'user', 'order', 'reference', 'gateway_response_formatted',
        'metadata_formatted', 'created_at', 'updated_at', 'completed_at'
    ]
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'user', 'order', 'reference', 'status')
        }),
        ('Payment Details', {
            'fields': ('amount', 'currency', 'payment_method', 'gateway_fee', 'app_fee')
        }),
        ('Provider Data', {
            'fields': ('gateway_response_formatted',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('metadata_formatted', 'ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'completed_at'),
            'classes': ('collapse',)
        })
    )
    inlines = [TransactionInline, RefundInline]
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User'
    
    def order_link(self, obj):
        if obj.order:
            url = reverse('admin:orders_order_change', args=[obj.order.id])
            return format_html('<a href="{}">{}</a>', url, obj.order.id)
        return '-'
    order_link.short_description = 'Order'
    
    def gateway_response_formatted(self, obj):
        if obj.gateway_response:
            return format_html('<pre>{}</pre>', json.dumps(obj.gateway_response, indent=2))
        return '-'
    gateway_response_formatted.short_description = 'Gateway Response'
    
    def metadata_formatted(self, obj):
        if obj.metadata:
            return format_html('<pre>{}</pre>', json.dumps(obj.metadata, indent=2))
        return '-'
    metadata_formatted.short_description = 'Metadata'


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = [
        'reference', 'payment_reference', 'transaction_type', 'amount', 
        'status', 'created_at'
    ]
    list_filter = ['transaction_type', 'status', 'created_at']
    search_fields = ['reference', 'payment__reference', 'provider_transaction_id']
    readonly_fields = [
        'id', 'payment', 'provider_response_formatted', 'created_at', 
        'updated_at', 'processed_at'
    ]
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'payment', 'transaction_type', 'amount', 'status')
        }),
        ('Provider Details', {
            'fields': ('reference', 'provider_transaction_id', 'provider_response_formatted'),
            'classes': ('collapse',)
        }),
        ('Additional Info', {
            'fields': ('notes', 'processed_by'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'processed_at'),
            'classes': ('collapse',)
        })
    )
    
    def payment_reference(self, obj):
        return obj.payment.reference
    payment_reference.short_description = 'Payment Reference'
    
    def provider_response_formatted(self, obj):
        if obj.provider_response:
            return format_html('<pre>{}</pre>', json.dumps(obj.provider_response, indent=2))
        return '-'
    provider_response_formatted.short_description = 'Provider Response'


@admin.register(PaymentWebhook)
class PaymentWebhookAdmin(admin.ModelAdmin):
    list_display = ['event_type', 'processed', 'created_at', 'processed_at']
    list_filter = ['event_type', 'processed', 'created_at']
    search_fields = ['event_type']
    readonly_fields = [
        'id', 'data_formatted', 'signature', 'created_at', 'processed_at'
    ]
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'event_type', 'processed', 'processing_error')
        }),
        ('Webhook Data', {
            'fields': ('data_formatted', 'signature'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'processed_at'),
        })
    )
    
    def data_formatted(self, obj):
        if obj.data:
            return format_html('<pre>{}</pre>', json.dumps(obj.data, indent=2))
        return '-'
    data_formatted.short_description = 'Webhook Data'


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = [
        'reference', 'payment_reference', 'amount', 'refund_type', 
        'status', 'created_at'
    ]
    list_filter = ['refund_type', 'status', 'created_at']
    search_fields = ['reference', 'payment__reference', 'provider_refund_id']
    readonly_fields = [
        'id', 'payment', 'reference', 'gateway_response_formatted',
        'created_at', 'updated_at', 'processed_at'
    ]
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'payment', 'amount', 'refund_type', 'status')
        }),
        ('Details', {
            'fields': ('reason', 'reference', 'provider_refund_id')
        }),
        ('Provider Data', {
            'fields': ('gateway_response_formatted',),
            'classes': ('collapse',)
        }),
        ('Staff Tracking', {
            'fields': ('requested_by', 'processed_by')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'processed_at'),
            'classes': ('collapse',)
        })
    )
    
    def payment_reference(self, obj):
        return obj.payment.reference
    payment_reference.short_description = 'Payment Reference'
    
    def gateway_response_formatted(self, obj):
        if obj.gateway_response:
            return format_html('<pre>{}</pre>', json.dumps(obj.gateway_response, indent=2))
        return '-'
    gateway_response_formatted.short_description = 'Gateway Response'


@admin.register(PaymentAttempt)
class PaymentAttemptAdmin(admin.ModelAdmin):
    list_display = [
        'user_email', 'amount', 'currency', 'payment_method', 
        'success', 'ip_address', 'created_at'
    ]
    list_filter = ['success', 'payment_method', 'currency', 'country', 'created_at']
    search_fields = ['user__email', 'ip_address', 'error_message']
    readonly_fields = [
        'id', 'user', 'gateway_response_formatted', 'user_agent', 'created_at'
    ]
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'user', 'amount', 'currency', 'payment_method', 'success')
        }),
        ('Error Details', {
            'fields': ('error_message', 'gateway_response_formatted'),
            'classes': ('collapse',)
        }),
        ('Security Information', {
            'fields': ('ip_address', 'user_agent', 'country')
        }),
        ('Timestamp', {
            'fields': ('created_at',)
        })
    )
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User'
    
    def gateway_response_formatted(self, obj):
        if obj.gateway_response:
            return format_html('<pre>{}</pre>', json.dumps(obj.gateway_response, indent=2))
        return '-'
    gateway_response_formatted.short_description = 'Gateway Response'
