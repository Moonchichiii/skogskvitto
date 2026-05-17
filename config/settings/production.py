"""Production settings — strict, secure, fail-fast on misconfiguration."""

from __future__ import annotations

import os

import dj_database_url

from .base import *  # noqa: F403

DEBUG = False


# -----------------------------------------------------------------------------
# Required env vars — fail fast if missing
# -----------------------------------------------------------------------------

SECRET_KEY = env_required("DJANGO_SECRET_KEY")  # noqa: F405

ALLOWED_HOSTS = env_csv("DJANGO_ALLOWED_HOSTS")  # noqa: F405
if not ALLOWED_HOSTS:
    raise ValueError("DJANGO_ALLOWED_HOSTS must be set in production")

CSRF_TRUSTED_ORIGINS = env_csv("DJANGO_CSRF_TRUSTED_ORIGINS")  # noqa: F405
if not CSRF_TRUSTED_ORIGINS:
    raise ValueError("DJANGO_CSRF_TRUSTED_ORIGINS must be set in production")

DATABASE_URL = env_required("DATABASE_URL")  # noqa: F405


# -----------------------------------------------------------------------------
# Database
# -----------------------------------------------------------------------------

DATABASES = {
    "default": dj_database_url.parse(
        DATABASE_URL,
        conn_max_age=env_int("POSTGRES_CONN_MAX_AGE", 60),  # noqa: F405
        ssl_require=True,
    )
}


# -----------------------------------------------------------------------------
# Cloudinary — required in production
# -----------------------------------------------------------------------------

CLOUDINARY_URL = env_str("CLOUDINARY_URL", "")  # noqa: F405
CLOUDINARY_CLOUD_NAME = env_str("CLOUDINARY_CLOUD_NAME", "")  # noqa: F405
CLOUDINARY_API_KEY = env_str("CLOUDINARY_API_KEY", "")  # noqa: F405
CLOUDINARY_API_SECRET = env_str("CLOUDINARY_API_SECRET", "")  # noqa: F405

if not (CLOUDINARY_URL or CLOUDINARY_CLOUD_NAME):
    raise ValueError("Cloudinary must be configured in production")

if CLOUDINARY_URL:
    os.environ.setdefault("CLOUDINARY_URL", CLOUDINARY_URL)

CLOUDINARY_STORAGE = {
    "CLOUD_NAME": CLOUDINARY_CLOUD_NAME,
    "API_KEY": CLOUDINARY_API_KEY,
    "API_SECRET": CLOUDINARY_API_SECRET,
    "SECURE": True,
}


# -----------------------------------------------------------------------------
# Storages — Cloudinary media + WhiteNoise compressed static
# -----------------------------------------------------------------------------

STORAGES = {
    "default": {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}


# -----------------------------------------------------------------------------
# Security — strict
# -----------------------------------------------------------------------------

SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", default=True)  # noqa: F405
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = env_int("DJANGO_SECURE_HSTS_SECONDS", 31536000)  # noqa: F405
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")


# -----------------------------------------------------------------------------
# Logging — louder default in production
# -----------------------------------------------------------------------------

# Inherit LOGGING from base but bump root level to INFO with WARNING for Django.
LOGGING["root"]["level"] = env_str("DJANGO_LOG_LEVEL", "INFO")  # noqa: F405
LOGGING["loggers"]["django"]["level"] = "WARNING"  # noqa: F405
