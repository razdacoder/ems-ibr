from django.apps import AppConfig


class EmsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ems'

    def ready(self):
        from ems import signals  # noqa: F401
