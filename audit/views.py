# audit/views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from audit.models import AuditEvent


@login_required(login_url="login")
def audit_trail(request):
    """
    Tenant-scoped, read-only audit trail page.

    Supports optional ``category`` and ``q`` (free-text action search) filters.
    """
    events = AuditEvent._base_manager.filter(
        organization=request.user.organization
    ).select_related("actor")

    category = request.GET.get("category")
    if category:
        events = events.filter(category=category)

    query = (request.GET.get("q") or "").strip()
    if query:
        events = events.filter(action__icontains=query)

    categories = (
        AuditEvent._base_manager.filter(organization=request.user.organization)
        .values_list("category", flat=True)
        .distinct()
        .order_by("category")
    )

    context = {
        "page_title": "Audit trail | QS AI",
        "events": events[:200],
        "active_category": category or "",
        "query": query,
        "categories": list(categories),
    }
    return render(request, "audit_trail.html", context)
