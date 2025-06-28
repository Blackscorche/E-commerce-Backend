from django.apps import AppConfig


class ProductsConfig(AppConfig):
    name = "src.apps.products"
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        import src.apps.products.signals
