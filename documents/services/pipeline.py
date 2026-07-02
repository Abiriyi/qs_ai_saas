# documents/services/pipeline.py

from documents.enums import DocumentStatus

from boq.services.generation_service import (
    BoQGenerationService,
)


class DocumentProcessingPipeline:

    def process(self):

        text = extractor.extract(...)

        ai_data = generator.generate(text)

        validated = pydantic_validator.validate(ai_data)

        business_validator.validate(validated)

        confidence = confidence_service.calculate(validated)

        draft_boq = boq_builder.build(...)

        audit.log_generation(...)

        return draft_boq