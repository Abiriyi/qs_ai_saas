# tribunal/admin.py
from django.contrib import admin

from tribunal.models import TribunalCase


@admin.register(TribunalCase)
class TribunalCaseAdmin(admin.ModelAdmin):
    list_display = (
        "reference",
        "title",
        "project",
        "status",
        "decision",
        "raised_by",
        "decided_at",
    )
    list_filter = ("status", "decision", "opened_at")
    search_fields = ("reference", "title", "description")
    readonly_fields = ("id", "opened_at", "decided_at", "updated_at")
    raw_id_fields = ("project", "boq", "raised_by", "assigned_to", "decided_by")

    def get_queryset(self, request):
        # Bypass the tenant manager so staff can administer across orgs in the
        # Django admin, which already enforces its own permissions.
        return self.model._base_manager.get_queryset()
