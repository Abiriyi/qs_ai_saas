# documents/api/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser
from documents.models import UploadedDocument
from documents.tasks import process_document_task
from django.shortcuts import get_object_or_404
from projects.models import Project
from rest_framework.parsers import MultiPartParser, FormParser

import logging

logger = logging.getLogger(__name__)

class DocumentUploadView(APIView):
    parser_classes = [
        MultiPartParser,
        FormParser
    ]

    def post(self, request):

        logger.info(f"user = {request.user}")
        logger.info(f"authenticated = {request.user.is_authenticated}")

        file = request.FILES.get("file")

        logger.info(f"File received: {file}")

        if not file:
            return Response(
                {"error": "file is required"},
                status=400
            )

        project_id = request.data.get("project_id")

        if not project_id:
            return Response(
                {"error": "project_id is required"},
                status=400
            )

        project = get_object_or_404(
            Project,
            id=project_id
        )

        doc = UploadedDocument.objects.create(
            organization=project.organization,
            project=project,
            original_filename=file.name,
            file=file,
        )

        logger.info(f"Document upload initiated for document: {doc.id}")

        process_document_task.delay(
            str(doc.id),
            org_id=str(doc.organization.id)
        )

        logger.info(f"Document processing initiated for document: {doc.id}")

        return Response({
            "document_id": str(doc.id),
            "status": "uploaded"
        })

    def get(self, request):
        logger.info(f"user = {request.user}")
        logger.info(f"authenticated = {request.user.is_authenticated}")
        return Response(
            {
                "project_id":
                "183020d7-f8d2-4e41-8f08-a2650206daf9"
            }
        )    