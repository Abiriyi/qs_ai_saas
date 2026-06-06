import logging

from celery import shared_task

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
    retry_backoff=True,
    max_retries=3,
)

def process_document_task(
    self,
    document_id,
):

    document = UploadedDocument.objects.get(
        id=document_id
    )

    try:

        document.status = (
            DocumentStatus.PROCESSING
        )

        document.save()

        pipeline = (
            DocumentProcessingPipeline(
                document
            )
        )

        pipeline.process()

        document.status = (
            DocumentStatus.COMPLETED
        )

        document.save()

    except Exception as exc:

        document.status = (
            DocumentStatus.FAILED
        )

        document.processing_error = str(exc)

        document.save()

        raise