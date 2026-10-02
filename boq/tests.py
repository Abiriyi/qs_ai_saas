from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from django.conf import settings

from boq.services.generation_service import BoQGenerationService


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
