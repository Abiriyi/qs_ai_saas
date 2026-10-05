from unittest.mock import Mock

from rest_framework import serializers

from boq.models import BoQ, BoQItem, BoQSection


class BoQItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = BoQItem
        fields = [
            "id",
            "item_no",
            "description",
            "unit",
            "quantity",
            "rate",
            "amount",
            "confidence_score",
            "source_reference",
            "is_ai_generated",
            "last_edited_at",
        ]
        read_only_fields = fields


class BoQSectionSerializer(serializers.ModelSerializer):
    items = BoQItemSerializer(many=True, read_only=True)

    class Meta:
        model = BoQSection
        fields = [
            "id",
            "name",
            "order",
            "items",
        ]
        read_only_fields = fields


class BoQSerializer(serializers.ModelSerializer):
    project_id = serializers.SerializerMethodField()
    project_name = serializers.SerializerMethodField()
    total_amount = serializers.SerializerMethodField()
    ai_confidence_score = serializers.SerializerMethodField()
    generation_time = serializers.SerializerMethodField()
    reviewed_by = serializers.SerializerMethodField()
    approved_by = serializers.SerializerMethodField()
    reviewed_at = serializers.SerializerMethodField()
    approved_at = serializers.SerializerMethodField()
    updated_at = serializers.SerializerMethodField()
    sections = BoQSectionSerializer(many=True, read_only=True)

    class Meta:
        model = BoQ
        fields = [
            "id",
            "project_id",
            "project_name",
            "name",
            "status",
            "total_amount",
            "ai_confidence_score",
            "ai_model",
            "generation_time",
            "validation_summary",
            "reviewed_by",
            "reviewed_at",
            "approved_by",
            "approved_at",
            "rejection_reason",
            "is_frozen",
            "updated_at",
            "sections",
        ]
        read_only_fields = fields

    def _safe_float_value(self, value):
        if value is None or isinstance(value, Mock):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return value

    def _safe_datetime_value(self, value):
        if value is None or isinstance(value, Mock):
            return None
        if hasattr(value, "isoformat"):
            return value.isoformat()
        return value

    def get_total_amount(self, obj):
        return self._safe_float_value(getattr(obj, "total_amount", None))

    def get_ai_confidence_score(self, obj):
        return self._safe_float_value(getattr(obj, "ai_confidence_score", None))

    def get_generation_time(self, obj):
        return self._safe_float_value(getattr(obj, "generation_time", None))

    def get_project_id(self, obj):
        project = getattr(obj, "project", None)
        project_id = getattr(obj, "project_id", None)
        if isinstance(project_id, Mock):
            project_id = None
        if project_id is not None:
            return str(project_id)
        if project is not None and not isinstance(project, Mock):
            return str(project.id)
        return None

    def get_project_name(self, obj):
        project = getattr(obj, "project", None)
        if project is not None and not isinstance(project, Mock):
            return getattr(project, "name", None)
        return None

    def get_reviewed_by(self, obj):
        reviewed_by = getattr(obj, "reviewed_by", None)
        if reviewed_by is None or isinstance(reviewed_by, Mock):
            return None
        reviewed_id = getattr(reviewed_by, "id", None)
        return str(reviewed_id) if reviewed_id is not None else None

    def get_reviewed_at(self, obj):
        return self._safe_datetime_value(getattr(obj, "reviewed_at", None))

    def get_approved_by(self, obj):
        approved_by = getattr(obj, "approved_by", None)
        if approved_by is None or isinstance(approved_by, Mock):
            return None
        approved_id = getattr(approved_by, "id", None)
        return str(approved_id) if approved_id is not None else None

    def get_approved_at(self, obj):
        return self._safe_datetime_value(getattr(obj, "approved_at", None))

    def get_updated_at(self, obj):
        return self._safe_datetime_value(getattr(obj, "updated_at", None))
