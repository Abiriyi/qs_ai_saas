from django.db import models
from core.models import BaseTenantModel
from boq.models import BoQItem
from projects.models import Project
from users.models import User
from django.conf import settings
from django.utils import timezone


class RateLibrary(BaseTenantModel):

    SOURCE_CHOICES = [
        ("manual", "Manual"),
        ("csv", "CSV Import"),
        ("ai", "AI Generated"),
    ]

    project = models.ForeignKey(
        "projects.Project",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="rate_library",
    )

    element = models.CharField(max_length=255)

    unit = models.CharField(max_length=50)

    location = models.CharField(max_length=100)

    base_rate = models.DecimalField(
        max_digits=18,
        decimal_places=2,
    )

    source = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        default="manual",
    )

    confidence_score = models.FloatField(
        null=True,
        blank=True,
    )

    ai_model = models.CharField(
        max_length=100,
        null=True,
        blank=True,
    )

    is_verified = models.BooleanField(default=False)

    year = models.PositiveIntegerField(default=2026)

    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        indexes = [
            models.Index(
                fields=[
                    "organization",
                    "project",
                    "location",
                    "element",
                    "unit",
                ]
            )
        ]

    def soft_delete(self):
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at"])

    def __str__(self):
        return (
            f"{self.element} - {self.location} - {self.base_rate}"
        )


class RateAudit(models.Model):

    ACTION_CHOICES = [
        ("created", "Created"),
        ("updated", "Updated"),
        ("deleted", "Deleted"),
        ("ai_generated", "AI Generated"),
        ("verified", "Verified"),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    rate = models.ForeignKey(
        RateLibrary,
        on_delete=models.CASCADE,
        related_name="audits",
    )

    action = models.CharField(
        max_length=30,
        choices=ACTION_CHOICES,
    )

    previous_rate = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True,
    )

    new_rate = models.DecimalField(
        max_digits=18,
        decimal_places=2,
    )

    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.action} - {self.rate.element}"