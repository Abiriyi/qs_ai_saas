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

        try:
            text = PDFExtractorService.extract_text(
                self.document.file
            )
        except Exception as exc:
            self.document.status = DocumentStatus.FAILED
            self.document.processing_error = str(exc)
            self.document.save(
                update_fields=["status", "processing_error", "updated_at"]
            )
            raise

        if not text or not text.strip():
            msg = "No readable text could be extracted from the uploaded PDF."
            self.document.status = DocumentStatus.FAILED
            self.document.processing_error = msg
            self.document.save(
                update_fields=["status", "processing_error", "updated_at"]
            )
            raise ValueError(msg)

        self.document.extracted_text = text
        self.document.status = DocumentStatus.STRUCTURING
        self.document.save(
            update_fields=["extracted_text", "status", "updated_at"]
        )

        result = BoQGenerationService.finish_safely(
            text=text,
            project=self.document.project,
            user=self.document.project.created_by,
        )

        self.document.status = (
            DocumentStatus.REVIEW_PENDING
        )
        self.document.save(
            update_fields=["status", "updated_at"]
        )

        return result