from .base import *

import os

# Initialise error reporting as early as possible. No-ops unless SENTRY_DSN is
# set, so this is safe in every environment.
from core.sentry import init_sentry

init_sentry()


DEBUG = False

ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "").split(",")
ALLOWED_HOSTS = [h.strip() for h in ALLOWED_HOSTS if h.strip()]

# Fly.io terminates TLS at the edge and forwards to the app over its internal
# network, so allow the wildcard app domain for CSRF by default. Override with
# an explicit DJANGO_CSRF_TRUSTED_ORIGINS if you serve a custom domain.
_csrf_origins = os.getenv("DJANGO_CSRF_TRUSTED_ORIGINS", "")
CSRF_TRUSTED_ORIGINS = [o.strip() for o in _csrf_origins.split(",") if o.strip()]

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SECURE_SSL_REDIRECT = True

SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Fly.io health checks reach the app over plain HTTP on the internal port.
# Exempt the health path from the HTTPS redirect so the probe gets a 200
# instead of a 301 (which would otherwise mark every machine unhealthy).
SECURE_REDIRECT_EXEMPT = [r"^healthz/$"]

# Static files are collected into STATIC_ROOT at build time and served
# directly by WhiteNoise (added to MIDDLEWARE in base.py). The compressed
# manifest storage adds content-hashed filenames + brotli/gzip so we get
# long-lived caching without a separate CDN.
STORAGES["staticfiles"]["BACKEND"] = (
    "whitenoise.storage.CompressedManifestStaticFilesStorage"
)

# In production, media uploads go to Tigris (S3-compatible) object storage via
# django-storages. The AWS_* / TIGRIS_* settings are inherited from base.py.
STORAGES["default"]["BACKEND"] = "storages.backends.s3.S3Storage"

# Keep manifests tolerant so a single missing optional asset does not crash
# ``collectstatic`` (and therefore the deploy).
WHITENOISE_MANIFEST_STRICT = False
WHITENOISE_KEEP_ONLY_HASHED_FILES = False

LOGGING["root"]["level"] = "ERROR"

# ---------------------------------------------------------------------------
# Email (password reset, notifications)
# ---------------------------------------------------------------------------
# SMTP is configured via environment so the provider (Postmark, SES, Mailgun,
# SendGrid, ...) can be swapped without a code change. If EMAIL_HOST is not
# set we fall back to console output so the app never crashes on boot.
EMAIL_HOST = os.getenv("EMAIL_HOST", "")
if EMAIL_HOST:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
    EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
    EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
    EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "true").lower() in ("1", "true", "yes")
    EMAIL_TIMEOUT = int(os.getenv("EMAIL_TIMEOUT", "10"))
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

DEFAULT_FROM_EMAIL = os.getenv(
    "DEFAULT_FROM_EMAIL",
    "QS AI <no-reply@qs-ai.example>",
)