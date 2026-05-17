"""Local development settings.

Inherits everything from base.py. Only overrides what genuinely differs
between development and production defaults.
"""

from __future__ import annotations

from .base import *  # noqa: F403

DEBUG = True

SECRET_KEY = env_str(  # noqa: F405
    "DJANGO_SECRET_KEY",
    "local-development-only-not-for-production",
)

ALLOWED_HOSTS = env_csv(  # noqa: F405
    "DJANGO_ALLOWED_HOSTS",
    "localhost,127.0.0.1,testserver",
)

CSRF_TRUSTED_ORIGINS = env_csv(  # noqa: F405
    "DJANGO_CSRF_TRUSTED_ORIGINS",
    "http://localhost:8001,http://127.0.0.1:8001",
)


# -----------------------------------------------------------------------------
# Database — SQLite by default, switchable to Postgres via env
# -----------------------------------------------------------------------------

USE_SQLITE = env_bool("DJANGO_USE_SQLITE", default=True)  # noqa: F405

if USE_SQLITE:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",  # noqa: F405
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env_str("POSTGRES_DB", "skogskvitto"),  # noqa: F405
            "USER": env_str("POSTGRES_USER", "skogskvitto"),  # noqa: F405
            "PASSWORD": env_str("POSTGRES_PASSWORD", ""),  # noqa: F405
            "HOST": env_str("POSTGRES_HOST", "localhost"),  # noqa: F405
            "PORT": env_int("POSTGRES_PORT", 5432),  # noqa: F405
            "CONN_MAX_AGE": env_int("POSTGRES_CONN_MAX_AGE", 0),  # noqa: F405
        }
    }


# -----------------------------------------------------------------------------
# Email — console by default in dev
# -----------------------------------------------------------------------------

EMAIL_BACKEND = env_str(  # noqa: F405
    "EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend",
)


# -----------------------------------------------------------------------------
# Allauth — no email verification in dev
# -----------------------------------------------------------------------------

ACCOUNT_EMAIL_VERIFICATION = env_str(  # noqa: F405
    "ACCOUNT_EMAIL_VERIFICATION",
    "none",
)


# -----------------------------------------------------------------------------
# Security — relaxed for dev
# -----------------------------------------------------------------------------

SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SAMESITE = "Lax"
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False

