from django.core.management.base import BaseCommand
from src.apps.payments.models import PaymentMethod


class Command(BaseCommand):
    help = 'Setup initial payment methods'

    def handle(self, *args, **options):
        payment_methods = [
            {
                'name': 'Paystack',
                'provider': 'paystack',
                'is_active': True,
                'configuration': {
                    'supports_cards': True,
                    'supports_bank_transfer': True,
                    'supports_ussd': True,
                    'supports_mobile_money': True,
                }
            },
            {
                'name': 'Bank Transfer',
                'provider': 'bank_transfer',
                'is_active': True,
                'configuration': {
                    'manual_verification': True,
                    'processing_time': '1-3 business days',
                }
            },
            {
                'name': 'Cash on Delivery',
                'provider': 'cash',
                'is_active': True,
                'configuration': {
                    'delivery_fee_applicable': True,
                    'verification_required': False,
                }
            },
        ]

        for method_data in payment_methods:
            method, created = PaymentMethod.objects.get_or_create(
                name=method_data['name'],
                provider=method_data['provider'],
                defaults={
                    'is_active': method_data['is_active'],
                    'configuration': method_data['configuration'],
                }
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created payment method: {method.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Payment method already exists: {method.name}')
                )

        self.stdout.write(
            self.style.SUCCESS('Payment methods setup completed!')
        )
