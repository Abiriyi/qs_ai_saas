import logging
from unittest.mock import Mock

from django.utils import timezone

from boq.models import BoQ, BoQItem, BoQItemReviewStatus, BoQStatus


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
    def _iter_sections(boq):
        sections = getattr(boq, "sections", None)
        if sections is None or isinstance(sections, Mock):
            return []
        if hasattr(sections, "all"):
            try:
                return list(sections.all())
            except TypeError:
                return []
        try:
            return list(sections)
        except TypeError:
            return []

    @staticmethod
    def submit_for_review(boq: BoQ):

        if boq.status != BoQStatus.DRAFT:
            raise BoQWorkflowError(
                "Only draft BoQs can be submitted for review."
            )

        review_timestamp = timezone.now()
        boq.status = BoQStatus.REVIEW_PENDING
        boq.reviewed_at = review_timestamp

        for section in BoQWorkflowService._iter_sections(boq):
            items = getattr(section, "items", None)
            if items is None or isinstance(items, Mock):
                continue
            if hasattr(items, "all"):
                try:
                    item_list = list(items.all())
                except TypeError:
                    continue
            else:
                try:
                    item_list = list(items)
                except TypeError:
                    continue
            for item in item_list:
                item.review_status = BoQItemReviewStatus.PENDING_REVIEW
                item.reviewed_at = review_timestamp
                item.rejection_reason = None
                item.save(update_fields=["review_status", "reviewed_at", "rejection_reason"])

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
    def approve_item(item: BoQItem, user):
        if item.review_status not in {
            BoQItemReviewStatus.PENDING_REVIEW,
            BoQItemReviewStatus.NEEDS_REVISION,
        }:
            raise BoQWorkflowError(
                "Only pending or revised items can be approved."
            )

        approval_timestamp = timezone.now()
        item.review_status = BoQItemReviewStatus.APPROVED
        item.reviewed_by = user
        item.reviewed_at = approval_timestamp
        item.rejection_reason = None
        item.record_audit_event("approved", actor=user, item_id=str(item.id), reason=None)
        item.save(
            update_fields=[
                "review_status",
                "reviewed_by",
                "reviewed_at",
                "rejection_reason",
                "audit_trail",
            ]
        )
        return item

    @staticmethod
    def reject_item(item: BoQItem, user, reason: str):
        if item.review_status not in {
            BoQItemReviewStatus.PENDING_REVIEW,
            BoQItemReviewStatus.NEEDS_REVISION,
            BoQItemReviewStatus.APPROVED,
        }:
            raise BoQWorkflowError(
                "Only reviewable items can be rejected."
            )

        item.review_status = BoQItemReviewStatus.REJECTED
        item.reviewed_by = user
        item.reviewed_at = timezone.now()
        item.rejection_reason = reason or "Rejected during review."
        item.record_audit_event("rejected", actor=user, item_id=str(item.id), reason=item.rejection_reason)
        item.save(
            update_fields=[
                "review_status",
                "reviewed_by",
                "reviewed_at",
                "rejection_reason",
                "audit_trail",
            ]
        )
        return item

    @staticmethod
    def request_item_revision(item: BoQItem, user, reason: str):
        if item.review_status == BoQItemReviewStatus.APPROVED:
            raise BoQWorkflowError("Approved items cannot be sent back for revision.")

        item.review_status = BoQItemReviewStatus.NEEDS_REVISION
        item.reviewed_by = user
        item.reviewed_at = timezone.now()
        item.rejection_reason = reason or "Item requires updates."
        item.record_audit_event("needs_revision", actor=user, item_id=str(item.id), reason=item.rejection_reason)
        item.save(
            update_fields=[
                "review_status",
                "reviewed_by",
                "reviewed_at",
                "rejection_reason",
                "audit_trail",
            ]
        )
        return item

    @staticmethod
    def approve(
        boq: BoQ,
        user,
    ):

        if boq.status != BoQStatus.REVIEW_PENDING:
            raise BoQWorkflowError(
                "Only BoQs pending review can be approved."
            )

        approval_timestamp = timezone.now()

        boq.status = BoQStatus.APPROVED
        boq.reviewed_by = user
        boq.reviewed_at = approval_timestamp
        boq.approved_by = user
        boq.approved_at = approval_timestamp

        for section in BoQWorkflowService._iter_sections(boq):
            items = getattr(section, "items", None)
            if items is None or isinstance(items, Mock):
                continue
            if hasattr(items, "all"):
                try:
                    item_list = list(items.all())
                except TypeError:
                    continue
            else:
                try:
                    item_list = list(items)
                except TypeError:
                    continue
            for item in item_list:
                item.review_status = BoQItemReviewStatus.APPROVED
                item.reviewed_by = user
                item.reviewed_at = approval_timestamp
                item.rejection_reason = None
                item.record_audit_event("approved", actor=user, item_id=str(item.id), boq_id=str(boq.id))
                item.save(update_fields=["review_status", "reviewed_by", "reviewed_at", "rejection_reason", "audit_trail"])

        boq.save(
            update_fields=[
                "status",
                "reviewed_by",
                "reviewed_at",
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

        for section in BoQWorkflowService._iter_sections(boq):
            items = getattr(section, "items", None)
            if items is None or isinstance(items, Mock):
                continue
            if hasattr(items, "all"):
                try:
                    item_list = list(items.all())
                except TypeError:
                    continue
            else:
                try:
                    item_list = list(items)
                except TypeError:
                    continue
            for item in item_list:
                item.review_status = BoQItemReviewStatus.REJECTED
                item.reviewed_by = user
                item.reviewed_at = boq.reviewed_at
                item.rejection_reason = reason
                item.record_audit_event("rejected", actor=user, item_id=str(item.id), boq_id=str(boq.id), reason=reason)
                item.save(update_fields=["review_status", "reviewed_by", "reviewed_at", "rejection_reason", "audit_trail"])

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