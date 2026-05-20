import uuid
from django.db import models
from core.tenant import get_current_org
from django.utils import timezone

class TenantManager(models.Manager):

    def get_queryset(self):

        qs = super().get_queryset().filter(
            deleted_at__isnull=True
        )

        org = get_current_org()

        if org:
            return qs.filter(organization=org)

        return qs
        
class BaseTenantModel(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    organization = models.ForeignKey(
        "users.Organization",
        on_delete=models.CASCADE,
    )

    deleted_at = models.DateTimeField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        """
        Automatically attach current organization if not set.
        """
        if not self.organization_id:
            org = get_current_org()

            if org:
                self.organization = org

        super().save(*args, **kwargs)

    def soft_delete(self):
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at"])   

# -----------------------
# Tenant QuerySet
# -----------------------
class TenantQuerySet(models.QuerySet):
    def for_current_org(self):
        org = get_current_org()
        if org:
            return self.filter(organization=org)
        return self.none()



