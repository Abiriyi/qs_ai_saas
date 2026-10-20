# pricing/services/boq_pricing_service.py
"""
Wires the pricing engine to persisted BoQ line items.

Historically the AI generator wrote a ``rate`` straight onto every
:class:`boq.models.BoQItem` and never revisited it, and ``BoQ.total_amount``
was left at its default of ``0`` so the pricing-review screen always showed
``£0.00``. This service closes both gaps:

* it re-prices every item through :class:`PricingPipeline` (org rate library →
  CSV rate library → AI fallback), and
* it recalculates ``BoQ.total_amount`` as the sum of item amounts.
"""

import logging
from decimal import Decimal

from audit.services import AuditService
from boq.models import BoQ, BoQItem, BoQSection
from pricing.services.pricing_pipeline import PricingPipeline

logger = logging.getLogger(__name__)


class BoQPricingService:
    """Applies org/AI pricing to a BoQ and keeps ``total_amount`` in sync."""

    @classmethod
    def recalculate_total(cls, boq: BoQ) -> Decimal:
        """
        Recompute ``boq.total_amount`` from the persisted item amounts.

        Uses a DB aggregate so it stays correct regardless of how many items
        were created or edited, and is safe to call repeatedly.
        """
        from django.db.models import Sum

        total = (
            BoQItem._base_manager.filter(
                section__boq=boq,
                deleted_at__isnull=True,
            )
            .aggregate(total=Sum("amount"))
            .get("total")
        )
        total = total or Decimal("0")

        boq.total_amount = total
        boq.save(update_fields=["total_amount", "updated_at"])
        return total

    @classmethod
    def price_boq(cls, boq: BoQ, *, actor=None) -> dict:
        """
        Price every item on ``boq`` through the pricing pipeline and refresh
        the BoQ total. Records a single audit event summarising the run.

        Returns a summary dict: ``{"total": str, "items": int,
        "sources": {...}}``.
        """
        pipeline = PricingPipeline(boq.project)

        sources: dict[str, int] = {}
        item_count = 0

        for section in BoQSection._base_manager.filter(
            boq=boq, deleted_at__isnull=True
        ).order_by("order"):
            for item in BoQItem._base_manager.filter(
                section=section, deleted_at__isnull=True
            ):
                element = item.description or ""
                result = pipeline.price_item(
                    {
                        "element": element,
                        "description": item.description,
                        "unit": item.unit,
                    }
                )

                rate = result.get("rate")
                source = result.get("source", "unknown")
                confidence = result.get("confidence")

                # An "unmatched" result returns rate=None and confidence=None,
                # so both fields below are skipped and the item's existing
                # generation-time rate/confidence are preserved. It is still
                # counted under sources["unmatched"] and surfaced as
                # needs_review so a QS knows which lines lack a library rate.
                update_fields = []
                if rate is not None:
                    item.rate = Decimal(str(rate))
                    update_fields.append("rate")
                if confidence is not None:
                    item.confidence_score = float(confidence)
                    update_fields.append("confidence_score")

                if update_fields:
                    # BoQItem.save() recomputes ``amount = quantity * rate``.
                    item.save(update_fields=update_fields + ["amount", "updated_at"])

                sources[source] = sources.get(source, 0) + 1
                item_count += 1

        total = cls.recalculate_total(boq)
        needs_review = sources.get("unmatched", 0)

        AuditService.pricing(
            "boq_priced",
            boq=boq,
            actor=actor,
            message=(
                f"Priced {item_count} item(s) across {len(sources)} rate source(s)"
                + (f"; {needs_review} need manual review." if needs_review else ".")
            ),
            payload={
                "total": str(total),
                "items": item_count,
                "sources": sources,
                "needs_review": needs_review,
            },
        )

        logger.info(
            "Priced BoQ %s: %d items, total=%s, sources=%s, needs_review=%d",
            boq.id,
            item_count,
            total,
            sources,
            needs_review,
        )

        return {
            "total": str(total),
            "items": item_count,
            "sources": sources,
            "needs_review": needs_review,
        }
