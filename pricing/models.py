from django.db import models
from core.models import BaseTenantModel
from boq.models import BoQItem
from projects.models import Project
from users.models import User


class RateLibrary(BaseTenantModel):

    element = models.CharField(max_length=255)

    unit = models.CharField(max_length=50)

    base_rate = models.DecimalField(
        max_digits=14,
        decimal_places=2
    )

    location = models.CharField(max_length=100)

    year = models.IntegerField()

    source = models.CharField(
        max_length=100,
        default="manual"
    )

    confidence_score = models.FloatField(default=1.0)

    is_active = models.BooleanField(default=True)

    version = models.IntegerField(default=1)

    def __str__(self):
        return f"{self.element} ({self.location})"

class RateAudit(BaseTenantModel):

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE
    )

    boq_item = models.ForeignKey(
        BoQItem,
        on_delete=models.CASCADE
    )

    rate_library = models.ForeignKey(
        RateLibrary,
        on_delete=models.SET_NULL,
        null=True
    )

    ai_generated = models.BooleanField(default=False)

    original_rate = models.DecimalField(
        max_digits=14,
        decimal_places=2
    )

    final_rate = models.DecimalField(
        max_digits=14,
        decimal_places=2
    )

    user_override = models.BooleanField(default=False)

    generated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True
    )

    notes = models.TextField(blank=True)