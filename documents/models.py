# documents/models.py

import uuid
from django.db import models
from core.models import BaseTenantModel
from documents.enums import DocumentStatus
from projects.models import Project


def project_upload_path(instance, filename):
    """Store each project's drawings in a dedicated folder.

    Files are placed under ``media/uploads/projects/<project_id>/<filename>``
    so every project has its own isolated directory.
    """
    project_id = instance.project_id if instance.project_id else "unassigned"
    return f"uploads/projects/{project_id}/{filename}"


class UploadedDocument(BaseTenantModel):

    DOCUMENT_TYPE_CHOICES = [
        ("drawing", "Drawing"),
        ("specification", "Specification"),
        ("other", "Other"),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    file = models.FileField(
        upload_to=project_upload_path
    )

    document_type = models.CharField(
        max_length=50,
        choices=DOCUMENT_TYPE_CHOICES,
        default="drawing",
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

    @property
    def badge_class(self):
        """Return the CSS badge class for the document's status."""
        return {
            "processed": "success",
            "review_pending": "success",
            "pending": "warning",
            "processing": "info",
            "failed": "danger",
        }.get(self.status, "info")

    class Meta:

        ordering = ["-uploaded_at"]