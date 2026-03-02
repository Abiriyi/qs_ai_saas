import uuid
from django.db import models


class Organization(models.Model):
    PLAN_CHOICES = [
        ("solo", "Solo"),
        ("team", "Team"),
        ("enterprise", "Enterprise"),
    ]

    TYPE_CHOICES = [
        ("individual", "Individual"),
        ("firm", "Firm"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    name = models.CharField(max_length=255)

    type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
    )

    subscription_plan = models.CharField(
        max_length=20,
        choices=PLAN_CHOICES,
        default="solo",
    )

    max_users = models.PositiveIntegerField(default=1)
    max_projects = models.PositiveIntegerField(default=5)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Enforce rule: individuals can only have 1 user
        if self.type == "individual":
            self.max_users = 1

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

