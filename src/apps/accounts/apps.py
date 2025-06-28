from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = "src.apps.accounts"
    default_auto_field = 'django.db.models.BigAutoField'
    
    def ready(self):
        import src.apps.accounts.signals
