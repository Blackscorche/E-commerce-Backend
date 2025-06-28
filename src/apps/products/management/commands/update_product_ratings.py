from django.core.management.base import BaseCommand
from django.db.models import Avg
from src.apps.products.models import Product, ProductReview

class Command(BaseCommand):
    help = 'Update product ratings based on reviews'

    def add_arguments(self, parser):
        parser.add_argument(
            '--product-id',
            type=int,
            help='Update rating for specific product ID',
        )

    def handle(self, *args, **options):
        if options['product_id']:
            products = Product.objects.filter(id=options['product_id'])
        else:
            products = Product.objects.all()

        updated_count = 0
        
        for product in products:
            reviews = ProductReview.objects.filter(product=product)
            
            if reviews.exists():
                avg_rating = reviews.aggregate(Avg('rating'))['rating__avg']
                review_count = reviews.count()
                
                product.rating = round(avg_rating, 2)
                product.review_count = review_count
                product.save()
                
                updated_count += 1
                
                self.stdout.write(
                    f'Updated {product.name}: {product.rating}/5 ({product.review_count} reviews)'
                )
            else:
                product.rating = 0.0
                product.review_count = 0
                product.save()
                
                updated_count += 1
                
                self.stdout.write(
                    f'Reset {product.name}: No reviews'
                )

        self.stdout.write(
            self.style.SUCCESS(f'Successfully updated {updated_count} products')
        )
