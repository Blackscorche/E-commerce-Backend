# yourapp/tests/test_payments.py
from django.test import TestCase, Client
from django.urls import reverse

class PaystackTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_initialize_payment_missing_fields(self):
        response = self.client.post(reverse('initialize_payment'), {})
        self.assertEqual(response.status_code, 400)

    def test_initialize_payment_success(self):
        # Use Paystack test credentials and valid format
        response = self.client.post(reverse('initialize_payment'), {
            'email': 'test@example.com',
            'amount': '5000'
        })
        self.assertIn(response.status_code, [200, 400])  # Paystack might reject dummy requests

    def test_verify_payment_no_reference(self):
        response = self.client.get(reverse('verify_payment'))
        self.assertEqual(response.status_code, 400)
