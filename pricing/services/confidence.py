class PricingConfidenceService:

    @staticmethod
    def calculate_confidence(
        rate_source,
        historical_match=False,
        ai_similarity=0.0,
    ):

        score = 0.0

        if rate_source == "project_override":
            score += 0.95

        elif rate_source == "org_library":
            score += 0.90

        elif rate_source == "historical":
            score += 0.75

        elif rate_source == "ai_generated":
            score += 0.50

        if historical_match:
            score += 0.10

        score += ai_similarity * 0.15

        return min(score, 1.0)