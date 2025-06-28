from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

from .models import Order, OrderItem, OrderStatusHistory, OrderShippingUpdate, ReturnRequest


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('total_price', 'created_at')
    fields = ('product', 'product_name', 'quantity', 'unit_price', 'total_price')


class OrderStatusHistoryInline(admin.TabularInline):
    model = OrderStatusHistory
    extra = 0
    readonly_fields = ('timestamp',)
    fields = ('status', 'notes', 'changed_by', 'timestamp')


class OrderShippingUpdateInline(admin.TabularInline):
    model = OrderShippingUpdate
    extra = 0
    readonly_fields = ('timestamp',)
    fields = ('update_type', 'message', 'location', 'timestamp')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'order_number', 'user_email', 'status', 'payment_status',
        'total_amount', 'total_items', 'created_at'
    )
    list_filter = (
        'status', 'payment_status', 'payment_method', 'created_at',
        'estimated_delivery_date'
    )
    search_fields = (
        'order_number', 'user__email', 'user__first_name', 'user__last_name',
        'payment_reference', 'tracking_number'
    )
    readonly_fields = (
        'id', 'order_number', 'user', 'created_at', 'updated_at',
        'total_items', 'subtotal_display', 'total_amount_display'
    )
    
    fieldsets = (
        ('Order Information', {
            'fields': ('id', 'order_number', 'user', 'email', 'phone_number', 'created_at', 'updated_at')
        }),
        ('Status', {
            'fields': ('status', 'payment_status')
        }),
        ('Financial Information', {
            'fields': (
                'subtotal_display', 'shipping_cost', 'tax_amount', 'discount_amount',
                'total_amount_display', 'payment_method', 'payment_reference', 'paystack_reference'
            )
        }),
        ('Shipping Information', {
            'fields': (
                'shipping_address', 'billing_address', 'estimated_delivery_date',
                'actual_delivery_date', 'tracking_number', 'courier_service'
            )
        }),
        ('Additional Information', {
            'fields': ('special_instructions', 'order_notes'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [OrderItemInline, OrderStatusHistoryInline, OrderShippingUpdateInline]
    
    actions = ['mark_as_confirmed', 'mark_as_processing', 'mark_as_shipped']
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Customer Email'
    user_email.admin_order_field = 'user__email'
    
    def total_items(self, obj):
        return obj.total_items
    total_items.short_description = 'Items'
    
    def subtotal_display(self, obj):
        return f"₦{obj.subtotal:,.2f}"
    subtotal_display.short_description = 'Subtotal'
    
    def total_amount_display(self, obj):
        return f"₦{obj.total_amount:,.2f}"
    total_amount_display.short_description = 'Total Amount'
    
    def mark_as_confirmed(self, request, queryset):
        updated = queryset.update(status='confirmed')
        self.message_user(request, f'{updated} orders marked as confirmed.')
    mark_as_confirmed.short_description = 'Mark selected orders as confirmed'
    
    def mark_as_processing(self, request, queryset):
        updated = queryset.update(status='processing')
        self.message_user(request, f'{updated} orders marked as processing.')
    mark_as_processing.short_description = 'Mark selected orders as processing'
    
    def mark_as_shipped(self, request, queryset):
        updated = queryset.update(status='shipped')
        self.message_user(request, f'{updated} orders marked as shipped.')
    mark_as_shipped.short_description = 'Mark selected orders as shipped'


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = (
        'order_number', 'product_name', 'quantity', 'unit_price',
        'total_price', 'order_status'
    )
    list_filter = ('order__status', 'created_at')
    search_fields = (
        'order__order_number', 'product__name', 'product_name'
    )
    readonly_fields = ('total_price', 'created_at')
    
    def order_number(self, obj):
        url = reverse('admin:orders_order_change', args=[obj.order.pk])
        return format_html('<a href="{}">{}</a>', url, obj.order.order_number)
    order_number.short_description = 'Order'
    order_number.admin_order_field = 'order__order_number'
    
    def order_status(self, obj):
        return obj.order.get_status_display()
    order_status.short_description = 'Order Status'
    order_status.admin_order_field = 'order__status'


@admin.register(OrderStatusHistory)
class OrderStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'status', 'changed_by', 'timestamp')
    list_filter = ('status', 'timestamp')
    search_fields = ('order__order_number',)
    readonly_fields = ('timestamp',)
    
    def order_number(self, obj):
        url = reverse('admin:orders_order_change', args=[obj.order.pk])
        return format_html('<a href="{}">{}</a>', url, obj.order.order_number)
    order_number.short_description = 'Order'
    order_number.admin_order_field = 'order__order_number'


@admin.register(OrderShippingUpdate)
class OrderShippingUpdateAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'update_type', 'message', 'location', 'timestamp')
    list_filter = ('update_type', 'timestamp')
    search_fields = ('order__order_number', 'message', 'location')
    readonly_fields = ('timestamp',)
    
    def order_number(self, obj):
        url = reverse('admin:orders_order_change', args=[obj.order.pk])
        return format_html('<a href="{}">{}</a>', url, obj.order.order_number)
    order_number.short_description = 'Order'
    order_number.admin_order_field = 'order__order_number'


@admin.register(ReturnRequest)
class ReturnRequestAdmin(admin.ModelAdmin):
    list_display = (
        'order_number', 'reason', 'status', 'requested_at', 'refund_amount'
    )
    list_filter = ('reason', 'status', 'requested_at')
    search_fields = ('order__order_number', 'description')
    readonly_fields = ('requested_at',)
    
    fieldsets = (
        ('Return Information', {
            'fields': ('order', 'order_item', 'reason', 'description', 'requested_at')
        }),
        ('Status', {
            'fields': ('status', 'processed_at', 'refund_amount')
        }),
        ('Admin Notes', {
            'fields': ('admin_notes',),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['approve_returns', 'reject_returns']
    
    def order_number(self, obj):
        url = reverse('admin:orders_order_change', args=[obj.order.pk])
        return format_html('<a href="{}">{}</a>', url, obj.order.order_number)
    order_number.short_description = 'Order'
    order_number.admin_order_field = 'order__order_number'
    
    def approve_returns(self, request, queryset):
        updated = queryset.update(status='approved')
        self.message_user(request, f'{updated} return requests approved.')
    approve_returns.short_description = 'Approve selected return requests'
    
    def reject_returns(self, request, queryset):
        updated = queryset.update(status='rejected')
        self.message_user(request, f'{updated} return requests rejected.')
    reject_returns.short_description = 'Reject selected return requests'
