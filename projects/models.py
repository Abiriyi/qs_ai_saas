from django.db import models
from django.conf import settings
from core.models import BaseTenantModel, TenantManager

class Project(BaseTenantModel):
    objects = TenantManager()
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("archived", "Archived"),
    ]

    name = models.CharField(max_length=255)

    description = models.TextField(blank=True, null=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="projects",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="draft",
    )

    is_frozen = models.BooleanField(default=False)  # tribunal locking

    def __str__(self):
        return self.name
