from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser
from documents.models import UploadedDocument
from documents.tasks import process_document_task

class DocumentUploadView(APIView):
    parser_classes = [MultiPartParser]

    def post(self, request):
        file = request.FILES["file"]

        doc = UploadedDocument.objects.create(
            organization=request.user.organization,
            original_filename=file.name,
            file=file,   # 🔥 Django + Tigris handles upload
        )

        # 🔥 safe async trigger AFTER file is guaranteed uploaded
        process_document_task.delay(str(doc.id))

        return Response({
            "document_id": str(doc.id),
            "status": "uploaded"
        })