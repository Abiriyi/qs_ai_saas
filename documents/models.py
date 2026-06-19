# documents/models.py

import uuid
from django.db import models
from core.models import BaseTenantModel
from documents.enums import DocumentStatus
from projects.models import Project

class UploadedDocument(BaseTenantModel):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    file = models.FileField(
        upload_to="uploaded_documents/"
    )

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="documents",
        null=True,
        blank=True,
    )

    original_filename = models.CharField(
        max_length=255
    )

    extracted_text = models.TextField(
        blank=True,
        null=True,
    )

    status = models.CharField(
        max_length=50,
        choices=DocumentStatus.choices,
        default=DocumentStatus.PENDING,
    )

    processing_error = models.TextField(
        blank=True,
        null=True,
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:

        ordering = ["-uploaded_at"]