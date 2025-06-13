from django.apps import AppConfig

class FaturasConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'faturas'

    verbose_name = 'Faturas Manager'
    def ready(self):
     import faturas.signals