# core/sentry.py
"""
Optional Sentry integration.

Sentry is initialised only when ``SENTRY_DSN`` is present, so local/dev/test
environments are completely unaffected. The integration is deliberately
conservative:

* ``send_default_pii=False`` keeps user IPs, cookies and auth headers out of
  events by default.
* a ``before_send`` scrubber redacts anything that looks like a secret
  (OpenAI/Tigris keys, JWTs, passwords, tokens) as defence-in-depth, in case a
  value ever leaks into an error message, request body or extra context.
"""

import logging
import os
import re

logger = logging.getLogger(__name__)

# Substrings that mark a key/value as sensitive. Matched case-insensitively.
_SENSITIVE_KEY_PATTERN = re.compile(
    r"(secret|password|passwd|token|api[-_]?key|authorization|"
    r"access[-_]?key|private[-_]?key|csrf|session|cookie|"
    r"openai|tigris|bearer|credential)",
    re.IGNORECASE,
)

# Well-known secret shapes we redact even when the key name is innocuous.
_VALUE_PATTERNS = [
    re.compile(r"sk-proj-[A-Za-z0-9_\-]+"),          # OpenAI project keys
    re.compile(r"sk-[A-Za-z0-9]{20,}"),              # OpenAI legacy keys
    re.compile(r"tid_[A-Za-z0-9_\-]+"),              # Tigris access key id
    re.compile(r"tsec_[A-Za-z0-9_\-]+"),             # Tigris secret key
    re.compile(r"eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+"),  # JWT
]

_REDACTED = "[Filtered]"


def _scrub_value(value):
    if isinstance(value, str):
        scrubbed = value
        for pattern in _VALUE_PATTERNS:
            scrubbed = pattern.sub(_REDACTED, scrubbed)
        return scrubbed
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    if isinstance(value, dict):
        return _scrub_mapping(value)
    if isinstance(value, (list, tuple)):
        return [_scrub_value(item) for item in value]
    return value


def _scrub_mapping(mapping):
    cleaned = {}
    for key, value in mapping.items():
        if isinstance(key, str) and _SENSITIVE_KEY_PATTERN.search(key):
            cleaned[key] = _REDACTED
        else:
            cleaned[key] = _scrub_value(value)
    return cleaned


def _before_send(event, hint):
    """Redact secrets from the event payload before it leaves the process."""
    try:
        if isinstance(event.get("extra"), dict):
            event["extra"] = _scrub_mapping(event["extra"])

        request = event.get("request")
        if isinstance(request, dict):
            headers = request.get("headers")
            if isinstance(headers, dict):
                request["headers"] = _scrub_mapping(headers)
            if isinstance(request.get("data"), dict):
                request["data"] = _scrub_mapping(request["data"])
            # Drop cookies entirely — never useful for debugging, always risky.
            request.pop("cookies", None)

        # Scrub the exception message itself (e.g. an OpenAI 401 that echoes
        # the offending key, as seen in a past document-processing failure).
        exception = event.get("exception")
        if isinstance(exception, dict):
            values = exception.get("values")
            if isinstance(values, list):
                for entry in values:
                    if isinstance(entry, dict) and isinstance(entry.get("value"), str):
                        entry["value"] = _scrub_value(entry["value"])

        logentry = event.get("logentry")
        if isinstance(logentry, dict) and isinstance(logentry.get("message"), str):
            logentry["message"] = _scrub_value(logentry["message"])
    except Exception:  # pragma: no cover - scrubbing must never crash reporting
        logger.exception("Sentry before_send scrubber failed")
    return event


def init_sentry():
    """
    Initialise Sentry if a DSN is configured. Safe to call unconditionally —
    it no-ops (and logs) when ``SENTRY_DSN`` is unset.
    """
    dsn = os.getenv("SENTRY_DSN", "").strip()
    if not dsn:
        logger.info("SENTRY_DSN not set; Sentry reporting disabled.")
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.celery import CeleryIntegration
        from sentry_sdk.integrations.django import DjangoIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
        from sentry_sdk.integrations.redis import RedisIntegration
    except ImportError:
        logger.warning("sentry-sdk is not installed; Sentry reporting disabled.")
        return False

    environment = os.getenv("SENTRY_ENVIRONMENT", "production")

    try:
        sample_rate = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1"))
    except (TypeError, ValueError):
        sample_rate = 0.1

    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
            RedisIntegration(),
            # Capture ERROR+ logs as Sentry events; INFO stays as breadcrumbs.
            LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
        ],
        send_default_pii=False,
        traces_sample_rate=sample_rate,
        before_send=_before_send,
    )

    logger.info("Sentry initialised for environment '%s'.", environment)
    return True
