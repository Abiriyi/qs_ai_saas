# core/admin.py
from django.contrib import admin

from core.tenant import get_current_org, reset_current_org, set_current_org


class TenantAdmin(admin.ModelAdmin):
    """
    Base admin for tenant-scoped models.

    The default ``TenantManager`` returns an empty queryset unless a tenant is
    active in the request context, which is never the case in Django admin. To
    keep the admin usable we read through ``_base_manager`` and scope by the
    logged-in user's organization, falling back to showing everything for
    superusers without an organization (e.g. platform staff).
    """

    def get_queryset(self, request):
        qs = self.model._base_manager.get_queryset()
        org = getattr(request.user, "organization", None)
        if org is not None:
            return qs.filter(organization=org)
        return qs

    def save_model(self, request, obj, form, change):
        # Model writes require an active tenant context (BaseTenantModel.save
        # validates it), so set it around the save for the user's org.
        org = getattr(request.user, "organization", None)
        if not getattr(obj, "organization_id", None) and org is not None:
            obj.organization = org

        token = set_current_org(org)
        try:
            super().save_model(request, obj, form, change)
        finally:
            reset_current_org(token)

    def delete_model(self, request, obj):
        token = set_current_org(getattr(request.user, "organization", None))
        try:
            super().delete_model(request, obj)
        finally:
            reset_current_org(token)

    def delete_queryset(self, request, queryset):
        token = set_current_org(getattr(request.user, "organization", None))
        try:
            super().delete_queryset(request, queryset)
        finally:
            reset_current_org(token)
