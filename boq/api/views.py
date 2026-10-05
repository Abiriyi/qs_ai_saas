from decimal import Decimal, InvalidOperation
from uuid import UUID

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from boq.api.serializers import BoQItemSerializer, BoQSectionSerializer, BoQSerializer
from boq.models import BoQ, BoQItem, BoQSection, BoQStatus
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


def get_tenant_instance(model_cls, request, **kwargs):
    queryset = get_tenant_queryset(model_cls, request)
    if hasattr(queryset, "get") and callable(getattr(queryset, "get")):
        try:
            return queryset.get(**kwargs)
        except Exception:
            return None

    try:
        items = list(queryset)
    except TypeError:
        items = []

    for item in items:
        if all(str(getattr(item, key, "")) == str(value) for key, value in kwargs.items()):
            return item
    return None


def filter_tenant_instances(model_cls, request, **kwargs):
    queryset = get_tenant_queryset(model_cls, request)
    if hasattr(queryset, "filter") and callable(getattr(queryset, "filter")):
        if queryset.__class__.__module__.startswith("django.db.models"):
            return queryset.filter(**kwargs)

    try:
        items = list(queryset)
    except TypeError:
        items = []

    return [
        item for item in items if all(str(getattr(item, key, "")) == str(value) for key, value in kwargs.items())
    ]


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


class BoQSectionListView(TenantAPIViewMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, boq_id):
        boq = get_tenant_instance(BoQ, request, id=boq_id)
        if boq is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        sections = filter_tenant_instances(BoQSection, request, boq_id=boq.id)
        return Response(BoQSectionSerializer(sections, many=True).data)

    def post(self, request, boq_id):
        boq = get_tenant_instance(BoQ, request, id=boq_id)
        if boq is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if getattr(boq, "is_frozen", False):
            return Response({"error": "Cannot edit frozen BoQ."}, status=status.HTTP_400_BAD_REQUEST)

        name = (request.data.get("name") or "").strip()
        if not name:
            return Response({"error": "name is required"}, status=status.HTTP_400_BAD_REQUEST)

        order = request.data.get("order", 0)
        try:
            order = int(order)
        except (TypeError, ValueError):
            return Response({"error": "order must be an integer"}, status=status.HTTP_400_BAD_REQUEST)

        section = BoQSection.objects.create(
            organization=request.user.organization,
            boq=boq,
            name=name,
            order=order,
        )
        return Response(BoQSectionSerializer(section).data, status=status.HTTP_201_CREATED)


