import uuid
from django.db import models
from users.middleware import get_current_org

# -----------------------
# Base Tenant Model
# -----------------------
class BaseTenantModel(models.Model):
    """
    Abstract base model that enforces organization ownership.
    All tenant-aware models MUST inherit this.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    organization = models.ForeignKey(
        "users.Organization",
        on_delete=models.CASCADE,
        related_name="%(class)s_set",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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


# -----------------------
# Tenant QuerySet
# -----------------------
class TenantQuerySet(models.QuerySet):
    def for_current_org(self):
        org = get_current_org()
        if org:
            return self.filter(organization=org)
        return self.none()


# -----------------------
# Tenant Manager
# -----------------------
class TenantManager(models.Manager):
    def get_queryset(self):
        org = get_current_org()
        if org:
            return super().get_queryset().filter(organization=org)
        return super().get_queryset().none()
