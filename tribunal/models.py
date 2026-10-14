# tribunal/models.py
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models import BaseTenantModel
from projects.models import Project


class TribunalCaseStatus(models.TextChoices):
    OPEN = "open", "Open"
    UNDER_REVIEW = "under_review", "Under review"
    DECIDED = "decided", "Decided"
    WITHDRAWN = "withdrawn", "Withdrawn"


class TribunalDecision(models.TextChoices):
    UPHELD = "upheld", "Original BoQ upheld"
    AMENDED = "amended", "BoQ amended"
    DISMISSED = "dismissed", "Claim dismissed"


class TribunalCase(BaseTenantModel):
    """
    A formal dispute raised against a project / its Bill of Quantities.

    While a case is ``open`` or ``under_review`` the linked project and BoQ are
    *frozen* (``is_frozen``) so no further edits can be made until the tribunal
    issues a ruling. A decision of ``upheld`` keeps the BoQ frozen as a final
    record, while ``amended`` / ``dismissed`` / ``withdrawn`` release the freeze
    so the QS team can continue working.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    reference = models.CharField(
        max_length=40,
        unique=True,
        blank=True,
        help_text="Human-readable case reference, e.g. TRB-0001.",
    )

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="tribunal_cases",
    )

    boq = models.ForeignKey(
        "boq.BoQ",
        on_delete=models.SET_NULL,
        related_name="tribunal_cases",
        null=True,
        blank=True,
    )

    title = models.CharField(max_length=255)

    description = models.TextField(blank=True)

    raised_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="raised_tribunal_cases",
    )

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tribunal_cases",
    )

    status = models.CharField(
        max_length=20,
        choices=TribunalCaseStatus.choices,
        default=TribunalCaseStatus.OPEN,
        db_index=True,
    )

    decision = models.CharField(
        max_length=20,
        choices=TribunalDecision.choices,
        blank=True,
    )

    decision_notes = models.TextField(blank=True)

    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="decided_tribunal_cases",
    )

    opened_at = models.DateTimeField(default=timezone.now)

    decided_at = models.DateTimeField(null=True, blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-opened_at"]
        indexes = [
            models.Index(fields=["organization", "status"]),
        ]

    def __str__(self):
        return f"{self.reference or self.id} - {self.title}"

    @property
    def is_active(self):
        return self.status in {
            TribunalCaseStatus.OPEN,
            TribunalCaseStatus.UNDER_REVIEW,
        }
