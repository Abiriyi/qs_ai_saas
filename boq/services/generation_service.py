# boq/services/generation_service.py
from django.conf import settings

import time

from dataclasses import dataclass

import logging

from boq.models import BoQ

from boq.services.ai_generator import (
    BoQAIGenerator,
)

from boq.services.boq_builder import (
    build_boq_from_engine,
)

from boq.services.validators.pydantic_validator import (
    PydanticValidator,
)

from boq.services.validators.business_validator import (
    BusinessValidator,
    ValidationReport,
)

from boq.services.confidence.confidence_service import (
    ConfidenceService,
    ConfidenceResult,
)

logger = logging.getLogger(__name__)

@dataclass
class GenerationResult:

    boq: BoQ

    raw_ai_json: dict

    validation_report: ValidationReport

    confidence_report: ConfidenceResult

    processing_time: float

    ai_model: str

    ai_tokens: int | None = None


class BoQGenerationService:

    """
    Responsible for the complete
    AI BoQ generation workflow.
    """

    @classmethod
    def generate(
        cls,
        *,
        text: str,
        project,
        user,
    ) -> GenerationResult:

        start = time.perf_counter()

        logger.info(
            "Starting AI BoQ generation "
            "for project %s",
            project.id,
        )

        #
        # STEP 1
        # AI Generation
        #

        generator = BoQAIGenerator()

        raw_json = generator.generate(text)

        logger.info(
            "AI generation completed successfully."
        )

        #
        # STEP 2
        # Pydantic validation
        #

        validated_schema = (
            PydanticValidator.validate(
                raw_json
            )
        )

        #
        # STEP 3
        # Business validation
        #

        validation_report = (
            BusinessValidator.validate(
                validated_schema
            )
        )

        logger.info(
            "Business validation completed (%d errors, %d warnings).",
            len(validation_report.errors),
            len(validation_report.warnings),
        )

        #
        # Log detailed validation messages
        #

        if validation_report.errors:
            logger.warning(
                "Validation errors: %s",
                validation_report.errors,
            )

        if validation_report.warnings:
            logger.info(
                "Validation warnings: %s",
                validation_report.warnings,
            )

        #
        # Continue processing even if there are business errors.
        # The QS will review these before approval.
        #

        if not validation_report.valid:
            logger.warning(
                "Draft BoQ contains business validation errors and requires QS review."
            )

        # STEP 4
        # Confidence Assessment
        #

        confidence_report = (
            ConfidenceService.assess(
                validated_schema,
                validation_report,
            )
        )

        logger.info(
            "Confidence %.2f%%",
            confidence_report.overall_score,
        )

        #
        # STEP 5
        # Persist Draft BoQ
        #

        boq = build_boq_from_engine(
            data=validated_schema.model_dump(),
            project=project,
            user=user,
        )

        processing_time = (
            time.perf_counter() - start
        )

        logger.info(
            "Draft BoQ %s generated in %.2f seconds",
            boq.id,
            processing_time,
        )

        return GenerationResult(
            boq=boq,
            raw_ai_json=raw_json,
            validation_report=validation_report,
            confidence_report=confidence_report,
            processing_time=processing_time,
            ai_model=settings.OPENAI_MODEL,
            ai_tokens=None,
        )

        