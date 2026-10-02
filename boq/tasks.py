import logging

from celery import shared_task

from boq.services.generation_service import BoQGenerationService
from core.tasks import TenantAwareTask
from projects.models import Project
from users.models import User

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    base=TenantAwareTask,
    autoretry_for=(Exception,),
    retry_backoff=60,
    max_retries=5,
)
def finish_ai_boq_task(
    self,
    *,
    text,
    project_id,
    user_id=None,
    org_id=None,
):
    """
    Generate a BoQ and route it to review without allowing unsafe auto-approval.
    """
    project = Project.objects.select_related("created_by", "organization").get(id=project_id)

    if user_id:
        user = User.objects.get(id=user_id)
    else:
        user = project.created_by

    result = BoQGenerationService.finish_safely(
        text=text,
        project=project,
        user=user,
    )

    logger.info(
        "Finish-safe BoQ task completed for project %s: %s",
        project_id,
        result,
    )

    return result
