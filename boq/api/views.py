from uuid import UUID

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from boq.models import BoQ
from boq.services.workflow import BoQWorkflowService
from boq.tasks import finish_ai_boq_task
from core.drf import TenantAPIViewMixin
from projects.models import Project


class FinishSafeBoQView(TenantAPIViewMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        text = request.data.get("text")
        project_id = request.data.get("project_id")

        if not text or not str(text).strip():
            return Response(
                {"error": "text is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not project_id:
            return Response(
                {"error": "project_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            project_id = UUID(str(project_id))
        except (TypeError, ValueError, AttributeError):
            return Response(
                {"error": "project_id must be a valid UUID"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        project = get_object_or_404(
            Project.objects.filter(organization_id=request.user.organization_id),
            id=project_id,
        )

        task = finish_ai_boq_task.delay(
            text=str(text),
            project_id=str(project.id),
            user_id=str(request.user.id),
            org_id=str(request.user.organization_id),
        )

        return Response(
            {
                "task_id": task.id,
                "status": "queued",
                "message": "AI BoQ generation has been queued for safe review",
                "project_id": str(project.id),
            },
            status=status.HTTP_202_ACCEPTED,
        )


class BoQReviewDecisionView(TenantAPIViewMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, boq_id):
        action = str(request.data.get("action", "")).lower()

        boq = get_object_or_404(
            BoQ.objects.filter(organization_id=request.user.organization_id),
            id=boq_id,
        )

        if action == "approve":
            boq = BoQWorkflowService.approve(boq, request.user)
            response_status = status.HTTP_200_OK
        elif action == "reject":
            reason = request.data.get("reason") or "Rejected by QS reviewer."
            boq = BoQWorkflowService.reject(boq, request.user, reason)
            response_status = status.HTTP_200_OK
        else:
            return Response(
                {"error": "action must be either 'approve' or 'reject'"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "boq_id": str(boq.id),
                "status": boq.status,
                "reviewed_by": str(request.user.id),
                "rejection_reason": boq.rejection_reason,
            },
            status=response_status,
        )
