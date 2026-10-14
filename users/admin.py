# users/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from users.models import Organization, User


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "type",
        "subscription_plan",
        "max_users",
        "max_projects",
        "is_active",
        "created_at",
    )
    list_filter = ("type", "subscription_plan", "is_active")
    search_fields = ("name",)
    readonly_fields = ("id", "created_at")


class UserInline(admin.TabularInline):
    model = User
    extra = 0
    fields = ("email", "role", "is_active", "is_staff")
    show_change_link = True


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ("email",)
    list_display = ("email", "organization", "role", "is_active", "is_staff")
    list_filter = ("role", "is_active", "is_staff", "is_superuser")
    search_fields = ("email", "organization__name")
    list_select_related = ("organization",)

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Organization", {"fields": ("organization", "role")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "created_at")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "organization", "role", "password1", "password2"),
        }),
    )
    readonly_fields = ("id", "created_at", "last_login")

