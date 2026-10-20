# core/ratelimit.py
"""
Cache-backed rate limiting for the non-DRF auth views.

Django's function/class-based views are outside DRF's throttling, so the login
and signup endpoints need their own protection against brute-force and mass
account creation. This is a deliberately small fixed-window counter stored in
the Django cache.

It **fails open**: if the cache is unavailable (e.g. Redis is down) we never
block legitimate sign-ins — availability of authentication outweighs the
marginal loss of throttling during a cache outage.
"""

import time

from django.core.cache import cache

# Login: allow a burst but stop scripted guessing. Generous enough that a
# human who mistypes a few times is unaffected.
LOGIN_PER_IP_LIMIT = 12
LOGIN_PER_IP_WINDOW = 300      # 5 minutes
LOGIN_PER_EMAIL_LIMIT = 6
LOGIN_PER_EMAIL_WINDOW = 300   # 5 minutes

# Signup: far stricter, to discourage mass account creation from one address.
SIGNUP_PER_IP_LIMIT = 5
SIGNUP_PER_IP_WINDOW = 3600    # 1 hour


def get_client_ip(request):
    """
    Best-effort client IP.

    On Fly.io (and most proxies) the real client IP is forwarded in
    ``X-Forwarded-For``; the first entry is the originating client.
    """
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


def check_rate_limit(key, limit, window_seconds):
    """
    Increment a fixed-window counter for ``key`` and report whether the caller
    is within ``limit`` for the current ``window_seconds`` window.

    Returns ``(allowed, retry_after_seconds)``. ``retry_after`` is only
    meaningful when ``allowed`` is False.
    """
    now = int(time.time())
    window = now // max(window_seconds, 1)
    cache_key = f"ratelimit:{key}:{window}"

    try:
        current = cache.get(cache_key, 0)
    except Exception:
        # Fail open on cache errors: never lock users out because of infra.
        return True, 0

    if current >= limit:
        retry_after = max(window_seconds - (now % window_seconds), 1)
        return False, retry_after

    try:
        # +1 for this attempt; expire just after the window rolls over.
        cache.set(cache_key, current + 1, timeout=window_seconds + 1)
    except Exception:
        pass

    return True, 0
