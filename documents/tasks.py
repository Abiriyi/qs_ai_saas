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