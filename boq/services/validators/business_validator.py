import logging
from dataclasses import dataclass, field

from boq.services.validators.schemas import (
    BoQSchema,
)

from boq.constants.units import VALID_UNITS

logger = logging.getLogger(__name__)


@dataclass
class ValidationReport:
    """
    Result returned by the BusinessValidator.
    """

    valid: bool

    errors: list[str] = field(
        default_factory=list
    )

    warnings: list[str] = field(
        default_factory=list
    )


class BusinessValidator:
    """
    Applies Quantity Surveying business rules
    after Pydantic validation.

    Pydantic validates the JSON structure.

    This validator checks whether the BoQ
    makes sense from a QS perspective.
    """

    @classmethod
    def validate(
        cls,
        boq: BoQSchema,
    ) -> ValidationReport:

        report = ValidationReport(
            valid=True
        )

        item_numbers = set()

        for section in boq.sections:

            if not section.items:

                report.warnings.append(
                    f'Section "{section.name}" has no items.'
                )

            for item in section.items:

                # -------------------------
                # Duplicate Item Numbers
                # -------------------------

                if item.item_no in item_numbers:

                    report.errors.append(
                        f'Duplicate item number "{item.item_no}".'
                    )

                item_numbers.add(
                    item.item_no
                )

                # -------------------------
                # Empty Description
                # -------------------------

                if not item.description.strip():

                    report.errors.append(
                        f'Item "{item.item_no}" '
                        "has an empty description."
                    )

                # -------------------------
                # Quantity
                # -------------------------

                if item.quantity <= 0:

                    report.errors.append(
                        f'Item "{item.item_no}" '
                        "has zero or negative quantity."
                    )

                # -------------------------
                # Unit
                # -------------------------

                if item.unit not in VALID_UNITS:

                    report.warnings.append(
                        f'Item "{item.item_no}" '
                        f'uses uncommon unit "{item.unit}".'
                    )

                # -------------------------
                # Confidence
                # -------------------------

                if item.confidence < 0.60:

                    report.warnings.append(
                        f'Item "{item.item_no}" '
                        "has low AI confidence."
                    )

                # -------------------------
                # Missing Rate
                # -------------------------

                if item.rate < 0:

                    report.errors.append(
                        f'Item "{item.item_no}" '
                        "has negative rate."
                    )

        report.valid = (
            len(report.errors) == 0
        )

        logger.info(
            "Business validation completed "
            "(errors=%s warnings=%s)",
            len(report.errors),
            len(report.warnings),
        )

        return report