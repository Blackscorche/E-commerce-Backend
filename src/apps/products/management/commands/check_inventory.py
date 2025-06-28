from django.core.management.base import BaseCommand
from django.utils import timezone
from src.apps.products.models import Product, InventoryAlert


class Command(BaseCommand):
    help = 'Check inventory levels and send alerts for low stock products'

    def add_arguments(self, parser):
        parser.add_argument(
            '--create-alerts',
            action='store_true',
            help='Create inventory alerts for products that don\'t have them',
        )
        parser.add_argument(
            '--threshold',
            type=int,
            default=5,
            help='Default low stock threshold for new alerts',
        )

    def handle(self, *args, **options):
        if options['create_alerts']:
            self.create_missing_alerts(options['threshold'])
        
        self.check_inventory_levels()

    def create_missing_alerts(self, threshold):
        products_without_alerts = Product.objects.filter(inventory_alert__isnull=True)
        created_count = 0
        
        for product in products_without_alerts:
            InventoryAlert.objects.create(
                product=product,
                low_stock_threshold=threshold
            )
            created_count += 1
            
        self.stdout.write(
            self.style.SUCCESS(f"Created {created_count} inventory alerts")
        )

    def check_inventory_levels(self):
        alerts = InventoryAlert.objects.select_related('product').all()
        low_stock_products = []
        
        for alert in alerts:
            if alert.check_stock_level():
                low_stock_products.append(alert.product)
                
                if alert.should_send_alert():
                    # In a real implementation, you would send an email/notification here
                    self.stdout.write(
                        self.style.WARNING(
                            f"LOW STOCK ALERT: {alert.product.name} "
                            f"(Current: {alert.product.quantity}, "
                            f"Threshold: {alert.low_stock_threshold})"
                        )
                    )
                    alert.last_alert_sent = timezone.now()
                    alert.save(update_fields=['last_alert_sent'])
        
        self.stdout.write(
            f"Checked {alerts.count()} products, "
            f"found {len(low_stock_products)} with low stock"
        )
        
        if low_stock_products:
            self.stdout.write("\nLow stock products:")
            for product in low_stock_products:
                self.stdout.write(f"  - {product.name}: {product.quantity} units")
        else:
            self.stdout.write(self.style.SUCCESS("All products have adequate stock!"))
