from __future__ import annotations

import os

from .base import *  # noqa: F403

DEBUG = False

SECRET_KEY = env_required("DJANGO_SECRET_KEY")  # noqa: F405

ALLOWED_HOSTS = env_csv("DJANGO_ALLOWED_HOSTS")  # noqa: F405
if not ALLOWED_HOSTS:
    raise ValueError("DJANGO_ALLOWED_HOSTS must be set in production")

CSRF_TRUSTED_ORIGINS = env_csv("DJANGO_CSRF_TRUSTED_ORIGINS")  # noqa: F405
if not CSRF_TRUSTED_ORIGINS:
    raise ValueError("DJANGO_CSRF_TRUSTED_ORIGINS must be set in production")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env_required("POSTGRES_DB"),  # noqa: F405
        "USER": env_required("POSTGRES_USER"),  # noqa: F405
        "PASSWORD": env_required("POSTGRES_PASSWORD"),  # noqa: F405
        "HOST": env_required("POSTGRES_HOST"),  # noqa: F405
        "PORT": env_int("POSTGRES_PORT", 5432),  # noqa: F405
        "CONN_MAX_AGE": env_int("POSTGRES_CONN_MAX_AGE", 60),  # noqa: F405
        "OPTIONS": {
            "sslmode": env_str("POSTGRES_SSLMODE", "require"),  # noqa: F405
        },
    }
}

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

STORAGES = {
    "default": {"BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
    },
}

SECURE_SSL_REDIRECT = config("DJANGO_SECURE_SSL_REDIRECT", default=True, cast=bool)  # noqa: F405
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = env_int("DJANGO_SECURE_HSTS_SECONDS", 31536000)  # noqa: F405
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")