# documents/services/pipeline.py

from documents.enums import DocumentStatus
from documents.services.pdf_extractor import PDFExtractorService

from boq.services.generation_service import (
    BoQGenerationService,
)


class DocumentProcessingPipeline:

    def __init__(self, document):
        self.document = document

    def process(self):

        #
        # Extract PDF
        #

        text = PDFExtractorService.extract_text(
            self.document.file
        )

        self.document.extracted_text = text
        self.document.status = DocumentStatus.STRUCTURING
        self.document.save()

        #
        # Generate Draft BoQ
        #

        result = BoQGenerationService.generate(
            text=text,
            project=self.document.project,
            user=self.document.project.created_by,
        )

        #
        # Update status
        #

        self.document.status = (
            DocumentStatus.REVIEW_PENDING
        )

        self.document.save()

        return result