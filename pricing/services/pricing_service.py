from django.core.cache import cache
from core.cache import tenant_cache_key
from pricing.models import RateLibrary, RateAudit
from decimal import Decimal
from core.tenant import get_current_org
from django.db.models import Q

from qs_ai_project.ai_pricing import (
    get_rate_from_ai,
    get_rate_from_library,
)

class PricingService:

    @staticmethod
    def get_rate(...):
        ...

    @staticmethod
    def store_ai_rate(*, organization, project, element, unit, rate):

        obj, created = RateLibrary.objects.update_or_create(
            organization=organization,
            project=project,
            element=element,
            unit=unit,
            defaults={
                "base_rate": rate,
                "source": "ai",
                "is_active": True,
            }
        )

        RateAudit.objects.create(
            organization=organization,
            project=project,
            element=element,
            unit=unit,
            new_rate=rate,
            action="ai_generate",
            source="ai"
        )

        cache.set(
            f"org:{organization.id}:rate:{element}:{unit}",
            float(rate),
            86400
        )

        return obj