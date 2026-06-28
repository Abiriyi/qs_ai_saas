# documents/services/pipeline.py

from documents.enums import DocumentStatus

from boq.services.generation_service import (
    BoQGenerationService,
)


class DocumentProcessingPipeline:

    def __init__(self, document):

        self.document = document

    def process(self):

        self.document.status = (
            DocumentStatus.STRUCTURING
        )

        self.document.save(
            update_fields=["status"]
        )

        generator = BoQGenerationService(
            self.document
        )

        boq = generator.generate()

        self.document.status = (
            DocumentStatus.REVIEW_PENDING
        )

        self.document.save(
            update_fields=["status"]
        )

        return boq