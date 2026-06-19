# documents/api/serializers.py

from rest_framework import serializers
from documents.models import UploadedDocument

class UploadedDocumentSerializer(
    serializers.ModelSerializer
):
    class Meta:
        model = UploadedDocument

        fields = [
            "id",
            "original_filename",
            "file",
            "status",
            "uploaded_at",
        ]

        read_only_fields = [
            "id",
            "status",
            "uploaded_at",
        ]