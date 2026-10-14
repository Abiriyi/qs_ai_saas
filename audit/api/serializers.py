# audit/api/serializers.py
from rest_framework import serializers

from audit.models import AuditEvent


class AuditEventSerializer(serializers.ModelSerializer):
    actor_email = serializers.SerializerMethodField()

    class Meta:
        model = AuditEvent
        fields = [
            "id",
            "action",
            "category",
            "model_name",
            "object_id",
            "message",
            "payload",
            "actor",
            "actor_email",
            "created_at",
        ]
        read_only_fields = fields

    def get_actor_email(self, obj):
        actor = getattr(obj, "actor", None)
        return getattr(actor, "email", None) if actor is not None else None
