from django.core.management.base import BaseCommand
from django.utils.text import slugify
from decimal import Decimal
from datetime import date, timedelta
import random

from src.apps.products.models import Brand, Category, Product
from src.apps.accounts.models import CustomUser, UserProfile, UserPreferences


class Command(BaseCommand):
    help = 'Seed the database with sample products, categories, brands, and users'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before seeding',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write(self.style.WARNING('Clearing existing data...'))
            Product.objects.all().delete()
            Category.objects.all().delete()
            Brand.objects.all().delete()
            CustomUser.objects.filter(is_superuser=False).delete()

        # Create Categories
        self.stdout.write('Creating categories...')
        categories_data = [
            {'name': 'Electronics', 'description': 'Electronic devices and gadgets'},
            {'name': 'Smartphones', 'description': 'Mobile phones and accessories', 'parent': 'Electronics'},
            {'name': 'Laptops', 'description': 'Laptops and notebooks', 'parent': 'Electronics'},
            {'name': 'Tablets', 'description': 'Tablets and e-readers', 'parent': 'Electronics'},
            {'name': 'Headphones', 'description': 'Audio headphones and earbuds', 'parent': 'Electronics'},
            {'name': 'Smart Watches', 'description': 'Wearable smart devices', 'parent': 'Electronics'},
            {'name': 'Cameras', 'description': 'Digital cameras and accessories', 'parent': 'Electronics'},
            {'name': 'Gaming', 'description': 'Gaming consoles and accessories'},
            {'name': 'Home & Kitchen', 'description': 'Home appliances and kitchen gadgets'},
            {'name': 'Fashion', 'description': 'Clothing and accessories'},
        ]
        
        categories = {}
        for cat_data in categories_data:
            parent = None
            if 'parent' in cat_data:
                parent = categories.get(cat_data['parent'])
            
            category, created = Category.objects.get_or_create(
                name=cat_data['name'],
                defaults={
                    'description': cat_data.get('description', ''),
                    'parent': parent,
                }
            )
            categories[cat_data['name']] = category
            if created:
                self.stdout.write(f'  Created category: {category.name}')

        # Create Brands
        self.stdout.write('Creating brands...')
        brands_data = [
            {'name': 'Apple', 'description': 'Premium technology products'},
            {'name': 'Samsung', 'description': 'Innovative electronics and smartphones'},
            {'name': 'Sony', 'description': 'Entertainment and electronics'},
            {'name': 'Dell', 'description': 'Computers and laptops'},
            {'name': 'HP', 'description': 'Computers and printers'},
            {'name': 'Lenovo', 'description': 'Laptops and computers'},
            {'name': 'Microsoft', 'description': 'Software and hardware'},
            {'name': 'Google', 'description': 'Technology and services'},
            {'name': 'OnePlus', 'description': 'Flagship smartphones'},
            {'name': 'Xiaomi', 'description': 'Affordable smart devices'},
            {'name': 'Nike', 'description': 'Athletic wear and shoes'},
            {'name': 'Adidas', 'description': 'Sports apparel and footwear'},
        ]
        
        brands = {}
        for brand_data in brands_data:
            brand, created = Brand.objects.get_or_create(
                name=brand_data['name'],
                defaults={
                    'slug': slugify(brand_data['name']),
                    'description': brand_data.get('description', ''),
                }
            )
            brands[brand_data['name']] = brand
            if created:
                self.stdout.write(f'  Created brand: {brand.name}')

        # Create Products
        self.stdout.write('Creating products...')
        products_data = [
            # Featured Products
            {
                'name': 'iPhone 15 Pro Max',
                'brand': 'Apple',
                'categories': ['Smartphones'],
                'price': Decimal('1299.99'),
                'original_price': Decimal('1399.99'),
                'quantity': 50,
                'featured': True,
                'description': 'The latest iPhone with A17 Pro chip, titanium design, and advanced camera system.',
                'rating': Decimal('4.8'),
                'review_count': 1250,
                'specifications': {
                    'storage': '256GB',
                    'ram': '8GB',
                    'screen': '6.7" Super Retina XDR',
                    'camera': '48MP Main, 12MP Ultra Wide, 12MP Telephoto',
                    'battery': '4422 mAh',
                    'weight': '221g'
                }
            },
            {
                'name': 'Samsung Galaxy S24 Ultra',
                'brand': 'Samsung',
                'categories': ['Smartphones'],
                'price': Decimal('1199.99'),
                'original_price': Decimal('1299.99'),
                'quantity': 45,
                'featured': True,
                'description': 'Flagship Android phone with S Pen, 200MP camera, and AI features.',
                'rating': Decimal('4.7'),
                'review_count': 980,
                'specifications': {
                    'storage': '256GB',
                    'ram': '12GB',
                    'screen': '6.8" Dynamic AMOLED 2X',
                    'camera': '200MP Main, 12MP Ultra Wide, 50MP Telephoto, 10MP Telephoto',
                    'battery': '5000 mAh',
                    'weight': '233g'
                }
            },
            {
                'name': 'MacBook Pro 16-inch M3 Max',
                'brand': 'Apple',
                'categories': ['Laptops'],
                'price': Decimal('3499.99'),
                'original_price': Decimal('3999.99'),
                'quantity': 30,
                'featured': True,
                'description': 'Powerful laptop for professionals with M3 Max chip, Liquid Retina XDR display.',
                'rating': Decimal('4.9'),
                'review_count': 650,
                'specifications': {
                    'processor': 'Apple M3 Max',
                    'storage': '1TB SSD',
                    'ram': '36GB',
                    'screen': '16.2" Liquid Retina XDR',
                    'graphics': '40-core GPU',
                    'weight': '2.15kg'
                }
            },
            {
                'name': 'Dell XPS 15',
                'brand': 'Dell',
                'categories': ['Laptops'],
                'price': Decimal('1899.99'),
                'original_price': Decimal('2199.99'),
                'quantity': 40,
                'featured': True,
                'description': 'Premium laptop with OLED display, Intel Core i9, and RTX graphics.',
                'rating': Decimal('4.6'),
                'review_count': 420,
                'specifications': {
                    'processor': 'Intel Core i9-13900H',
                    'storage': '512GB SSD',
                    'ram': '32GB',
                    'screen': '15.6" OLED 3.5K',
                    'graphics': 'NVIDIA RTX 4070',
                    'weight': '1.92kg'
                }
            },
            {
                'name': 'Sony WH-1000XM5',
                'brand': 'Sony',
                'categories': ['Headphones'],
                'price': Decimal('399.99'),
                'original_price': Decimal('449.99'),
                'quantity': 100,
                'featured': True,
                'description': 'Industry-leading noise canceling headphones with exceptional sound quality.',
                'rating': Decimal('4.8'),
                'review_count': 2100,
                'specifications': {
                    'type': 'Over-ear',
                    'connectivity': 'Bluetooth 5.2, 3.5mm jack',
                    'battery': '30 hours',
                    'noise_canceling': 'Yes',
                    'weight': '250g'
                }
            },
            {
                'name': 'iPad Pro 12.9-inch',
                'brand': 'Apple',
                'categories': ['Tablets'],
                'price': Decimal('1099.99'),
                'original_price': Decimal('1199.99'),
                'quantity': 60,
                'featured': True,
                'description': 'Powerful tablet with M2 chip, Liquid Retina XDR display, and Apple Pencil support.',
                'rating': Decimal('4.7'),
                'review_count': 890,
                'specifications': {
                    'storage': '256GB',
                    'ram': '8GB',
                    'screen': '12.9" Liquid Retina XDR',
                    'processor': 'Apple M2',
                    'camera': '12MP Wide, 10MP Ultra Wide',
                    'weight': '682g'
                }
            },
            {
                'name': 'Apple Watch Series 9',
                'brand': 'Apple',
                'categories': ['Smart Watches'],
                'price': Decimal('399.99'),
                'original_price': Decimal('429.99'),
                'quantity': 80,
                'featured': True,
                'description': 'Advanced smartwatch with health tracking, GPS, and always-on display.',
                'rating': Decimal('4.6'),
                'review_count': 1500,
                'specifications': {
                    'screen': '45mm Always-On Retina',
                    'battery': '18 hours',
                    'gps': 'Yes',
                    'water_resistance': '50m',
                    'weight': '51.5g'
                }
            },
            {
                'name': 'Sony Alpha 7 IV',
                'brand': 'Sony',
                'categories': ['Cameras'],
                'price': Decimal('2499.99'),
                'original_price': Decimal('2699.99'),
                'quantity': 25,
                'featured': True,
                'description': 'Full-frame mirrorless camera with 33MP sensor and 4K video recording.',
                'rating': Decimal('4.8'),
                'review_count': 560,
                'specifications': {
                    'sensor': '33MP Full-frame',
                    'video': '4K 60p',
                    'iso': '100-51200',
                    'autofocus': '759 phase-detection points',
                    'weight': '658g'
                }
            },
            # Regular Products
            {
                'name': 'OnePlus 12',
                'brand': 'OnePlus',
                'categories': ['Smartphones'],
                'price': Decimal('799.99'),
                'quantity': 70,
                'featured': False,
                'description': 'Flagship killer with Snapdragon 8 Gen 3 and fast charging.',
                'rating': Decimal('4.5'),
                'review_count': 320,
            },
            {
                'name': 'Xiaomi 14 Pro',
                'brand': 'Xiaomi',
                'categories': ['Smartphones'],
                'price': Decimal('699.99'),
                'quantity': 65,
                'featured': False,
                'description': 'Premium features at an affordable price with Leica cameras.',
                'rating': Decimal('4.4'),
                'review_count': 280,
            },
            {
                'name': 'HP Spectre x360',
                'brand': 'HP',
                'categories': ['Laptops'],
                'price': Decimal('1499.99'),
                'quantity': 35,
                'featured': False,
                'description': '2-in-1 convertible laptop with premium design and performance.',
                'rating': Decimal('4.5'),
                'review_count': 190,
            },
            {
                'name': 'Lenovo ThinkPad X1 Carbon',
                'brand': 'Lenovo',
                'categories': ['Laptops'],
                'price': Decimal('1699.99'),
                'quantity': 40,
                'featured': False,
                'description': 'Business laptop with exceptional keyboard and durability.',
                'rating': Decimal('4.6'),
                'review_count': 240,
            },
            {
                'name': 'Samsung Galaxy Tab S9',
                'brand': 'Samsung',
                'categories': ['Tablets'],
                'price': Decimal('899.99'),
                'quantity': 50,
                'featured': False,
                'description': 'Premium Android tablet with S Pen and AMOLED display.',
                'rating': Decimal('4.5'),
                'review_count': 180,
            },
            {
                'name': 'AirPods Pro 2',
                'brand': 'Apple',
                'categories': ['Headphones'],
                'price': Decimal('249.99'),
                'quantity': 150,
                'featured': False,
                'description': 'Wireless earbuds with active noise cancellation and spatial audio.',
                'rating': Decimal('4.7'),
                'review_count': 3200,
            },
            {
                'name': 'Samsung Galaxy Watch 6',
                'brand': 'Samsung',
                'categories': ['Smart Watches'],
                'price': Decimal('299.99'),
                'quantity': 90,
                'featured': False,
                'description': 'Advanced smartwatch with health monitoring and long battery life.',
                'rating': Decimal('4.5'),
                'review_count': 670,
            },
            {
                'name': 'Canon EOS R6 Mark II',
                'brand': 'Sony',  # Using Sony as placeholder
                'categories': ['Cameras'],
                'price': Decimal('2599.99'),
                'quantity': 20,
                'featured': False,
                'description': 'Full-frame mirrorless camera with advanced autofocus and video capabilities.',
                'rating': Decimal('4.7'),
                'review_count': 380,
            },
        ]

        created_count = 0
        for prod_data in products_data:
            brand = brands.get(prod_data['brand'])
            if not brand:
                continue

            slug = slugify(prod_data['name'])
            product, created = Product.objects.get_or_create(
                slug=slug,
                defaults={
                    'name': prod_data['name'],
                    'brand': brand,
                    'price': prod_data['price'],
                    'original_price': prod_data.get('original_price'),
                    'quantity': prod_data.get('quantity', 10),
                    'featured': prod_data.get('featured', False),
                    'description': prod_data.get('description', ''),
                    'rating': prod_data.get('rating', Decimal('0.0')),
                    'review_count': prod_data.get('review_count', 0),
                    'specifications': prod_data.get('specifications', {}),
                    'condition': 'new',
                    'warranty_months': 12,
                }
            )
            
            # Add categories
            for cat_name in prod_data.get('categories', []):
                category = categories.get(cat_name)
                if category:
                    product.category.add(category)
            
            if created:
                created_count += 1
                self.stdout.write(f'  Created product: {product.name}')

        self.stdout.write(self.style.SUCCESS(f'Created {created_count} products'))

        # Create Users
        self.stdout.write('Creating users...')
        
        # Create Admin User
        admin_user, created = CustomUser.objects.get_or_create(
            email='admin@example.com',
            defaults={
                'first_name': 'Admin',
                'last_name': 'User',
                'is_staff': True,
                'is_superuser': True,
                'is_active': True,
            }
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            self.stdout.write(self.style.SUCCESS('  Created admin user: admin@example.com / admin123'))
        else:
            # Update password in case it was changed
            admin_user.set_password('admin123')
            admin_user.save()
            self.stdout.write('  Admin user already exists, password reset to: admin123')
        
        # Create or get profile
        UserProfile.objects.get_or_create(user=admin_user)
        # Create or get preferences
        UserPreferences.objects.get_or_create(user=admin_user)

        # Create Regular User
        regular_user, created = CustomUser.objects.get_or_create(
            email='user@example.com',
            defaults={
                'first_name': 'John',
                'last_name': 'Doe',
                'is_staff': False,
                'is_superuser': False,
                'is_active': True,
            }
        )
        if created:
            regular_user.set_password('user123')
            regular_user.save()
            self.stdout.write(self.style.SUCCESS('  Created regular user: user@example.com / user123'))
        else:
            # Update password in case it was changed
            regular_user.set_password('user123')
            regular_user.save()
            self.stdout.write('  Regular user already exists, password reset to: user123')
        
        # Create or get profile
        UserProfile.objects.get_or_create(user=regular_user)
        # Create or get preferences
        UserPreferences.objects.get_or_create(user=regular_user)

        self.stdout.write(self.style.SUCCESS('\nDatabase seeding completed successfully!'))
        self.stdout.write('\nLogin Credentials:')
        self.stdout.write('   Admin: admin@example.com / admin123')
        self.stdout.write('   User:  user@example.com / user123')

