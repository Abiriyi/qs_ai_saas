from django.core.cache import cache
from core.cache import tenant_cache_key

def get_dashboard_metrics():

    cache_key = tenant_cache_key(
        "dashboard_metrics"
    )

    cached = cache.get(cache_key)

    if cached:
        return cached

    metrics = {
        "projects": Project.objects.count(),
        "completed_boqs": BOQ.objects.count(),
    }

    cache.set(cache_key, metrics, timeout=300)

    return metrics