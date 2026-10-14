from .base import *

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "test.sqlite3",
    }
}

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Use an in-process cache for tests so the suite needs no running Redis. This
# keeps CI self-contained (a GitHub Actions runner has no Redis) and makes the
# run deterministic. Throttling is also disabled below, so the cache is only
# exercised by direct cache usage (e.g. PricingService.store_ai_rate).
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# Disable rate limiting during tests: throttling state lives in the shared
# Redis cache, which would make the suite order-dependent and flaky. No test
# asserts on throttling, so turning it off keeps runs deterministic.
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_THROTTLE_CLASSES": [],
    "DEFAULT_THROTTLE_RATES": {
        "anon": None,
        "user": None,
        "document_upload": None,
        "boq_generate": None,
        "boq_price": None,
    },
}
