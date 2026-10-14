# tribunal/api/serializers.py
from rest_framework import serializers

from tribunal.models import TribunalCase, TribunalDecision


class TribunalCaseSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    raised_by_email = serializers.SerializerMethodField()
    decided_by_email = serializers.SerializerMethodField()

    class Meta:
        model = TribunalCase
        fields = [
            "id",
            "reference",
            "project",
            "project_name",
            "boq",
            "title",
            "description",
            "status",
            "decision",
            "decision_notes",
            "raised_by",
            "raised_by_email",
            "assigned_to",
            "decided_by",
            "decided_by_email",
            "opened_at",
            "decided_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "reference",
            "status",
            "decision",
            "decision_notes",
            "decided_by",
            "decided_at",
            "opened_at",
            "updated_at",
        ]

    def get_raised_by_email(self, obj):
        actor = getattr(obj, "raised_by", None)
        return getattr(actor, "email", None) if actor is not None else None

    def get_decided_by_email(self, obj):
        actor = getattr(obj, "decided_by", None)
        return getattr(actor, "email", None) if actor is not None else None


class TribunalDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=TribunalDecision.choices)
    notes = serializers.CharField(required=False, allow_blank=True)
