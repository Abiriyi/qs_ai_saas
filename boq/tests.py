from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from django.conf import settings
from rest_framework.test import APIRequestFactory

from boq.api.views import BoQDetailView, BoQListView
from boq.services.generation_service import BoQGenerationService
from boq.services.workflow import BoQWorkflowService


class OpenAISettingsConfigurationTest(SimpleTestCase):
    def test_openai_settings_are_exposed_to_django(self):
        self.assertTrue(hasattr(settings, "OPENAI_API_KEY"))
        self.assertTrue(settings.OPENAI_API_KEY)
        self.assertEqual(settings.OPENAI_MODEL, "gpt-4.1")


class BoQGenerationServiceTest(SimpleTestCase):
    def test_generation_time_is_calculated_after_boq_persistence(self):
        project = Mock()
        project.id = "project-id"
        user = Mock()
        boq = Mock()
        validated_schema = Mock()
        validated_schema.model_dump.return_value = {"sections": []}
        validation_report = SimpleNamespace(
            valid=True,
            errors=[],
            warnings=[],
        )
        confidence_report = SimpleNamespace(overall_score=90.0)

        with (
            patch(
                "boq.services.generation_service.time.perf_counter",
                side_effect=[10.0, 12.5],
            ),
            patch(
                "boq.services.generation_service.BoQAIGenerator"
            ) as generator_class,
            patch(
                "boq.services.generation_service.PydanticValidator.validate",
                return_value=validated_schema,
            ),
            patch(
                "boq.services.generation_service.BusinessValidator.validate",
                return_value=validation_report,
            ),
            patch(
                "boq.services.generation_service.ConfidenceService.assess",
                return_value=confidence_report,
            ),
            patch(
                "boq.services.generation_service.build_boq_from_engine",
                return_value=boq,
            ) as build_boq,
        ):
            generator_class.return_value.generate.return_value = {
                "sections": []
            }

            result = BoQGenerationService.generate(
                text="source text",
                project=project,
                user=user,
            )

        self.assertEqual(result.processing_time, 2.5)
        self.assertEqual(boq.generation_time, 2.5)
        boq.save.assert_called_once_with(
            update_fields=["generation_time", "updated_at"]
        )
        self.assertIsNone(
            build_boq.call_args.kwargs["generation_time"]
        )

    def test_finish_safely_submits_generation_for_review(self):
        project = Mock()
        project.id = "project-id"
        user = Mock()
        boq = Mock()
        boq.status = "draft"
        result = SimpleNamespace(
            boq=boq,
            validation_report=SimpleNamespace(valid=False, errors=["bad"], warnings=[]),
            confidence_report=SimpleNamespace(overall_score=55.0),
        )

        with (
            patch.object(
                BoQGenerationService,
                "generate",
                return_value=result,
            ) as generate_mock,
            patch(
                "boq.services.generation_service.BoQWorkflowService.submit_for_review",
                return_value=boq,
            ) as submit_review_mock,
        ):
            safe_result = BoQGenerationService.finish_safely(
                text="source text",
                project=project,
                user=user,
            )

        self.assertEqual(safe_result["status"], "review_pending")
        self.assertFalse(safe_result["auto_approved"])
        generate_mock.assert_called_once_with(
            text="source text",
            project=project,
            user=user,
        )
        submit_review_mock.assert_called_once_with(boq)


class BoQWorkflowServiceReviewTest(SimpleTestCase):
    def test_approve_sets_review_and_approval_metadata(self):
        user = Mock()
        boq = Mock()
        boq.status = "review_pending"
        boq.reviewed_by = None
        boq.reviewed_at = None
        boq.approved_by = None
        boq.approved_at = None
        now = "2026-01-01T00:00:00Z"

        with patch("boq.services.workflow.timezone.now", return_value=now):
            result = BoQWorkflowService.approve(boq, user)

        self.assertEqual(result.reviewed_by, user)
        self.assertEqual(result.reviewed_at, now)
        self.assertEqual(result.approved_by, user)
        self.assertEqual(result.approved_at, now)
        boq.save.assert_called_once_with(
            update_fields=[
                "status",
                "reviewed_by",
                "reviewed_at",
                "approved_by",
                "approved_at",
                "updated_at",
            ]
        )


