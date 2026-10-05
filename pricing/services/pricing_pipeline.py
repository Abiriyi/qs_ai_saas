import logging

from pricing.models import RateLibrary
from pricing.services.confidence import PricingConfidenceService

try:
    from qs_ai_project.ai_pricing import get_rate_from_ai, get_rate_from_library
except ImportError:
    from engine.ai_pricing import get_rate_from_ai, get_rate_from_library

logger = logging.getLogger(__name__)


class PricingPipeline:

    def __init__(self, project):
        self.project = project

    def price_item(self, item):
        item = dict(item)
        rate = self._get_org_rate(item)

        if rate is not None:
            source = "org_library"
            rate_value = float(rate.base_rate)
            confidence = PricingConfidenceService.calculate_confidence(source)
        else:
            source = "ai_generated"
            rate_value = self._generate_ai_rate(item)
            confidence = PricingConfidenceService.calculate_confidence(
                source,
                ai_similarity=0.60,
            )

        pricing_result = {
            "rate": rate_value,
            "source": source,
            "confidence": confidence,
        }

        tenant_id = getattr(getattr(self.project, "organization", None), "id", None)
        logger.info(
            "pricing_completed",
            extra={
                "tenant_id": str(tenant_id) if tenant_id else None,
                "project_id": str(getattr(self.project, "id", "")),
                "item_description": item.get("description") or item.get("element") or "",
                "source": source,
                "confidence": confidence,
            },
        )

        return pricing_result

    def _get_org_rate(self, item):
        organization = getattr(self.project, "organization", None)
        if organization is None or getattr(organization, "pk", None) is None:
            return None

        element = item.get("element") or item.get("description") or ""
        description = item.get("description") or ""
        unit = item.get("unit") or ""

        queryset = RateLibrary.objects.filter(
            organization=organization,
            is_active=True,
            base_rate__isnull=False,
        )

        if element:
            queryset = queryset.filter(
                element__icontains=element,
            )
        if description:
            queryset = queryset.filter(
                description__icontains=description,
            )
        if unit:
            queryset = queryset.filter(
                unit__icontains=unit,
            )

        return queryset.order_by("-updated_at").first()

    def _generate_ai_rate(self, item):
        element = item.get("element") or item.get("description") or ""
        description = item.get("description") or element
        unit = item.get("unit") or ""
        location = item.get("location") or "Kaduna"

        library_rate = get_rate_from_library(element, description=description, unit=unit, location=location)
        if library_rate is not None:
            return float(library_rate)

        ai_rate = get_rate_from_ai(element, description, unit, location)
        if ai_rate is not None:
            return float(ai_rate)

        return 0.0
        