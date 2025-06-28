from django.apps import AppConfig


class CartConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.apps.cart'
    
    def ready(self):
        import src.apps.cart.signals
