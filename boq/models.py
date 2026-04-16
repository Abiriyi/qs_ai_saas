import uuid
from django.db import models
from core.models import BaseTenantModel
from projects.models import Project
from django.conf import settings


class BoQ(BaseTenantModel):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("generated", "Generated"),
        ("finalized", "Finalized"),
        ("sealed", "Sealed"),  # tribunal-ready
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="boqs")

    name = models.CharField(max_length=255)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="draft",
    )

    total_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    is_frozen = models.BooleanField(default=False)  # tribunal lock

    created_at = models.DateTimeField(auto_now_add=True)

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
