from django.core.cache import cache

from core.cache import tenant_cache_key
from pricing.models import RateLibrary


class PricingService:

    @staticmethod
    def get_rate(
        *,
        element,
        unit,
        location,
        project=None
    ):

        cache_key = tenant_cache_key(
            f"rate:{location}:{element}:{unit}"
        )

        cached = cache.get(cache_key)

        if cached is not None:
            return cached

        rate = (
            RateLibrary.objects.filter(
                element__iexact=element,
                unit__iexact=unit,
                location__iexact=location,
                is_active=True,
            )
            .first()
        )

        if not rate:
            return None

        cache.set(
            cache_key,
            float(rate.base_rate),
            timeout=86400
        )

        return float(rate.base_rate)