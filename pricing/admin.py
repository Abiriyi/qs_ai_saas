from django.contrib import admin

from pricing.models import (
    RateLibrary,
    RateAudit,
)


@admin.register(RateLibrary)
class RateLibraryAdmin(admin.ModelAdmin):

    list_display = (
        "element",
        "location",
        "base_rate",
        "source",
        "is_verified",
        "organization",
    )

    search_fields = (
        "element",
        "location",
    )

    list_filter = (
        "source",
        "is_verified",
        "location",
    )


@admin.register(RateAudit)
class RateAuditAdmin(admin.ModelAdmin):

    list_display = (
        "rate",
        "action",
        "new_rate",
        "performed_by",
        "created_at",
    )