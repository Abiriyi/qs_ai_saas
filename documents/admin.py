# documents/admin.py
from django.contrib import admin

from core.admin import TenantAdmin
from documents.models import UploadedDocument


@admin.register(UploadedDocument)
class UploadedDocumentAdmin(TenantAdmin):
    list_display = (
        "original_filename",
        "project",
        "status",
        "organization",
        "uploaded_at",
        "updated_at",
    )
    list_filter = ("status",)
    search_fields = ("original_filename", "project__name")
    list_select_related = ("organization", "project")
    readonly_fields = ("id", "uploaded_at", "updated_at")
