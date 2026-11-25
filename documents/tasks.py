# documents/tasks.py

import logging

from celery import shared_task
from django.db import transaction

from core.tasks import TenantAwareTask

from documents.models import UploadedDocument
from documents.enums import DocumentStatus

from documents.services.pipeline import (
    DocumentProcessingPipeline
)

logger = logging.getLogger(__name__)


@shared_task
def test_task():

    logger.info(
        "Document processing started"
    )

    return "success"


@shared_task(
    bind=True,
    base=TenantAwareTask,
    autoretry_for=(Exception,),
    retry_backoff=60,
    max_retries=5,
)
def process_document_task(
    self,
    document_id,
    org_id=None,
):
    document = None

    try:
        document = (
            UploadedDocument.objects.for_current_org()
            .select_related("organization", "project")
            .get(id=document_id)
        )

        with transaction.atomic():
            document.status = DocumentStatus.PROCESSING
            document.save(update_fields=["status", "updated_at"])

        pipeline = DocumentProcessingPipeline(document)
        pipeline.process()

        return {"status": "ok", "document_id": str(document.id)}

    except UploadedDocument.DoesNotExist:
        # Document was deleted (e.g., project removed) while the task was
        # queued. Nothing to process -- exit gracefully without retrying.
        logger.warning(
            "Document %s no longer exists; skipping processing.",
            document_id,
        )
        return {"status": "skipped", "reason": "document_not_found", "document_id": str(document_id)}

    except FileNotFoundError as exc:
        # The referenced PDF file does not exist in storage (e.g. S3 object
        # was deleted or upload never completed). Mark the document as failed
        # without retrying -- retrying will not resurrect a missing file.
        if document is not None:
            document.status = DocumentStatus.FAILED
            document.processing_error = f"File not found in storage: {exc}"
            document.save(
                update_fields=["status", "processing_error", "updated_at"]
            )
        logger.warning(
            "File not found in storage for document %s: %s",
            document_id,
            exc,
        )
        return {"status": "failed", "reason": "file_not_found", "document_id": str(document_id)}

    except Exception as exc:
        if document is not None:
            document.status = DocumentStatus.FAILED
            document.processing_error = str(exc)
            document.save(
                update_fields=["status", "processing_error", "updated_at"]
            )

        logger.exception(
            "Document processing failed for document %s",
            document_id,
        )
        raise