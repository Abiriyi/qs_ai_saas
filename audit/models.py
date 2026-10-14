# audit/models.py
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class AuditEventManager(models.Manager):
    """
    Read helper that scopes audit events to the active tenant.

    Unlike :class:`core.models.TenantManager`, this fails *open* for reads:
    audit history is append-only and must never silently hide rows from an
    authenticated operator inside their own workspace.
    """

    def for_current_org(self):
        from core.tenant import get_current_org

        org = get_current_org()
        queryset = self.get_queryset()
        if org is not None:
            return queryset.filter(organization=org)
        return queryset.none()


class AuditEvent(models.Model):
    """
    Immutable, append-only record of a meaningful action taken in the system.

    Every model in the project (BoQ workflow transitions, pricing decisions,
    tribunal rulings, document processing, ...) writes here so operators have a
    single, tenant-scoped audit trail rather than scattered per-model logs.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    organization = models.ForeignKey(
        "users.Organization",
        on_delete=models.CASCADE,
        related_name="audit_events",
        null=True,
        blank=True,
    )

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_events",
    )

    action = models.CharField(max_length=100)

    category = models.CharField(
        max_length=50,
        default="general",
        db_index=True,
    )

    model_name = models.CharField(max_length=100, blank=True)

    object_id = models.CharField(max_length=64, blank=True)

    message = models.TextField(blank=True)

    payload = models.JSONField(default=dict, blank=True)

    ip_address = models.GenericIPAddressField(null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    objects = AuditEventManager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "created_at"]),
            models.Index(fields=["category", "action"]),
        ]
        verbose_name = "Audit event"
        verbose_name_plural = "Audit events"

    def __str__(self):
        target = f"{self.model_name}:{self.object_id}" if self.model_name else "-"
        return f"{self.created_at:%Y-%m-%d %H:%M} {self.action} ({target})"