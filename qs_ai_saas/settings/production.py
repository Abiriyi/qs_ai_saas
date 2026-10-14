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

# Keep manifests tolerant so a single missing optional asset does not crash
# ``collectstatic`` (and therefore the deploy).
WHITENOISE_MANIFEST_STRICT = False
WHITENOISE_KEEP_ONLY_HASHED_FILES = False

LOGGING["root"]["level"] = "ERROR"