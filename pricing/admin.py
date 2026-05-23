from django.contrib import admin

from pricing.models import (
    RateLibrary,
    RateAudit,
)


@admin.register(RateLibrary)
class RateLibraryAdmin(admin.ModelAdmin):

    list_display = (
        "element",
        "unit",
        "location",
        "base_rate",
        "source",
        "review_status",
        "organization",
        "project",
        "is_active",
    )

    list_filter = (
        "source",
        "review_status",
        "location",
        "is_active",
    )

    search_fields = (
        "element",
        "description",
        "location",
    )

    ordering = ("-created_at",)


@admin.register(RateAudit)
class RateAuditAdmin(admin.ModelAdmin):

    list_display = (
        "rate",
        "action",
        "new_rate",
        "source",
        "created_by",
        "created_at",
    )

    list_filter = (
        "action",
        "source",
    )

    search_fields = (
        "rate__element",
        "rate__unit",
    )

    ordering = ("-created_at",)