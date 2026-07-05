import logging

from boq.constants.units import VALID_UNITS
from boq.services.confidence.models import (
    ConfidenceResult,
)

logger = logging.getLogger(__name__)


class ConfidenceService:

    """
    Combines AI confidence with deterministic
    QS checks.

    Final confidence is NOT solely the AI score.
    """

    WEIGHTS = {

        "ai": 0.50,

        "business": 0.20,

        "description": 0.10,

        "quantity": 0.10,

        "unit": 0.10,
    }

    @classmethod
    def assess(
        cls,
        boq_schema,
        validation_report,
    ) -> ConfidenceResult:

        items = []

        for section in boq_schema.sections:
            items.extend(section.items)

        if not items:

            return ConfidenceResult(
                overall_score=0,
                ai_score=0,
                business_score=0,
                description_score=0,
                quantity_score=0,
                unit_score=0,
                recommendations=[
                    "No BoQ items generated."
                ],
            )

        # -------------------------
        # AI Confidence
        # -------------------------

        ai_score = (
            sum(
                item.confidence
                for item in items
            )
            / len(items)
        )

        ai_score *= 100

        # -------------------------
        # Business Validation
        # -------------------------

        if validation_report.valid:

            business_score = 100

        else:

            business_score = 0

        # -------------------------
        # Description Quality
        # -------------------------

        good_descriptions = sum(
            1
            for item in items
            if len(item.description.strip()) >= 10
        )

        description_score = (
            good_descriptions
            / len(items)
        ) * 100

        # -------------------------
        # Quantity Plausibility
        # -------------------------

        plausible_quantities = sum(
            1
            for item in items
            if item.quantity > 0
        )

        quantity_score = (
            plausible_quantities
            / len(items)
        ) * 100

        # -------------------------
        # Unit Quality
        # -------------------------

        valid_units = sum(
            1
            for item in items
            if item.unit in VALID_UNITS
        )

        unit_score = (
            valid_units
            / len(items)
        ) * 100

        # -------------------------
        # Overall Score
        # -------------------------

        overall = (

            ai_score
            * cls.WEIGHTS["ai"]

            +

            business_score
            * cls.WEIGHTS["business"]

            +

            description_score
            * cls.WEIGHTS["description"]

            +

            quantity_score
            * cls.WEIGHTS["quantity"]

            +

            unit_score
            * cls.WEIGHTS["unit"]

        )

        recommendations = []

        if overall >= 90:

            recommendations.append(
                "Excellent confidence."
            )

        elif overall >= 75:

            recommendations.append(
                "Suitable for QS review."
            )

        elif overall >= 60:

            recommendations.append(
                "Requires careful QS review."
            )

        else:

            recommendations.append(
                "Low confidence. Manual reconstruction recommended."
            )

        logger.info(
            "Confidence assessment complete: %.2f%%",
            overall,
        )

        return ConfidenceResult(

            overall_score=round(
                overall,
                2,
            ),

            ai_score=round(
                ai_score,
                2,
            ),

            business_score=round(
                business_score,
                2,
            ),

            description_score=round(
                description_score,
                2,
            ),

            quantity_score=round(
                quantity_score,
                2,
            ),

            unit_score=round(
                unit_score,
                2,
            ),

            recommendations=recommendations,
        )