# core/tasks.py

from celery import Task
from django.core.exceptions import ValidationError

from core.tenant import (
    set_current_org,
    reset_current_org,
)

from users.models import Organization


class TenantTask(Task):

    abstract = True
    acks_late = True
    reject_on_worker_lost = True

    def __call__(self, *args, **kwargs):
        org_id = kwargs.pop("org_id", None)
        token = set_current_org(None)
        try:
            if org_id is not None:
                try:
                    org = Organization.objects.get(pk=org_id)
                except Organization.DoesNotExist as exc:
                    raise ValidationError(
                        f"Unknown organization id for tenant task: {org_id}"
                    ) from exc
                set_current_org(org)
            return self.run(*args, **kwargs)
        finally:
            reset_current_org(token)


class TenantAwareTask(Task):

    abstract = True
    acks_late = True
    reject_on_worker_lost = True
    autoretry_for = (Exception,)
    retry_backoff = True
    max_retries = 5

    def __call__(self, *args, **kwargs):
        org_id = kwargs.pop("org_id", None)
        token = set_current_org(None)
        try:
            if org_id is not None:
                try:
                    organization = Organization.objects.get(pk=org_id)
                except Organization.DoesNotExist as exc:
                    raise ValidationError(
                        f"Unknown organization id for tenant task: {org_id}"
                    ) from exc
                set_current_org(organization)
            return super().__call__(*args, **kwargs)
        finally:
            reset_current_org(token)