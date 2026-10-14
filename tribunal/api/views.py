# tribunal/api/views.py
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.drf import TenantAPIViewMixin
from projects.models import Project
from tribunal.api.serializers import (
    TribunalCaseSerializer,
    TribunalDecisionSerializer,
)
from tribunal.models import TribunalCase
from tribunal.services import TribunalError, TribunalService


class TribunalCaseListCreateView(TenantAPIViewMixin, APIView):
    """List tribunal cases or raise a new dispute for a project/BoQ."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = TribunalCase.objects.filter(
            organization_id=request.user.organization_id
        ).select_related("project", "boq", "raised_by", "decided_by")

        project_id = request.query_params.get("project_id")
        if project_id:
            queryset = queryset.filter(project_id=project_id)

        return Response(TribunalCaseSerializer(queryset, many=True).data)

    def post(self, request):
        project_id = request.data.get("project_id")
        title = (request.data.get("title") or "").strip()
        if not project_id or not title:
            return Response(
                {"error": "project_id and title are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        project = get_object_or_404(
            Project.objects.filter(
                organization_id=request.user.organization_id
            ),
            id=project_id,
        )

        boq = None
        boq_id = request.data.get("boq_id")
        if boq_id:
            from boq.models import BoQ

            boq = get_object_or_404(
                BoQ.objects.filter(
                    organization_id=request.user.organization_id,
                    project=project,
                ),
                id=boq_id,
            )

        try:
            case = TribunalService.open_case(
                project=project,
                raised_by=request.user,
                title=title,
                description=request.data.get("description", ""),
                boq=boq,
            )
        except Exception as exc:  # pragma: no cover - defensive
            return Response(
                {"error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            TribunalCaseSerializer(case).data,
            status=status.HTTP_201_CREATED,
        )


class TribunalCaseDetailView(TenantAPIViewMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        case = get_object_or_404(
            TribunalCase.objects.filter(
                organization_id=request.user.organization_id
            ),
            id=pk,
        )
        return Response(TribunalCaseSerializer(case).data)


class TribunalCaseDecisionView(TenantAPIViewMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        case = get_object_or_404(
            TribunalCase.objects.filter(
                organization_id=request.user.organization_id
            ),
            id=pk,
        )

        serializer = TribunalDecisionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            case = TribunalService.decide(
                case=case,
                decision=serializer.validated_data["decision"],
                decided_by=request.user,
                notes=serializer.validated_data.get("notes", ""),
            )
        except TribunalError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(TribunalCaseSerializer(case).data)
