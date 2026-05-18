from django.apps import AppConfig


class PropertiesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.properties"
    label = "properties"
    verbose_name = "Fastigheter"

    def ready(self) -> None:
        # Register signals (e.g. auto-create default Property on user signup)
        from apps.properties import signals  # noqa: F401
