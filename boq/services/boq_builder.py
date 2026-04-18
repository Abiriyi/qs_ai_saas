from boq.models import BoQ, BoQSection, BoQItem


def build_boq_from_engine(data, project, user):
    boq = BoQ.objects.create(
        project=project,
        name="Generated BoQ",
        status="generated",
        organization=project.organization,
    )

    for i, section_data in enumerate(data.get("sections", [])):
        section = BoQSection.objects.create(
            boq=boq,
            name=section_data["name"],
            order=i,
            organization=project.organization,
        )

        for item in section_data.get("items", []):
            BoQItem.objects.create(
                section=section,
                item_no=item["item_no"],
                description=item["description"],
                unit=item["unit"],
                quantity=item["quantity"],
                rate=item["rate"],
                confidence_score=item.get("confidence", 0),
                organization=project.organization,
            )

    return boq
