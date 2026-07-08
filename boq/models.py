import uuid
from django.db import models
from core.models import BaseTenantModel
from projects.models import Project
from django.conf import settings

class BoQStatus(models.TextChoices):

    DRAFT = (
        "draft",
        "Draft"
    )

    VALIDATING = (
        "validating",
        "Validating"
    )

    REVIEW_PENDING = (
        "review_pending",
        "Review Pending"
    )

    APPROVED = (
        "approved",
        "Approved"
    )

    REJECTED = (
        "rejected",
        "Rejected"
    )

    PRICED = (
        "priced",
        "Priced"
    )

    SEALED = (
        "sealed",
        "Sealed"
    )

class BoQ(BaseTenantModel):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="boqs"
    )

    name = models.CharField(
        max_length=255
    )

    status = models.CharField(
        max_length=30,
        choices=BoQStatus.choices,
        default=BoQStatus.DRAFT,
    )

    total_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0
    )

    # AI metadata

    ai_confidence_score = models.FloatField(
        default=0.0
    )

    ai_model = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )

    generation_time = models.FloatField(
        null=True,
        blank=True
    )

    validation_summary = models.JSONField(
        default=dict,
        blank=True
    )

    # QS review workflow

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_boqs",
    )

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    # Approval workflow

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_boqs",
    )

    approved_at = models.DateTimeField(
        null=True,
        blank=True,
    )


    rejection_reason = models.TextField(
        null=True,
        blank=True
    )


    is_frozen = models.BooleanField(
        default=False
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )


    class Meta:
        indexes = [
            models.Index(
                fields=["status"]
            ),
        ]


    def __str__(self):
        return self.name

class BoQItem(BaseTenantModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    section = models.ForeignKey("BoQSection", on_delete=models.CASCADE, related_name="items")

    item_no = models.CharField(max_length=50)

    description = models.TextField()

    unit = models.CharField(max_length=50)

    quantity = models.DecimalField(max_digits=12, decimal_places=3)

    rate = models.DecimalField(max_digits=12, decimal_places=2)

    amount = models.DecimalField(max_digits=15, decimal_places=2)

    confidence_score = models.FloatField(default=0.0)

    source_reference = models.TextField(null=True, blank=True)  # PDF trace

    created_at = models.DateTimeField(auto_now_add=True)

    is_ai_generated = models.BooleanField(default=True)

    last_edited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="edited_boq_items"
    )

    last_edited_at = models.DateTimeField(null=True, blank=True)
    
    def save(self, *args, **kwargs):
        if self.section.boq.is_frozen:
            raise ValueError("Cannot edit frozen BoQ")

        self.amount = self.quantity * self.rate
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.item_no} - {self.description[:50]}"

class BoQSection(BaseTenantModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    boq = models.ForeignKey("BoQ", on_delete=models.CASCADE, related_name="sections")

    name = models.CharField(max_length=255)  # e.g. "Substructure"

    order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.name
