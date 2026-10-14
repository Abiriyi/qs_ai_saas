# core/throttling.py
from rest_framework.throttling import ScopedRateThrottle


class DocumentUploadThrottle(ScopedRateThrottle):
    """Limits PDF uploads, which are expensive (extraction + AI generation)."""

    scope = "document_upload"


class BoQGenerateThrottle(ScopedRateThrottle):
    """Limits on-demand AI BoQ generation requests."""

    scope = "boq_generate"


class BoQPriceThrottle(ScopedRateThrottle):
    """Limits BoQ pricing runs (rate-library + possible AI lookups)."""

    scope = "boq_price"
