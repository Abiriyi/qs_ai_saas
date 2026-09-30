# core/tasks.py

from celery import Task

from core.tenant import (
    set_current_org,
    reset_current_org,
)

from users.models import Organization

class TenantTask(Task):

    abstract = True

    def __call__(self, *args, **kwargs):
        org_id = kwargs.pop("org_id", None)
        token = set_current_org(None)
        try:
            if org_id:
                org = Organization.objects.get(id=org_id)
                set_current_org(org)
            return self.run(*args, **kwargs)
        finally:
            reset_current_org(token)

class TenantAwareTask(Task):

    abstract = True

    def __call__(self, *args, **kwargs):
        org_id = kwargs.pop("org_id", None)
        token = set_current_org(None)
        try:
            if org_id:
                organization = Organization.objects.get(id=org_id)
                set_current_org(organization)
            return super().__call__(
                *args,
                **kwargs
            )
        finally:
            reset_current_org(token)