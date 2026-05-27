from django.db import models


class DocumentStatus(models.TextChoices):

    PENDING = "pending", "Pending"

    PROCESSING = "processing", "Processing"

    EXTRACTING = "extracting", "Extracting"

    STRUCTURING = "structuring", "Structuring"

    PRICING = "pricing", "Pricing"

    REVIEW_PENDING = (
        "review_pending",
        "Review Pending",
    )

    COMPLETED = "completed", "Completed"

    FAILED = "failed", "Failed"