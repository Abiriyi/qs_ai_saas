# audit/services.py
import logging

from core.tenant import get_current_org

logger = logging.getLogger(__name__)


class AuditService:
    """
    Central, fail-safe writer for the audit trail.

    ``log`` never raises: auditing is a side-effect and must never break the
    primary business flow (BoQ generation, pricing, tribunal rulings, ...). If
    anything goes wrong while persisting the event it is logged and ``None`` is
    returned so callers can safely ignore the result.
    """

    @staticmethod
    def log(
        *,
        action,
        actor=None,
        organization=None,
        model_name="",
        object_id="",
        category="general",
        message="",
        payload=None,
        request=None,
    ):
        try:
            # Imported lazily so importing this module never triggers app-loading
            # ordering issues, and so callers can import it from anywhere.
            from audit.models import AuditEvent

            org = organization or get_current_org()
            if org is None and actor is not None:
                org = getattr(actor, "organization", None)

            ip_address = None
            if request is not None:
                ip_address = request.META.get("REMOTE_ADDR")

            event = AuditEvent.objects.create(
                organization=org if getattr(org, "pk", None) else None,
                actor=actor if getattr(actor, "pk", None) else None,
                action=str(action),
                category=str(category or "general"),
                model_name=str(model_name or ""),
                object_id=str(object_id or ""),
                message=str(message or ""),
                payload=payload or {},
                ip_address=ip_address,
            )
            return event
        except Exception:
            logger.exception("Failed to record audit event: %s", action)
            return None

    # -- convenience wrappers -------------------------------------------------

    @classmethod
    def boq(cls, action, *, boq=None, actor=None, **extra):
        return cls.log(
            action=action,
            actor=actor,
            organization=getattr(boq, "organization", None),
            model_name="BoQ",
            object_id=str(getattr(boq, "id", "") or ""),
            category="boq",
            **extra,
        )

    @classmethod
    def pricing(cls, action, *, boq=None, actor=None, **extra):
        return cls.log(
            action=action,
            actor=actor,
            organization=getattr(boq, "organization", None),
            model_name="BoQ",
            object_id=str(getattr(boq, "id", "") or ""),
            category="pricing",
            **extra,
        )

    @classmethod
    def tribunal(cls, action, *, case=None, actor=None, **extra):
        return cls.log(
            action=action,
            actor=actor,
            organization=getattr(case, "organization", None),
            model_name="TribunalCase",
            object_id=str(getattr(case, "id", "") or ""),
            category="tribunal",
            **extra,
        )

    @classmethod
    def document(cls, action, *, document=None, actor=None, **extra):
        return cls.log(
            action=action,
            actor=actor,
            organization=getattr(document, "organization", None),
            model_name="UploadedDocument",
            object_id=str(getattr(document, "id", "") or ""),
            category="document",
            **extra,
        )
