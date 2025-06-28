#!/usr/bin/env python
import os
import sys
import django

# Add the project root to Python path
sys.path.append('/root/ecommerce-backend')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.settings.defaults')
django.setup()

from django.urls import reverse, NoReverseMatch

# Test cart URL patterns
cart_urls = [
    'cart-list',
    'cart-detail',
    'cart-add-item',
    'cart-update-item', 
    'cart-remove-item',
    'cart-clear',
    'cart-summary',
    'cart-validate-stock',
    'cart-save-for-later',
    'saved-for-later-list',
    'saved-for-later-detail',
    'saved-for-later-move-to-cart',
]

print("Testing cart URL patterns:")
for url_name in cart_urls:
    try:
        url = reverse(url_name)
        print(f"✓ {url_name}: {url}")
    except NoReverseMatch as e:
        print(f"✗ {url_name}: {e}")

print("\nTesting orders URL patterns:")
order_urls = [
    'order-list',
    'order-detail',
    'order-create-order',
    'order-cancel-order',
    'order-order-tracking',
    'order-create-return-request',
    'order-list-return-requests',
    'order-order-summary',
]

for url_name in order_urls:
    try:
        url = reverse(url_name)
        print(f"✓ {url_name}: {url}")
    except NoReverseMatch as e:
        print(f"✗ {url_name}: {e}")
