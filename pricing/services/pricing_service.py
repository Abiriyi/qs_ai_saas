from decimal import Decimal

from django.core.cache import cache

from core.tenant import get_current_org
from pricing.models import RateAudit, RateLibrary

try:
    from qs_ai_project.ai_pricing import get_rate_from_ai, get_rate_from_library
except ImportError:
    from engine.ai_pricing import get_rate_from_ai, get_rate_from_library


class PricingService:

    @staticmethod
    def get_rate(*, organization=None, project=None, element, description="", unit="", location="Kaduna"):
        org = organization or get_current_org()
        filters = {"is_active": True, "base_rate__isnull": False}

        if org is not None:
            filters["organization"] = org

        if project is not None:
            filters["project"] = project

        rate_obj = (
            RateLibrary.objects.filter(**filters)
            .filter(
                element__icontains=element,
                unit__icontains=unit,
            )
            .order_by("-updated_at")
            .first()
        )

        if rate_obj is not None and rate_obj.base_rate is not None:
            return float(rate_obj.base_rate)

        library_rate = get_rate_from_library(element, description=description, unit=unit, location=location)
        if library_rate is not None:
            return float(library_rate)

        ai_rate = get_rate_from_ai(element, description, unit, location)
        if ai_rate is not None:
            return float(ai_rate)

        return None

    @staticmethod
    def store_ai_rate(*, organization, project, element, description="", unit="", rate, location="Kaduna"):
        rate_value = Decimal(str(rate))

        obj, _created = RateLibrary.objects.update_or_create(
            organization=organization,
            project=project,
            element=element,
            unit=unit,
            defaults={
                "description": description,
                "location": location,
                "base_rate": rate_value,
                "source": "ai",
                "review_status": "approved",
                "is_active": True,
                "confidence_score": 0.5,
            },
        )

        RateAudit.objects.create(
            organization=organization,
            project=project,
            rate=obj,
            old_rate=obj.base_rate,
            new_rate=rate_value,
            action="ai_generate",
            source="ai",
        )

        cache.set(
            f"org:{organization.id}:rate:{element}:{unit}",
            float(rate_value),
            86400,
        )

        return obj