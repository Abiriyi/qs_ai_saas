# tribunal/services.py
import logging

from django.db import transaction
from django.utils import timezone

from audit.services import AuditService
from tribunal.models import (
    TribunalCase,
    TribunalCaseStatus,
    TribunalDecision,
)

logger = logging.getLogger(__name__)


class TribunalError(Exception):
    """Raised when an invalid tribunal workflow transition is attempted."""


class TribunalService:
    """
    Encapsulates the dispute-adjudication lifecycle.

    Opening a case freezes the disputed project and BoQ; issuing a ruling
    records the decision and, for non-``upheld`` outcomes, releases the freeze.
    Every transition is written to the central audit trail.
    """

    # -- creation -------------------------------------------------------------

    @staticmethod
    @transaction.atomic
    def open_case(*, project, raised_by, title, description="", boq=None):
        case = TribunalCase.objects.create(
            organization=project.organization,
            project=project,
            boq=boq,
            title=title,
            description=description,
            raised_by=raised_by,
            status=TribunalCaseStatus.OPEN,
            reference=TribunalService._next_reference(project.organization),
        )

        TribunalService._freeze(case, freeze=True)
        AuditService.tribunal(
            "case_opened",
            case=case,
            actor=raised_by,
            message=f"Tribunal case opened for project {project.name}.",
            payload={
                "project_id": str(project.id),
                "boq_id": str(boq.id) if boq is not None else None,
            },
        )
        return case

    # -- transitions ----------------------------------------------------------

    @staticmethod
    @transaction.atomic
    def assign(case, user):
        if not case.is_active:
            raise TribunalError("Only open cases can be assigned.")
        case.assigned_to = user
        case.status = TribunalCaseStatus.UNDER_REVIEW
        case.save(update_fields=["assigned_to", "status", "updated_at"])
        AuditService.tribunal(
            "case_assigned",
            case=case,
            actor=user,
            message=f"Case assigned to {user.email}.",
        )
        return case

    @staticmethod
    @transaction.atomic
    def decide(*, case, decision, decided_by, notes=""):
        if not case.is_active:
            raise TribunalError("This case has already been decided.")

        if decision not in {choice[0] for choice in TribunalDecision.choices}:
            raise TribunalError(f"Unknown tribunal decision: {decision}")

        case.status = TribunalCaseStatus.DECIDED
        case.decision = decision
        case.decision_notes = notes
        case.decided_by = decided_by
        case.decided_at = timezone.now()
        case.save(
            update_fields=[
                "status",
                "decision",
                "decision_notes",
                "decided_by",
                "decided_at",
                "updated_at",
            ]
        )

        # An upheld ruling keeps the BoQ frozen as the final, authoritative
        # record. Any other outcome releases the freeze so work can continue.
        TribunalService._freeze(case, freeze=(decision == TribunalDecision.UPHELD))

        AuditService.tribunal(
            "case_decided",
            case=case,
            actor=decided_by,
            message=f"Case decided: {decision}.",
            payload={"decision": decision},
        )
        return case

    @staticmethod
    @transaction.atomic
    def withdraw(case, user, notes=""):
        if case.status == TribunalCaseStatus.DECIDED:
            raise TribunalError("Decided cases cannot be withdrawn.")
        case.status = TribunalCaseStatus.WITHDRAWN
        case.decision_notes = notes
        case.save(update_fields=["status", "decision_notes", "updated_at"])
        TribunalService._freeze(case, freeze=False)
        AuditService.tribunal(
            "case_withdrawn",
            case=case,
            actor=user,
            message="Case withdrawn.",
        )
        return case

    # -- helpers --------------------------------------------------------------

    @staticmethod
    def _freeze(case, *, freeze):
        project = case.project
        if project is not None and project.is_frozen != freeze:
            project.is_frozen = freeze
            project.save(update_fields=["is_frozen"])

        boq = case.boq
        if boq is not None and boq.is_frozen != freeze:
            boq.is_frozen = freeze
            boq.save(update_fields=["is_frozen"])

    @staticmethod
    def _next_reference(organization):
        count = TribunalCase._base_manager.filter(
            organization=organization
        ).count()
        return f"TRB-{count + 1:04d}"
