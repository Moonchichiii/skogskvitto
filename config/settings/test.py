"""Test settings — fast, isolated, deterministic."""

from __future__ import annotations

import tempfile
from pathlib import Path

from .base import *  # noqa: F403

DEBUG = False
SECRET_KEY = "test-secret-not-for-production"  # noqa: S105

ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]
CSRF_TRUSTED_ORIGINS = []


# -----------------------------------------------------------------------------
# Database — in-memory SQLite
# -----------------------------------------------------------------------------

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "test.sqlite3",  # noqa: F405
    }
}


# -----------------------------------------------------------------------------
# Email — in-memory
# -----------------------------------------------------------------------------

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"


# -----------------------------------------------------------------------------
# Cache — local memory only, ignore env REDIS_URL
# -----------------------------------------------------------------------------

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "test",
    }
}


# -----------------------------------------------------------------------------
# Media — isolated tempdir so tests don't pollute the dev media folder
# -----------------------------------------------------------------------------

MEDIA_ROOT = Path(tempfile.mkdtemp(prefix="skogskvitto-test-media-"))


# -----------------------------------------------------------------------------
# Hashing — fastest possible for tests
# -----------------------------------------------------------------------------

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]


# -----------------------------------------------------------------------------
# Security — disabled for tests
# -----------------------------------------------------------------------------

SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False


# -----------------------------------------------------------------------------
# Logging — quiet
# -----------------------------------------------------------------------------

LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "handlers": {
        "null": {"class": "logging.NullHandler"},
    },
    "root": {
        "handlers": ["null"],
        "level": "CRITICAL",
    },
}
