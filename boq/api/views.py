from decimal import Decimal, InvalidOperation
from uuid import UUID

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from boq.api.serializers import BoQSerializer
from boq.models import BoQ, BoQStatus
from boq.services.workflow import BoQWorkflowError, BoQWorkflowService
from boq.tasks import finish_ai_boq_task
from core.drf import TenantAPIViewMixin
from projects.models import Project


def get_tenant_queryset(model_cls, request):
    queryset = model_cls.objects.filter()
    org_id = getattr(request.user, "organization_id", None)
    if org_id is None:
        return queryset

    try:
        UUID(str(org_id))
    except (TypeError, ValueError, AttributeError):
        return queryset

    return queryset.filter(organization_id=org_id)


class BoQListView(TenantAPIViewMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = get_tenant_queryset(BoQ, request)

        is_django_queryset = (
            hasattr(queryset, "filter") and queryset.__class__.__module__.startswith("django.db.models")
        )

        if is_django_queryset:
            queryset = queryset.select_related("project", "reviewed_by", "approved_by")
            queryset = queryset.prefetch_related("sections__items")

        project_id = request.query_params.get("project_id")
        if is_django_queryset:
            if project_id:
                queryset = queryset.filter(project_id=project_id)
            if hasattr(queryset, "order_by"):
                queryset = queryset.order_by("-updated_at")
        elif project_id:
            queryset = [
                item for item in queryset if str(getattr(item, "project_id", "")) == str(project_id)
            ]

        serializer = BoQSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        project_id = request.data.get("project_id")
        name = request.data.get("name")

        if not project_id:
            return Response({"error": "project_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        if not name or not str(name).strip():
            return Response({"error": "name is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            project_id = UUID(str(project_id))
        except (TypeError, ValueError, AttributeError):
            return Response({"error": "project_id must be a valid UUID"}, status=status.HTTP_400_BAD_REQUEST)

        project = get_object_or_404(
            get_tenant_queryset(Project, request),
            id=project_id,
        )

        status_value = str(request.data.get("status", BoQStatus.DRAFT)).lower()
        if status_value not in {choice[0] for choice in BoQStatus.choices}:
            return Response({"error": "status is invalid"}, status=status.HTTP_400_BAD_REQUEST)

        total_amount_raw = request.data.get("total_amount", 0)
        try:
            total_amount = Decimal(str(total_amount_raw))
        except InvalidOperation:
            return Response({"error": "total_amount must be numeric"}, status=status.HTTP_400_BAD_REQUEST)

        boq = BoQ.objects.create(
            organization=request.user.organization,
            project=project,
            name=str(name).strip(),
            status=status_value,
            total_amount=total_amount,
            is_frozen=bool(request.data.get("is_frozen", False)),
        )

        return Response(BoQSerializer(boq).data, status=status.HTTP_201_CREATED)


class BoQDetailView(TenantAPIViewMixin, APIView):
    permission_classes = [IsAuthenticated]

    def _get_boq(self, request, pk):
        queryset = get_tenant_queryset(BoQ, request)

        is_django_queryset = (
            hasattr(queryset, "filter") and queryset.__class__.__module__.startswith("django.db.models")
        )

        if is_django_queryset:
            queryset = queryset.select_related("project", "reviewed_by", "approved_by")
            queryset = queryset.prefetch_related("sections__items")

        if hasattr(queryset, "get") and callable(getattr(queryset, "get")):
            try:
                return queryset.get(id=pk)
            except BoQ.DoesNotExist:
                return None

        boq = next((item for item in queryset if str(item.id) == str(pk)), None)
        return boq

    def get(self, request, pk):
        boq = self._get_boq(request, pk)
        if boq is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = BoQSerializer(boq)
        return Response(serializer.data)


    def patch(self, request, pk):
        boq = self._get_boq(request, pk)
        if boq is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if "project_id" in request.data:
            project_id = request.data.get("project_id")
            try:
                project_id = UUID(str(project_id))
            except (TypeError, ValueError, AttributeError):
                return Response({"error": "project_id must be a valid UUID"}, status=status.HTTP_400_BAD_REQUEST)
            project = get_object_or_404(
                get_tenant_queryset(Project, request),
                id=project_id,
            )
            boq.project = project

        if "name" in request.data:
            name = request.data.get("name")
            if not name or not str(name).strip():
                return Response({"error": "name is required"}, status=status.HTTP_400_BAD_REQUEST)
            boq.name = str(name).strip()

        if "status" in request.data:
            status_value = str(request.data.get("status")).lower()
            if status_value not in {choice[0] for choice in BoQStatus.choices}:
                return Response({"error": "status is invalid"}, status=status.HTTP_400_BAD_REQUEST)
            boq.status = status_value

        if "total_amount" in request.data:
            try:
                boq.total_amount = Decimal(str(request.data.get("total_amount")))
            except InvalidOperation:
                return Response({"error": "total_amount must be numeric"}, status=status.HTTP_400_BAD_REQUEST)

        if "is_frozen" in request.data:
            boq.is_frozen = bool(request.data.get("is_frozen"))

        boq.save()
        return Response(BoQSerializer(boq).data)

    def put(self, request, pk):
        return self.patch(request, pk)

    def delete(self, request, pk):
        boq = self._get_boq(request, pk)
        if boq is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        boq.soft_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


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
            get_tenant_queryset(Project, request),
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
            get_tenant_queryset(BoQ, request),
            id=boq_id,
        )

        try:
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
        except BoQWorkflowError as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "boq_id": str(boq.id),
                "status": boq.status,
                "reviewed_by": str(boq.reviewed_by.id) if boq.reviewed_by else None,
                "approved_by": str(boq.approved_by.id) if boq.approved_by else None,
                "rejection_reason": boq.rejection_reason,
            },
            status=response_status,
        )
