from core.tenant import get_current_org


def tenant_cache_key(key):

    org = get_current_org()

    if not org:
        return key

    return f"org:{org.id}:{key}"