from dataclasses import dataclass, field


@dataclass
class ConfidenceResult:
    """
    Overall confidence assessment for a generated BoQ.
    """

    overall_score: float

    ai_score: float

    business_score: float

    description_score: float

    quantity_score: float

    unit_score: float

    recommendations: list[str] = field(
        default_factory=list
    )