class BoQSectionDetailView(TenantAPIViewMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, boq_id, section_id):
        boq = get_tenant_instance(BoQ, request, id=boq_id)
        if boq is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        section = get_tenant_instance(BoQSection, request, boq_id=boq.id, id=section_id)
        if section is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(BoQSectionSerializer(section).data)

    def patch(self, request, boq_id, section_id):
        boq = get_tenant_instance(BoQ, request, id=boq_id)
        if boq is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if getattr(boq, "is_frozen", False):
            return Response({"error": "Cannot edit frozen BoQ."}, status=status.HTTP_400_BAD_REQUEST)

        section = get_tenant_instance(BoQSection, request, boq_id=boq.id, id=section_id)
        if section is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if "name" in request.data:
            name = str(request.data.get("name") or "").strip()
            if not name:
                return Response({"error": "name is required"}, status=status.HTTP_400_BAD_REQUEST)
            section.name = name

        if "order" in request.data:
            try:
                section.order = int(request.data.get("order"))
            except (TypeError, ValueError):
                return Response({"error": "order must be an integer"}, status=status.HTTP_400_BAD_REQUEST)

        section.save()
        return Response(BoQSectionSerializer(section).data)

    def delete(self, request, boq_id, section_id):
        boq = get_tenant_instance(BoQ, request, id=boq_id)
        if boq is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if getattr(boq, "is_frozen", False):
            return Response({"error": "Cannot edit frozen BoQ."}, status=status.HTTP_400_BAD_REQUEST)

        section = get_tenant_instance(BoQSection, request, boq_id=boq.id, id=section_id)
        if section is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        section.soft_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class BoQItemListView(TenantAPIViewMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, boq_id, section_id):
        boq = get_tenant_instance(BoQ, request, id=boq_id)
        if boq is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        section = get_tenant_instance(BoQSection, request, boq_id=boq.id, id=section_id)
        if section is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        items = filter_tenant_instances(BoQItem, request, section_id=section.id)
        return Response(BoQItemSerializer(items, many=True).data)

    def post(self, request, boq_id, section_id):
        boq = get_tenant_instance(BoQ, request, id=boq_id)
        if boq is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if getattr(boq, "is_frozen", False):
            return Response({"error": "Cannot edit frozen BoQ."}, status=status.HTTP_400_BAD_REQUEST)

        section = get_tenant_instance(BoQSection, request, boq_id=boq.id, id=section_id)
        if section is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        required_fields = ["item_no", "description", "unit", "quantity", "rate"]
        for field in required_fields:
            if not request.data.get(field):
                return Response({"error": f"{field} is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            quantity = Decimal(str(request.data.get("quantity")))
            rate = Decimal(str(request.data.get("rate")))
        except InvalidOperation:
            return Response({"error": "quantity and rate must be numeric"}, status=status.HTTP_400_BAD_REQUEST)

        item = BoQItem.objects.create(
            organization=request.user.organization,
            section=section,
            item_no=str(request.data.get("item_no")).strip(),
            description=str(request.data.get("description")).strip(),
            unit=str(request.data.get("unit")).strip(),
            quantity=quantity,
            rate=rate,
            amount=quantity * rate,
            confidence_score=float(request.data.get("confidence_score", 0.0) or 0.0),
            source_reference=request.data.get("source_reference"),
            is_ai_generated=bool(request.data.get("is_ai_generated", True)),
        )
        return Response(BoQItemSerializer(item).data, status=status.HTTP_201_CREATED)


class BoQItemDetailView(TenantAPIViewMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, boq_id, section_id, item_id):
        boq = get_tenant_instance(BoQ, request, id=boq_id)
        if boq is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        section = get_tenant_instance(BoQSection, request, boq_id=boq.id, id=section_id)
        if section is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        item = get_tenant_instance(BoQItem, request, section_id=section.id, id=item_id)
        if item is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(BoQItemSerializer(item).data)

    def patch(self, request, boq_id, section_id, item_id):
        boq = get_tenant_instance(BoQ, request, id=boq_id)
        if boq is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if getattr(boq, "is_frozen", False):
            return Response({"error": "Cannot edit frozen BoQ."}, status=status.HTTP_400_BAD_REQUEST)

        section = get_tenant_instance(BoQSection, request, boq_id=boq.id, id=section_id)
        if section is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        item = get_tenant_instance(BoQItem, request, section_id=section.id, id=item_id)
        if item is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        for field in ["item_no", "description", "unit", "source_reference"]:
            if field in request.data:
                setattr(item, field, str(request.data.get(field)).strip())

        if "quantity" in request.data:
            try:
                item.quantity = Decimal(str(request.data.get("quantity")))
            except InvalidOperation:
                return Response({"error": "quantity must be numeric"}, status=status.HTTP_400_BAD_REQUEST)

        if "rate" in request.data:
            try:
                item.rate = Decimal(str(request.data.get("rate")))
            except InvalidOperation:
                return Response({"error": "rate must be numeric"}, status=status.HTTP_400_BAD_REQUEST)

        if "confidence_score" in request.data:
            try:
                item.confidence_score = float(request.data.get("confidence_score"))
            except (TypeError, ValueError):
                return Response({"error": "confidence_score must be numeric"}, status=status.HTTP_400_BAD_REQUEST)

        if hasattr(item, "amount"):
            try:
                quantity = Decimal(str(item.quantity))
                rate = Decimal(str(item.rate))
                item.amount = quantity * rate
            except (TypeError, ValueError, InvalidOperation):
                item.amount = 0

        item.save()
        return Response(BoQItemSerializer(item).data)

    def delete(self, request, boq_id, section_id, item_id):
        boq = get_tenant_instance(BoQ, request, id=boq_id)
        if boq is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if getattr(boq, "is_frozen", False):
            return Response({"error": "Cannot edit frozen BoQ."}, status=status.HTTP_400_BAD_REQUEST)

        section = get_tenant_instance(BoQSection, request, boq_id=boq.id, id=section_id)
        if section is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        item = get_tenant_instance(BoQItem, request, section_id=section.id, id=item_id)
        if item is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        item.soft_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


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
