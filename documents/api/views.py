# documents/api/views.py
from pathlib import Path
from uuid import UUID

from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated

from documents.models import UploadedDocument
from documents.tasks import process_document_task
from django.shortcuts import get_object_or_404
from projects.models import Project
from core.drf import TenantAPIViewMixin


class DocumentUploadView(TenantAPIViewMixin, APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [
        MultiPartParser,
        FormParser,
    ]

    def post(self, request):
        uploaded_file = request.FILES.get("file")
        if not uploaded_file:
            return Response(
                {"error": "file is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        max_upload_size = getattr(
            settings,
            "DOCUMENT_MAX_UPLOAD_SIZE",
            25 * 1024 * 1024,
        )
        if uploaded_file.size > max_upload_size:
            return Response(
                {"error": "file exceeds the maximum allowed size"},
                status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            )

        if Path(uploaded_file.name).suffix.lower() != ".pdf":
            return Response(
                {"error": "only PDF files are allowed"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if b"%PDF-" not in uploaded_file.read(1024):
            return Response(
                {"error": "uploaded file is not a valid PDF"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        uploaded_file.seek(0)

        project_id = request.data.get("project_id")
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
            Project.objects.filter(
                organization_id=request.user.organization_id,
            ),
            id=project_id,
        )

        doc = UploadedDocument.objects.create(
            organization=project.organization,
            project=project,
            original_filename=uploaded_file.name,
            file=uploaded_file,
        )

        process_document_task.delay(
            str(doc.id),
            org_id=str(doc.organization_id),
        )

        return Response(
            {
                "document_id": str(doc.id),
                "status": "uploaded",
            },
            status=status.HTTP_202_ACCEPTED,
        )    