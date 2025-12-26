# app/apps.py
from django.apps import AppConfig

class AppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "app"

    def ready(self):
        # If you use signals, import them here
        # import app.signals
        pass
