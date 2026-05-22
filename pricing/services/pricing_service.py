from django.core.cache import cache
from core.cache import tenant_cache_key
from pricing.models import RateLibrary, RateAudit
from decimal import Decimal
from core.tenant import get_current_org

from qs_ai_project.ai_pricing import (
    get_rate_from_ai,
    get_rate_from_library,
)


class PricingService:

    CACHE_TIMEOUT = 86400

    @staticmethod
    def get_rate(
        *,
        element,
        unit,
        location,
        project=None,
        user=None,
        use_ai=True,
    ):

        org = get_current_org()

        if not org:
            raise ValueError("No tenant organization set")

        cache_key = tenant_cache_key(
            f"rate:{location}:{element}:{unit}"
        )

        cached = cache.get(cache_key)

        if cached is not None:
            return Decimal(str(cached))

        # -------------------------------------------------
        # 1. PROJECT OVERRIDE
        # -------------------------------------------------

        if project:
            project_rate = (
                RateLibrary.objects.filter(
                    organization=org,
                    project=project,
                    element__iexact=element,
                    unit__iexact=unit,
                    location__iexact=location,
                    deleted_at__isnull=True,
                )
                .order_by("-created_at")
                .first()
            )

            if project_rate:
                cache.set(
                    cache_key,
                    float(project_rate.base_rate),
                    timeout=PricingService.CACHE_TIMEOUT,
                )

                return project_rate.base_rate

        # -------------------------------------------------
        # 2. ORGANIZATION RATE
        # -------------------------------------------------

        org_rate = (
            RateLibrary.objects.filter(
                organization=org,
                project__isnull=True,
                element__iexact=element,
                unit__iexact=unit,
                location__iexact=location,
                deleted_at__isnull=True,
            )
            .order_by("-created_at")
            .first()
        )

        if org_rate:
            cache.set(
                cache_key,
                float(org_rate.base_rate),
                timeout=PricingService.CACHE_TIMEOUT,
            )

            return org_rate.base_rate

        # -------------------------------------------------
        # 3. CSV FALLBACK
        # -------------------------------------------------

        csv_rate = get_rate_from_library(
            element=element,
            unit=unit,
            location=location,
        )

        if csv_rate:

            rate = RateLibrary.objects.create(
                organization=org,
                project=project,
                element=element,
                unit=unit,
                location=location,
                base_rate=csv_rate,
                source="csv",
                is_verified=True,
            )

            RateAudit.objects.create(
                rate=rate,
                action="created",
                new_rate=csv_rate,
                performed_by=user,
                metadata={
                    "source": "csv_import"
                },
            )

            cache.set(
                cache_key,
                float(csv_rate),
                timeout=PricingService.CACHE_TIMEOUT,
            )

            return Decimal(str(csv_rate))

        # -------------------------------------------------
        # 4. AI FALLBACK
        # -------------------------------------------------

        if not use_ai:
            return None

        ai_rate = get_rate_from_ai(
            element=element,
            description=element,
            unit=unit,
            location=location,
        )

        if ai_rate is None:
            return None

        rate = RateLibrary.objects.create(
            organization=org,
            project=project,
            element=element,
            unit=unit,
            location=location,
            base_rate=ai_rate,
            source="ai",
            confidence_score=0.75,
            ai_model="gpt-4.1",
            is_verified=False,
        )

        RateAudit.objects.create(
            rate=rate,
            action="ai_generated",
            new_rate=ai_rate,
            performed_by=user,
            metadata={
                "ai_model": "gpt-4.1",
                "location": location,
            },
        )

        cache.set(
            cache_key,
            float(ai_rate),
            timeout=PricingService.CACHE_TIMEOUT,
        )

        return Decimal(str(ai_rate))
