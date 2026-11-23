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
from core.throttling import DocumentUploadThrottle


class DocumentUploadView(TenantAPIViewMixin, APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [DocumentUploadThrottle]
    parser_classes = [
        MultiPartParser,
        FormParser,
    ]

    def post(self, request):
        uploaded_files = request.FILES.getlist("file")
        if not uploaded_files:
            return Response(
                {"error": "file is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        max_upload_size = getattr(
            settings,
            "DOCUMENT_MAX_UPLOAD_SIZE",
            25 * 1024 * 1024,
        )

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

        created_docs = []
        for uploaded_file in uploaded_files:
            if uploaded_file.size > max_upload_size:
                return Response(
                    {"error": f"file '{uploaded_file.name}' exceeds the maximum allowed size"},
                    status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                )

            if Path(uploaded_file.name).suffix.lower() != ".pdf":
                return Response(
                    {"error": f"only PDF files are allowed ({uploaded_file.name})"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if b"%PDF-" not in uploaded_file.read(1024):
                return Response(
                    {"error": f"uploaded file is not a valid PDF ({uploaded_file.name})"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            uploaded_file.seek(0)

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

            created_docs.append(str(doc.id))

        return Response(
            {
                "document_ids": created_docs,
                "status": "uploaded",
            },
            status=status.HTTP_202_ACCEPTED,
        )    