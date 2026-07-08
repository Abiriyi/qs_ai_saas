import logging

from django.utils import timezone

from boq.models import BoQ, BoQStatus


logger = logging.getLogger(__name__)


class BoQWorkflowError(Exception):
    """
    Raised when an invalid BoQ workflow transition occurs.
    """
    pass


class BoQWorkflowService:
    """
    Handles all BoQ lifecycle transitions.
    """

    @staticmethod
    def submit_for_review(boq: BoQ):

        if boq.status != BoQStatus.DRAFT:
            raise BoQWorkflowError(
                "Only draft BoQs can be submitted for review."
            )

        boq.status = BoQStatus.REVIEW_PENDING
        boq.reviewed_at = timezone.now()

        boq.save(
            update_fields=[
                "status",
                "reviewed_at",
                "updated_at",
            ]
        )

        logger.info(
            "BoQ %s submitted for review.",
            boq.id,
        )

        return boq


    @staticmethod
    def approve(
        boq: BoQ,
        user,
    ):

        if boq.status != BoQStatus.REVIEW_PENDING:
            raise BoQWorkflowError(
                "Only BoQs pending review can be approved."
            )


        boq.status = BoQStatus.APPROVED

        boq.approved_by = user

        boq.approved_at = timezone.now()

        boq.save(
            update_fields=[
                "status",
                "approved_by",
                "approved_at",
                "updated_at",
            ]
        )


        logger.info(
            "BoQ %s approved by %s.",
            boq.id,
            user,
        )

        return boq



    @staticmethod
    def reject(
        boq: BoQ,
        user,
        reason: str,
    ):

        if boq.status != BoQStatus.REVIEW_PENDING:
            raise BoQWorkflowError(
                "Only BoQs pending review can be rejected."
            )


        boq.status = BoQStatus.REJECTED

        boq.reviewed_by = user

        boq.reviewed_at = timezone.now()

        boq.rejection_reason = reason


        boq.save(
            update_fields=[
                "status",
                "reviewed_by",
                "reviewed_at",
                "rejection_reason",
                "updated_at",
            ]
        )


        logger.warning(
            "BoQ %s rejected by %s.",
            boq.id,
            user,
        )

        return boq



    @staticmethod
    def mark_priced(boq: BoQ):

        if boq.status != BoQStatus.APPROVED:
            raise BoQWorkflowError(
                "Only approved BoQs can be priced."
            )


        boq.status = BoQStatus.PRICED

        boq.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )


        logger.info(
            "BoQ %s marked as priced.",
            boq.id,
        )

        return boq



    @staticmethod
    def seal(boq: BoQ):

        if boq.status != BoQStatus.PRICED:
            raise BoQWorkflowError(
                "Only priced BoQs can be sealed."
            )


        boq.status = BoQStatus.SEALED

        boq.is_frozen = True


        boq.save(
            update_fields=[
                "status",
                "is_frozen",
                "updated_at",
            ]
        )


        logger.info(
            "BoQ %s sealed and frozen.",
            boq.id,
        )

        return boq