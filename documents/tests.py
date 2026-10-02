from unittest.mock import patch
from inspect import signature

from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from core.tasks import TenantAwareTask
from core.tenant import get_current_org, reset_current_org, set_current_org
from documents.models import UploadedDocument
from documents.tasks import process_document_task
from projects.models import Project
from users.models import Organization, User


class DocumentLookupTask(TenantAwareTask):
    def run(self, document_id):
        return UploadedDocument.objects.get(id=document_id)


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
        token = set_current_org(self.organization)
        try:
            self.project = Project.objects.create(
                organization=self.organization,
                created_by=self.user,
                name="Upload test project",
            )
        finally:
            reset_current_org(token)
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
        document = UploadedDocument._base_manager.get(
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
        token = set_current_org(other_organization)
        try:
            other_project = Project.objects.create(
                organization=other_organization,
                created_by=other_user,
                name="Other project",
            )
        finally:
            reset_current_org(token)

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

    def test_task_without_org_id_fails_closed_and_clears_ambient_tenant(self):
        token = set_current_org(self.organization)
        try:
            document = UploadedDocument.objects.create(
                organization=self.organization,
                project=self.project,
                original_filename="plan.pdf",
            )
            with self.assertRaises(UploadedDocument.DoesNotExist):
                DocumentLookupTask()(str(document.id))
            self.assertEqual(get_current_org(), self.organization)
        finally:
            reset_current_org(token)

    def test_task_with_different_org_id_cannot_read_document(self):
        token = set_current_org(self.organization)
        try:
            document = UploadedDocument.objects.create(
                organization=self.organization,
                project=self.project,
                original_filename="plan.pdf",
            )
        finally:
            reset_current_org(token)
        other_organization = Organization.objects.create(
            name="Other task organization",
            type="firm",
        )

        with self.assertRaises(UploadedDocument.DoesNotExist):
            DocumentLookupTask()(
                str(document.id),
                org_id=str(other_organization.id),
            )

        self.assertIsNone(get_current_org())

    def test_task_with_invalid_org_id_fails_closed(self):
        token = set_current_org(self.organization)
        try:
            document = UploadedDocument.objects.create(
                organization=self.organization,
                project=self.project,
                original_filename="plan.pdf",
            )
            with self.assertRaises(ValidationError):
                DocumentLookupTask()(
                    str(document.id),
                    org_id="00000000-0000-0000-0000-000000000000",
                )
            self.assertEqual(get_current_org(), self.organization)
        finally:
            reset_current_org(token)

    def test_tenant_manager_returns_no_rows_without_context(self):
        token = set_current_org(self.organization)
        try:
            Project.objects.create(
                organization=self.organization,
                created_by=self.user,
                name="Scoped project",
            )
        finally:
            reset_current_org(token)

        self.assertFalse(Project.objects.all().exists())

    def test_save_requires_tenant_context(self):
        with self.assertRaises(ValidationError):
            Project.objects.create(
                organization=self.organization,
                created_by=self.user,
                name="Unscoped project",
            )

    def test_save_rejects_organization_from_another_tenant(self):
        other_organization = Organization.objects.create(
            name="Other write organization",
            type="firm",
        )
        other_user = User.objects.create_user(
            email="other-write-test@example.com",
            organization=other_organization,
            password="test-password",
        )
        token = set_current_org(self.organization)
        try:
            with self.assertRaises(ValidationError):
                Project.objects.create(
                    organization=other_organization,
                    created_by=other_user,
                    name="Cross-tenant project",
                )
        finally:
            reset_current_org(token)

    def test_save_rejects_related_object_from_another_tenant(self):
        other_organization = Organization.objects.create(
            name="Other related organization",
            type="firm",
        )
        other_user = User.objects.create_user(
            email="other-related-test@example.com",
            organization=other_organization,
            password="test-password",
        )
        other_token = set_current_org(other_organization)
        try:
            other_project = Project.objects.create(
                organization=other_organization,
                created_by=other_user,
                name="Other tenant project",
            )
        finally:
            reset_current_org(other_token)
        token = set_current_org(self.organization)
        try:
            with self.assertRaises(ValidationError):
                UploadedDocument.objects.create(
                    organization=self.organization,
                    project=other_project,
                    original_filename="cross-tenant.pdf",
                )
        finally:
            reset_current_org(token)

    def test_queryset_update_rejects_cross_tenant_assignment(self):
        other_organization = Organization.objects.create(
            name="Other update organization",
            type="firm",
        )
        token = set_current_org(self.organization)
        try:
            with self.assertRaises(ValidationError):
                Project.objects.filter(id=self.project.id).update(
                    organization=other_organization
                )
        finally:
            reset_current_org(token)

    def test_queryset_created_in_another_tenant_cannot_update_rows(self):
        token = set_current_org(self.organization)
        try:
            project_queryset = Project.objects.filter(id=self.project.id)
        finally:
            reset_current_org(token)

        other_organization = Organization.objects.create(
            name="Other queryset organization",
            type="firm",
        )
        token = set_current_org(other_organization)
        try:
            updated_count = project_queryset.update(
                organization=other_organization
            )
        finally:
            reset_current_org(token)

        self.assertEqual(updated_count, 0)
        project = Project._base_manager.get(id=self.project.id)
        self.assertEqual(project.organization_id, self.organization.id)

    def test_delete_rejects_record_from_another_tenant(self):
        other_organization = Organization.objects.create(
            name="Other delete organization",
            type="firm",
        )
        token = set_current_org(other_organization)
        try:
            with self.assertRaises(ValidationError):
                self.project.delete()
            deleted_count, _ = Project.objects.filter(
                id=self.project.id
            ).delete()
            self.assertEqual(deleted_count, 0)
        finally:
            reset_current_org(token)

    def test_bulk_create_requires_tenant_context(self):
        project = Project(
            organization=self.organization,
            created_by=self.user,
            name="Unscoped bulk project",
        )

        with self.assertRaises(ValidationError):
            Project.objects.bulk_create([project])