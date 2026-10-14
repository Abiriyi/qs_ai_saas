# boq/admin.py
from django.contrib import admin

from boq.models import BoQ, BoQItem, BoQSection
from core.admin import TenantAdmin


class BoQSectionInline(admin.TabularInline):
    model = BoQSection
    extra = 0
    fields = ("name", "order")


@admin.register(BoQ)
class BoQAdmin(TenantAdmin):
    list_display = (
        "name",
        "project",
        "status",
        "total_amount",
        "ai_confidence_score",
        "is_frozen",
        "updated_at",
    )
    list_filter = ("status", "is_frozen")
    search_fields = ("name", "project__name")
    list_select_related = ("project",)
    inlines = [BoQSectionInline]
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(BoQSection)
class BoQSectionAdmin(TenantAdmin):
    list_display = ("name", "boq", "order")
    list_filter = ("boq",)
    search_fields = ("name", "boq__name")
    list_select_related = ("boq",)


@admin.register(BoQItem)
class BoQItemAdmin(TenantAdmin):
    list_display = (
        "item_no",
        "description",
        "section",
        "unit",
        "quantity",
        "rate",
        "amount",
        "review_status",
    )
    list_filter = ("review_status", "unit", "is_ai_generated")
    search_fields = ("item_no", "description", "section__name")
    list_select_related = ("section",)

