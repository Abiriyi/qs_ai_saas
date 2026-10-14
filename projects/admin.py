# projects/admin.py
from django.contrib import admin

from core.admin import TenantAdmin
from projects.models import Project


@admin.register(Project)
class ProjectAdmin(TenantAdmin):
    list_display = (
        "name",
        "organization",
        "status",
        "is_frozen",
        "created_by",
        "created_at",
        "updated_at",
    )
    list_filter = ("status", "is_frozen")
    search_fields = ("name", "description")
    list_select_related = ("organization", "created_by")
    readonly_fields = ("id", "created_at", "updated_at")

