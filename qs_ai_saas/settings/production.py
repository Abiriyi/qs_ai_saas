from .base import *

import os


DEBUG = False

ALLOWED_HOSTS = os.getenv(
    "DJANGO_ALLOWED_HOSTS",
    ""
).split(",")


SECURE_BROWSER_XSS_FILTER = True

SECURE_CONTENT_TYPE_NOSNIFF = True

X_FRAME_OPTIONS = "DENY"

CSRF_COOKIE_SECURE = True

SESSION_COOKIE_SECURE = True

SECURE_SSL_REDIRECT = True


STATICFILES_STORAGE = (
    "django.contrib.staticfiles.storage."
    "ManifestStaticFilesStorage"
)

LOGGING["root"]["level"] = "ERROR"