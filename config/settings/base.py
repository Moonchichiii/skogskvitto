"""Base settings — defaults shared by all environments.

Environment-specific overrides live in local.py, test.py and production.py.
Each environment file must explicitly set or override anything it cares about;
this file holds defaults that are safe everywhere.
"""

from __future__ import annotations

from pathlib import Path

from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent.parent


# -----------------------------------------------------------------------------
# Env helpers
# -----------------------------------------------------------------------------


def env_str(name: str, default: str = "") -> str:
    value = config(name, default=default)
    return default if value is None else str(value).strip()


def env_csv(name: str, default: str = "") -> list[str]:
    value = env_str(name, default)
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def env_int(name: str, default: int) -> int:
    value = env_str(name, "")
    return default if value == "" else int(value)


def env_bool(name: str, default: bool = False) -> bool:
    return config(name, default=default, cast=bool)


def env_required(name: str) -> str:
    value = env_str(name, "")
    if not value:
        raise ValueError(f"{name} must be set")
    return value


# -----------------------------------------------------------------------------
# Core
# -----------------------------------------------------------------------------

SECRET_KEY = env_str("DJANGO_SECRET_KEY", "")
DEBUG = env_bool("DJANGO_DEBUG", False)

ALLOWED_HOSTS = env_csv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_csv("DJANGO_CSRF_TRUSTED_ORIGINS", "")


# -----------------------------------------------------------------------------
# Applications
# -----------------------------------------------------------------------------

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "csp",
    "cloudinary",
    "cloudinary_storage",
    "django_rq",
]

LOCAL_APPS = [
    "apps.accounts.apps.AccountsConfig",
    "apps.core.apps.CoreConfig",
    "apps.integrations.apps.IntegrationsConfig",
    "apps.billing.apps.BillingConfig",
    "apps.receipts.apps.ReceiptsConfig",
    "apps.scanning.apps.ScanningConfig",
    "apps.exports.apps.ExportsConfig",
    "apps.properties.apps.PropertiesConfig",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS


# -----------------------------------------------------------------------------
# Middleware
# -----------------------------------------------------------------------------

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "csp.middleware.CSPMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

SITE_ID = 1
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# -----------------------------------------------------------------------------
# Internationalization
# -----------------------------------------------------------------------------

LANGUAGE_CODE = "sv-se"
TIME_ZONE = "Europe/Stockholm"
USE_I18N = True
USE_TZ = True


# -----------------------------------------------------------------------------
# Templates
# -----------------------------------------------------------------------------

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.legal_contact",
                "apps.core.context_processors.public_assets",
                "apps.core.context_processors.site_meta",
            ],
        },
    }
]


# -----------------------------------------------------------------------------
# Auth
# -----------------------------------------------------------------------------

AUTH_USER_MODEL = "accounts.User"

LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/dashboard/"
LOGOUT_REDIRECT_URL = "/accounts/login/"

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_USER_MODEL_EMAIL_FIELD = "email"
ACCOUNT_USER_DISPLAY = "apps.accounts.services.user_display"

ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_EMAIL_UNKNOWN_ACCOUNTS = False
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_EMAIL_CONFIRMATION_AUTHENTICATED_REDIRECT_URL = "/dashboard/"
ACCOUNT_EMAIL_CONFIRMATION_ANONYMOUS_REDIRECT_URL = "/accounts/login/"
ACCOUNT_LOGOUT_ON_GET = False
ACCOUNT_EMAIL_SUBJECT_PREFIX = "[SkogsKvitto] "

SOCIALACCOUNT_ONLY = False
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_STORE_TOKENS = False
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "SCOPE": ["openid", "email", "profile"],
        "AUTH_PARAMS": {"prompt": "select_account"},
        "APP": {
            "client_id": env_str("GOOGLE_OAUTH_CLIENT_ID", ""),
            "secret": env_str("GOOGLE_OAUTH_CLIENT_SECRET", ""),
            "key": "",
        },
    }
}


# -----------------------------------------------------------------------------
# Database
# -----------------------------------------------------------------------------

# Each environment file (local/test/production) overrides DATABASES.
# Base only defines an empty placeholder so static analysis doesn't choke.
DATABASES: dict[str, dict[str, object]] = {}


# -----------------------------------------------------------------------------
# Cache & Redis
# -----------------------------------------------------------------------------

REDIS_URL = env_str("REDIS_URL", "")

if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
            "TIMEOUT": 300,
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "skogskvitto-locmem",
        }
    }


# -----------------------------------------------------------------------------
# Async worker queues (django-rq)
# -----------------------------------------------------------------------------

# RQ_QUEUES is read by django_rq once it's wired in INSTALLED_APPS.
# Defining it here so env vars are documented and the structure is locked.
_RQ_REDIS_URL = REDIS_URL or "redis://localhost:6379/0"

RQ_QUEUES = {
    "default": {
        "URL": _RQ_REDIS_URL,
        "DEFAULT_TIMEOUT": 360,
        "ASYNC": bool(REDIS_URL),
    },
    "scanning": {
        "URL": _RQ_REDIS_URL,
        "DEFAULT_TIMEOUT": 120,
        "ASYNC": bool(REDIS_URL),
    },
}


