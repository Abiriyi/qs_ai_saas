# documents/services/pipeline.py

from documents.enums import DocumentStatus
from documents.services.pdf_extractor import PDFExtractorService

from boq.services.generation_service import (
    BoQGenerationService,
)
from boq.models import BoQ
from pricing.services.boq_pricing_service import BoQPricingService
from audit.services import AuditService


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
            AuditService.document(
                "extraction_failed",
                document=self.document,
                message=str(exc),
            )
            raise

        if not text or not text.strip():
            msg = "No readable text could be extracted from the uploaded PDF."
            self.document.status = DocumentStatus.FAILED
            self.document.processing_error = msg
            self.document.save(
                update_fields=["status", "processing_error", "updated_at"]
            )
            AuditService.document(
                "extraction_failed",
                document=self.document,
                message=msg,
            )
            raise ValueError(msg)

        AuditService.document(
            "extracted",
            document=self.document,
            message=f"Extracted {len(text)} characters from PDF.",
        )

        self.document.extracted_text = text
        self.document.status = DocumentStatus.STRUCTURING
        self.document.save(
            update_fields=["extracted_text", "status", "updated_at"]
        )

        # BoQ generation depends on the OpenAI API. If it is unavailable
        # (e.g. no credits), we still want the document to be marked as
        # processed so the extracted text is available and the user can
        # retry BoQ generation later via the "Generate BoQ from documents"
        # button on the project page.
        try:
            result = BoQGenerationService.finish_safely(
                text=text,
                project=self.document.project,
                user=self.document.project.created_by,
            )

            # Price the freshly generated BoQ through the org rate library / AI
            # fallback and refresh its denormalised total. Pricing is best-effort:
            # a pricing failure must never discard a successfully generated BoQ.
            boq_id = result.get("boq_id") if isinstance(result, dict) else None
            if boq_id:
                try:
                    boq = BoQ._base_manager.select_related("project").get(id=boq_id)
                    BoQPricingService.price_boq(
                        boq,
                        actor=self.document.project.created_by,
                    )
                    self.document.status = DocumentStatus.PRICING
                    self.document.save(update_fields=["status", "updated_at"])
                except Exception:
                    # Pricing is non-fatal; the draft BoQ is still awaiting review.
                    pass

            self.document.status = (
                DocumentStatus.REVIEW_PENDING
            )
            self.document.save(
                update_fields=["status", "updated_at"]
            )

            AuditService.document(
                "boq_generated",
                document=self.document,
                message="BoQ generated and routed to review.",
                payload=result if isinstance(result, dict) else {},
            )

        except Exception as exc:
            # BoQ generation failed (e.g. OpenAI API quota exhausted).
            # Mark document as processed so extracted text is preserved;
            # the user can retry BoQ generation later.
            self.document.status = DocumentStatus.PROCESSED
            self.document.processing_error = (
                f"BoQ generation failed: {exc}. "
                "Extracted text is available; retry BoQ generation from the project page."
            )
            self.document.save(
                update_fields=["status", "processing_error", "updated_at"]
            )
            AuditService.document(
                "boq_generation_failed",
                document=self.document,
                message=str(exc),
            )

        return None