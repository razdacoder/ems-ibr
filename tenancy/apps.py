from django.apps import AppConfig


class TenancyConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tenancy"

    def ready(self):
        # Capture points that hang off signals (spec 0004).
        from tenancy.observability import middleware, signals, tasks  # noqa: F401

        signals.connect()