class BoQAPITest(SimpleTestCase):
    def test_create_view_creates_boq(self):
        project_id = "123e4567-e89b-12d3-a456-426614174000"
        project = Mock(id=project_id, name="Project Alpha")
        created_boq = Mock()
        created_boq.id = "123e4567-e89b-12d3-a456-426614174001"
        created_boq.name = "Sample BoQ"
        created_boq.status = "draft"
        created_boq.total_amount = 1000
        created_boq.project = project
        created_boq.sections = []
        created_boq.reviewed_by = None
        created_boq.approved_by = None

        request = APIRequestFactory().post(
            "/api/boq/",
            {"project_id": project_id, "name": "Sample BoQ", "total_amount": "1000"},
        )
        request.user = Mock(organization_id="org-123", organization=Mock(id="org-123"))

        with patch("boq.api.views.get_object_or_404", return_value=project), patch(
            "boq.api.views.BoQ.objects.create", return_value=created_boq
        ) as create_mock:
            response = BoQListView.as_view()(request)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["id"], str(created_boq.id))
        create_mock.assert_called_once()

    def test_update_view_updates_boq(self):
        boq = Mock()
        boq.id = "123e4567-e89b-12d3-a456-426614174001"
        boq.name = "Old Name"
        boq.status = "draft"
        boq.total_amount = 1000
        boq.project_id = "123e4567-e89b-12d3-a456-426614174000"
        boq.project = Mock(id="123e4567-e89b-12d3-a456-426614174000", name="Project Alpha")
        boq.sections = []
        boq.reviewed_by = None
        boq.approved_by = None
        boq.save = Mock()

        request = APIRequestFactory().patch(
            "/api/boq/123e4567-e89b-12d3-a456-426614174001/",
            {"name": "New Name", "total_amount": "2500"},
        )
        request.user = Mock(organization_id="org-123")

        queryset = Mock()
        queryset.get.return_value = boq

        with patch("boq.api.views.BoQ.objects.filter", return_value=queryset):
            response = BoQDetailView.as_view()(request, pk=str(boq.id))

        self.assertEqual(response.status_code, 200)
        boq.save.assert_called_once()
        self.assertEqual(boq.name, "New Name")

    def test_delete_view_soft_deletes_boq(self):
        boq = Mock()
        boq.id = "123e4567-e89b-12d3-a456-426614174001"
        boq.soft_delete = Mock()

        request = APIRequestFactory().delete("/api/boq/123e4567-e89b-12d3-a456-426614174001/")
        request.user = Mock(organization_id="org-123")

        queryset = Mock()
        queryset.get.return_value = boq

        with patch("boq.api.views.BoQ.objects.filter", return_value=queryset):
            response = BoQDetailView.as_view()(request, pk=str(boq.id))

        self.assertEqual(response.status_code, 204)
        boq.soft_delete.assert_called_once_with()

    def test_list_view_filters_by_organization_and_project(self):
        project_id = "123e4567-e89b-12d3-a456-426614174000"
        boq = Mock()
        boq.id = "123e4567-e89b-12d3-a456-426614174001"
        boq.name = "Sample BoQ"
        boq.status = "draft"
        boq.total_amount = 1000
        boq.ai_confidence_score = 0.8
        boq.ai_model = "gpt-4.1"
        boq.generation_time = 2.5
        boq.validation_summary = {}
        boq.reviewed_by = None
        boq.reviewed_at = None
        boq.approved_by = None
        boq.approved_at = None
        boq.rejection_reason = None
        boq.is_frozen = False
        boq.updated_at = "2026-01-01T00:00:00Z"
        boq.project_id = project_id
        boq.project = Mock(id=project_id, name="Project Alpha")
        boq.sections = []

        request = APIRequestFactory().get(f"/api/boq/?project_id={project_id}")
        request.user = Mock(organization_id="org-123")

        with patch("boq.api.views.BoQ.objects.filter", return_value=[boq]) as filter_mock:
            response = BoQListView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["id"], str(boq.id))
        filter_mock.assert_called_once()

    def test_detail_view_returns_single_boq(self):
        boq = Mock()
        boq.id = "123e4567-e89b-12d3-a456-426614174001"
        boq.name = "Sample BoQ"
        boq.status = "review_pending"
        boq.total_amount = 2000
        boq.ai_confidence_score = 0.9
        boq.ai_model = "gpt-4.1"
        boq.generation_time = 3.2
        boq.validation_summary = {}
        boq.reviewed_by = None
        boq.reviewed_at = None
        boq.approved_by = None
        boq.approved_at = None
        boq.rejection_reason = None
        boq.is_frozen = False
        boq.updated_at = "2026-01-01T00:00:00Z"
        boq.project_id = "123e4567-e89b-12d3-a456-426614174000"
        boq.project = Mock(id="123e4567-e89b-12d3-a456-426614174000", name="Project Alpha")
        boq.sections = []

        request = APIRequestFactory().get("/api/boq/123e4567-e89b-12d3-a456-426614174001/")
        request.user = Mock(organization_id="org-123")

        queryset = Mock()
        queryset.get.return_value = boq

        with patch("boq.api.views.BoQ.objects.filter", return_value=queryset):
            response = BoQDetailView.as_view()(request, pk=str(boq.id))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(boq.id))
