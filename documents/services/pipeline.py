# documents/services/pipeline.py

from documents.enums import DocumentStatus

from documents.services.pdf_extractor import (
    PDFExtractorService
)


from boq.services.boq_builder import (
    build_boq_from_engine
)

from pricing.services.pricing_pipeline import (
    PricingPipeline
)

from boq.services.ai_generator import (
            BoQAIGenerator
        )

class DocumentProcessingPipeline:

    def __init__(self, document):

        self.document = document

    def process(self):

        text = PDFExtractorService.extract_text(
            self.document.file
        )

        self.document.extracted_text = text
        self.document.save(update_fields=["extracted_text"])

        self.document.status = DocumentStatus.STRUCTURING
        self.document.save(update_fields=["status"])

        generator = BoQAIGenerator()

        structured_data = generator.generate(text)

        boq = build_boq_from_engine(
            data=structured_data,
            project=self.document.project,
        )

        self.document.status = DocumentStatus.PRICING
        self.document.save(update_fields=["status"])

        pricing_pipeline = PricingPipeline(
            project=self.document.project
        )

        for section in boq.sections.all():
            for item in section.items.all():

                pricing = pricing_pipeline.price_item(item)

                item.rate = pricing["rate"]

                item.save(update_fields=["rate"])

        self.document.status = DocumentStatus.REVIEW_PENDING
        self.document.save(update_fields=["status"])

        return boq