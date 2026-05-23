import uuid
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
        ("ai", "AI Generated"),
        ("imported", "Imported"),
    ]

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="rate_library"
    )

    element = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    unit = models.CharField(max_length=50)

    location = models.CharField(
        max_length=100,
        default="Kaduna"
    )

    base_rate = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True
    )

    confidence_score = models.FloatField(default=0.0)

    source = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        default="manual"
    )

    review_status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="draft"
    )

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_rates"
    )

    reviewed_at = models.DateTimeField(null=True, blank=True)

    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=["organization"]),
            models.Index(fields=["project"]),
            models.Index(fields=["element"]),
            models.Index(fields=["location"]),
        ]

    def __str__(self):
        return f"{self.element} - {self.base_rate}"

class RateAudit(models.Model):

    ACTION_CHOICES = [
        ("created", "Created"),
        ("updated", "Updated"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("ai_generate", "AI Generated"),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    organization = models.ForeignKey(
        "users.Organization",
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    rate = models.ForeignKey(
        RateLibrary,
        on_delete=models.CASCADE,
        related_name="audits"
    )

    old_rate = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True
    )

    new_rate = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,   # ✅ FIX
        blank=True
    )

    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES,
    )

    source = models.CharField(
        max_length=50,
        default="manual"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )