# audit/api/views.py
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.api.serializers import AuditEventSerializer
from audit.models import AuditEvent
from core.drf import TenantAPIViewMixin
from core.pagination import StandardResultsSetPagination


class AuditEventListView(TenantAPIViewMixin, APIView):
    """
    Read-only, tenant-scoped audit trail.

    Supports optional ``category``, ``action``, ``model_name`` and
    ``object_id`` filters, plus standard ``page`` / ``page_size`` pagination.
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

        queryset = queryset.select_related("actor")

        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        if page is not None:
            return paginator.get_paginated_response(
                AuditEventSerializer(page, many=True).data
            )

        return Response(AuditEventSerializer(queryset, many=True).data)
