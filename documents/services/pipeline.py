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


class DocumentProcessingPipeline:

    def __init__(self, document):

        self.document = document

    def process(self):

        text = (
            PDFExtractorService.extract_text(
                self.document.file
            )
        )

        self.document.extracted_text = text

        self.document.save(
            update_fields=["extracted_text"]
        )

        self.document.save()

        self.document.status = (
            DocumentStatus.STRUCTURING
        )

        self.document.save()

        boq_items = build_boq_from_engine(
            extracted_text
        )

        self.document.status = (
            DocumentStatus.PRICING
        )

        self.document.save()

        pricing_pipeline = PricingPipeline(
            project=self.document.project
        )

        priced_items = []

        for item in boq_items:

            pricing_data = (
                pricing_pipeline.price_item(
                    item
                )
            )

            priced_items.append({
                **item,
                **pricing_data,
            })

        self.document.status = (
            DocumentStatus.REVIEW_PENDING
        )

        self.document.save()

        return priced_items