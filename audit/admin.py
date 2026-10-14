# audit/admin.py
from django.contrib import admin

from audit.models import AuditEvent


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "action",
        "category",
        "model_name",
        "object_id",
        "actor",
        "organization",
    )
    list_filter = ("category", "action", "created_at")
    search_fields = ("action", "model_name", "object_id", "message")
    readonly_fields = (
        "id",
        "organization",
        "actor",
        "action",
        "category",
        "model_name",
        "object_id",
        "message",
        "payload",
        "ip_address",
        "created_at",
    )
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        # Audit rows are append-only; never expose soft-deletion semantics.
        return self.model._base_manager.get_queryset()