# -----------------------------------------------------------------------------
# Email
# -----------------------------------------------------------------------------

EMAIL_BACKEND = env_str(
    "EMAIL_BACKEND",
    "django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_HOST = env_str("EMAIL_HOST", "localhost")
EMAIL_PORT = env_int("EMAIL_PORT", 1025)
EMAIL_HOST_USER = env_str("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = env_str("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", False)
DEFAULT_FROM_EMAIL = env_str("DEFAULT_FROM_EMAIL", "noreply@example.test")
SERVER_EMAIL = DEFAULT_FROM_EMAIL


# -----------------------------------------------------------------------------
# Product settings
# -----------------------------------------------------------------------------

FREEMIUM_RECEIPT_LIMIT = env_int("FREEMIUM_RECEIPT_LIMIT", 5)

SUPPORT_CONTACT = env_str("SUPPORT_CONTACT", "support@skogskvitto.se")
PRIVACY_CONTACT = env_str("PRIVACY_CONTACT", "integritet@skogskvitto.se")

SITE_URL = env_str("SITE_URL", "https://skogskvitto.se")
DEFAULT_OG_IMAGE = env_str(
    "DEFAULT_OG_IMAGE",
    "https://res.cloudinary.com/dakjlrean/image/upload/f_jpg,q_auto:good,w_1200,h_630,c_fill/skogskvitto/js7drdp51fxqslknqtif",
)


# -----------------------------------------------------------------------------
# External integrations
# -----------------------------------------------------------------------------

OPENAI_API_KEY = env_str("OPENAI_API_KEY", "")
OPENAI_MODEL = env_str("OPENAI_MODEL", "gpt-4.1-mini")

STRIPE_SECRET_KEY = env_str("STRIPE_SECRET_KEY", "")
STRIPE_PRICE_MONTHLY_ID = env_str("STRIPE_PRICE_MONTHLY_ID", "")
STRIPE_PRICE_YEARLY_ID = env_str("STRIPE_PRICE_YEARLY_ID", "")

CLOUDINARY_URL = env_str("CLOUDINARY_URL", "")
CLOUDINARY_CLOUD_NAME = env_str("CLOUDINARY_CLOUD_NAME", "")
CLOUDINARY_API_KEY = env_str("CLOUDINARY_API_KEY", "")
CLOUDINARY_API_SECRET = env_str("CLOUDINARY_API_SECRET", "")

MARKETING_HERO_IMAGE_PUBLIC_ID = env_str(
    "MARKETING_HERO_IMAGE_PUBLIC_ID",
    "skogskvitto/js7drdp51fxqslknqtif",
)


# -----------------------------------------------------------------------------
# Static & media
# -----------------------------------------------------------------------------

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "/_private-media/"
MEDIA_ROOT = BASE_DIR / "private_media"

# Django 5+ STORAGES — overridden in production.py to use Cloudinary + WhiteNoise
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}


# -----------------------------------------------------------------------------
# File upload limits
# -----------------------------------------------------------------------------

# Modern smartphone receipts run 4–8 MB. Set generous limits with hard ceiling.
FILE_UPLOAD_MAX_MEMORY_SIZE = env_int("FILE_UPLOAD_MAX_MEMORY_SIZE", 10 * 1024 * 1024)
DATA_UPLOAD_MAX_MEMORY_SIZE = env_int("DATA_UPLOAD_MAX_MEMORY_SIZE", 10 * 1024 * 1024)
DATA_UPLOAD_MAX_NUMBER_FIELDS = 1000

FILE_UPLOAD_PERMISSIONS = 0o640
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o750


# -----------------------------------------------------------------------------
# Security
# -----------------------------------------------------------------------------

SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

# CSP — direct-to-Cloudinary upload requires connect-src to api.cloudinary.com
CONTENT_SECURITY_POLICY = {
    "DIRECTIVES": {
        "default-src": ("'self'",),
        "base-uri": ("'self'",),
        "form-action": ("'self'",),
        "frame-ancestors": ("'none'",),
        "object-src": ("'none'",),
        "script-src": (
            "'self'",
            "'unsafe-eval'",  # Alpine.js inline expression evaluation
        ),
        "style-src": ("'self'",),
        "img-src": (
            "'self'",
            "data:",
            "blob:",
            "https://res.cloudinary.com",
        ),
        "connect-src": (
            "'self'",
            "https://api.cloudinary.com",
        ),
        "font-src": ("'self'",),
    }
}


# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------

LOG_LEVEL = env_str("DJANGO_LOG_LEVEL", "INFO")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname:8s} {name}: {message}",
            "datefmt": "%Y-%m-%d %H:%M:%S",
            "style": "{",
        },
        "simple": {
            "format": "{levelname:8s} {name}: {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
            "level": LOG_LEVEL,
        },
    },
    "root": {
        "handlers": ["console"],
        "level": LOG_LEVEL,
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.security": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "apps": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
    },
}
