# audit/api/views.py
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.api.serializers import AuditEventSerializer
from audit.models import AuditEvent
from core.drf import TenantAPIViewMixin


class AuditEventListView(TenantAPIViewMixin, APIView):
    """
    Read-only, tenant-scoped audit trail.

    Supports optional ``category`` and ``action`` filters plus a ``limit``
    query parameter (default 100, max 500).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = AuditEvent._base_manager.filter(
            organization_id=request.user.organization_id
        )

        category = request.query_params.get("category")
        if category:
            queryset = queryset.filter(category=category)

        action = request.query_params.get("action")
        if action:
            queryset = queryset.filter(action=action)

        model_name = request.query_params.get("model_name")
        if model_name:
            queryset = queryset.filter(model_name=model_name)

        object_id = request.query_params.get("object_id")
        if object_id:
            queryset = queryset.filter(object_id=str(object_id))

        try:
            limit = int(request.query_params.get("limit", 100))
        except (TypeError, ValueError):
            limit = 100
        limit = max(1, min(limit, 500))

        events = queryset.select_related("actor")[:limit]
        return Response(AuditEventSerializer(events, many=True).data)
