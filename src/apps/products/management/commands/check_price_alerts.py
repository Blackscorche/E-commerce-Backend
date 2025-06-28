from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from src.apps.products.models import PriceAlert

class Command(BaseCommand):
    help = 'Check and trigger price alerts for products'

    def add_arguments(self, parser):
        parser.add_argument(
            '--send-notifications',
            action='store_true',
            help='Actually send notifications (default is dry-run)',
        )

    def handle(self, *args, **options):
        active_alerts = PriceAlert.objects.filter(is_active=True)
        triggered_count = 0

        for alert in active_alerts:
            if alert.product.price <= alert.target_price:
                if options['send_notifications']:
                    # In a real implementation, you would send email/SMS here
                    alert.notified_at = timezone.now()
                    alert.is_active = False
                    alert.save()
                    
                    self.stdout.write(
                        f'SENT: Alert for {alert.product.name} to {alert.user.email} '
                        f'(Target: ${alert.target_price}, Current: ${alert.product.price})'
                    )
                else:
                    self.stdout.write(
                        f'WOULD SEND: Alert for {alert.product.name} to {alert.user.email} '
                        f'(Target: ${alert.target_price}, Current: ${alert.product.price})'
                    )
                
                triggered_count += 1

        if options['send_notifications']:
            self.stdout.write(
                self.style.SUCCESS(f'Sent {triggered_count} price alerts')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'DRY RUN: {triggered_count} alerts would be sent')
            )
            self.stdout.write(
                self.style.WARNING('Use --send-notifications to actually send alerts')
            )
