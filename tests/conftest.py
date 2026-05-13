import django
from django.conf import settings

TEMPLATES_DIR = (
    __file__.replace("tests/conftest.py", "")
    + "apps/core/templates"
)


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
        ],
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
    )
    django.setup()
