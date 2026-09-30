from unittest.mock import patch
from inspect import signature

from django.core.files.storage import default_storage
from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from documents.models import UploadedDocument
from documents.tasks import process_document_task
from projects.models import Project
from users.models import Organization, User


@override_settings(
    STORAGES={
        "default": {
            "BACKEND": "django.core.files.storage.InMemoryStorage",
        },
        "staticfiles": {
            "BACKEND": (
                "django.contrib.staticfiles.storage.StaticFilesStorage"
            ),
        },
    }
)
class DocumentUploadAPITest(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Upload test organization",
            type="firm",
        )
        self.user = User.objects.create_user(
            email="upload-test@example.com",
            organization=self.organization,
            password="test-password",
        )
        self.project = Project.objects.create(
            organization=self.organization,
            created_by=self.user,
            name="Upload test project",
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def pdf_upload(self, name="plan.pdf", content=b"%PDF-1.4\n%EOF\n"):
        return SimpleUploadedFile(
            name,
            content,
            content_type="application/pdf",
        )

    def test_upload_requires_authentication(self):
        client = APIClient()

        response = client.post(
            "/api/documents/upload/",
            {
                "project_id": str(self.project.id),
                "file": self.pdf_upload(),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 403)

    @patch("documents.api.views.process_document_task.delay")
    def test_upload_saves_file_and_queues_tenant_task(self, delay_task):
        response = self.client.post(
            "/api/documents/upload/",
            {
                "project_id": str(self.project.id),
                "file": self.pdf_upload(),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 202)
        document = UploadedDocument.objects.get(
            id=response.data["document_id"]
        )
        self.assertTrue(default_storage.exists(document.file.name))
        delay_task.assert_called_once_with(
            str(document.id),
            org_id=str(self.organization.id),
        )

    @patch("documents.api.views.process_document_task.delay")
    def test_upload_rejects_project_from_another_organization(
        self,
        delay_task,
    ):
        other_organization = Organization.objects.create(
            name="Other organization",
            type="firm",
        )
        other_user = User.objects.create_user(
            email="other-upload-test@example.com",
            organization=other_organization,
            password="test-password",
        )
        other_project = Project.objects.create(
            organization=other_organization,
            created_by=other_user,
            name="Other project",
        )

        response = self.client.post(
            "/api/documents/upload/",
            {
                "project_id": str(other_project.id),
                "file": self.pdf_upload(),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 404)
        delay_task.assert_not_called()

    @patch("documents.api.views.process_document_task.delay")
    def test_upload_rejects_non_pdf(self, delay_task):
        response = self.client.post(
            "/api/documents/upload/",
            {
                "project_id": str(self.project.id),
                "file": self.pdf_upload(
                    name="notes.txt",
                    content=b"plain text",
                ),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)
        delay_task.assert_not_called()

    @override_settings(DOCUMENT_MAX_UPLOAD_SIZE=8)
    @patch("documents.api.views.process_document_task.delay")
    def test_upload_rejects_oversized_file(self, delay_task):
        response = self.client.post(
            "/api/documents/upload/",
            {
                "project_id": str(self.project.id),
                "file": self.pdf_upload(
                    content=b"%PDF-1.4\ncontent too large\n"
                ),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 413)
        delay_task.assert_not_called()

    def test_placeholder_get_is_removed(self):
        response = self.client.get("/api/documents/upload/")

        self.assertEqual(response.status_code, 405)

    def test_celery_task_accepts_tenant_org_id(self):
        signature(process_document_task.run).bind(
            "document-id",
            org_id=str(self.organization.id),
        )