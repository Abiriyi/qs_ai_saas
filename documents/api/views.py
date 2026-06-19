# documents/api/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser
from documents.models import UploadedDocument
from documents.tasks import process_document_task
from django.shortcuts import get_object_or_404

class DocumentUploadView(APIView):
    parser_classes = [MultiPartParser]

    def post(self, request):

        file = request.FILES["file"]

        project_id = request.data.get("project_id")

        project = get_object_or_404(
            Project,
            id=project_id,
            organization=request.user.organization
        )

        doc = UploadedDocument.objects.create(
            organization=request.user.organization,
            project=project,
            original_filename=file.name,
            file=file,
        )

        process_document_task.delay(
            str(doc.id),
            org_id=str(doc.organization.id)
        )

        return Response({
            "document_id": str(doc.id),
            "status": "uploaded"
        })