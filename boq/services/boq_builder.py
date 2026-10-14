from decimal import Decimal

from boq.models import BoQ, BoQSection, BoQItem, BoQStatus


def build_boq_from_engine(
    data,
    project,
    user=None,
    confidence_score=0.0,
    ai_model=None,
    generation_time=None,
    validation_summary=None,
):
    normalized_validation_summary = validation_summary or {}

    if hasattr(validation_summary, "valid"):
        normalized_validation_summary = {
            "valid": validation_summary.valid,
            "errors": list(validation_summary.errors),
            "warnings": list(validation_summary.warnings),
        }

    boq = BoQ.objects.create(
        project=project,
        name="Generated BoQ",
        status=BoQStatus.DRAFT,
        organization=project.organization,
        ai_confidence_score=confidence_score,
        ai_model=ai_model,
        generation_time=generation_time,
        validation_summary=normalized_validation_summary,
    )

    total_amount = Decimal("0")

    for i, section_data in enumerate(data.get("sections", [])):
        section = BoQSection.objects.create(
            boq=boq,
            name=section_data["name"],
            order=i,
            organization=project.organization,
        )

        for item in section_data.get("items", []):
            boq_item = BoQItem.objects.create(
                section=section,
                item_no=item["item_no"],
                description=item["description"],
                unit=item["unit"],
                quantity=item["quantity"],
                rate=item["rate"],
                confidence_score=item.get("confidence", 0),
                organization=project.organization,
            )
            # BoQItem.save() has already computed ``amount = quantity * rate``.
            total_amount += boq_item.amount

    # Keep the denormalised BoQ total in sync with its line items so the
    # pricing-review screen shows the real value instead of the default 0.
    if boq.total_amount != total_amount:
        boq.total_amount = total_amount
        boq.save(update_fields=["total_amount", "updated_at"])

    return boq
