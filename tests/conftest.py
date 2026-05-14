from pathlib import Path

import django
from django.conf import settings

TEMPLATES_DIR = Path(__file__).parent.parent / "apps/core/templates"


def pytest_configure() -> None:
    settings.configure(
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": ":memory:",
            }
        },
        INSTALLED_APPS=[
            "django.contrib.contenttypes",
            "django.contrib.auth",
            "apps.core.apps.CoreConfig",
            "apps.receipts.apps.ReceiptsConfig",
        ],
        AUTH_USER_MODEL="core.User",
        TEMPLATES=[
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "DIRS": [TEMPLATES_DIR],
                "APP_DIRS": False,
                "OPTIONS": {"context_processors": []},
            }
        ],
        DEFAULT_FROM_EMAIL="noreply@test.invalid",
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        SECRET_KEY="test-key",
    )
    django.setup()
