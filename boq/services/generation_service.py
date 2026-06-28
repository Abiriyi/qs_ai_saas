# boq/services/generation_service.py

from documents.services.pdf_extractor import (
    PDFExtractorService,
)

from boq.services.ai_generator import (
    BoQAIGenerator,
)

from boq.services.boq_builder import (
    build_boq_from_engine,
)

from pricing.services.pricing_pipeline import (
    PricingPipeline,
)


class BoQGenerationService:

    def __init__(self, document):

        self.document = document
        self.project = document.project

    def generate(self):

        # -----------------------------
        # Extract PDF text
        # -----------------------------
        text = PDFExtractorService.extract_text(
            self.document.file
        )

        self.document.extracted_text = text

        self.document.save(
            update_fields=["extracted_text"]
        )

        # -----------------------------
        # AI Generation
        # -----------------------------
        generator = BoQAIGenerator()

        structured_data = generator.generate(
            text
        )

        # -----------------------------
        # Persist database objects
        # -----------------------------
        boq = build_boq_from_engine(
            data=structured_data,
            project=self.project,
        )

        # -----------------------------
        # Price BoQ
        # -----------------------------
        pricing_pipeline = PricingPipeline(
            project=self.project
        )

        for section in boq.sections.all():

            for item in section.items.all():

                pricing = pricing_pipeline.price_item(
                    item
                )

                item.rate = pricing["rate"]

                if "confidence" in pricing:
                    item.confidence_score = pricing[
                        "confidence"
                    ]

                item.save(
                    update_fields=[
                        "rate",
                        "confidence_score",
                    ]
                )

        return boq