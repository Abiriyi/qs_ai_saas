from pricing.models import RateLibrary

from pricing.services.confidence import (
    PricingConfidenceService
)


class PricingPipeline:

    def __init__(self, project):

        self.project = project

    def price_item(self, item):

        rate = self._get_org_rate(item)

        if rate:

            confidence = (
                PricingConfidenceService
                .calculate_confidence(
                    "org_library"
                )
            )

            return {
                "rate": rate.rate,
                "source": "org_library",
                "confidence": confidence,
            }

        ai_rate = self._generate_ai_rate(item)

        confidence = (
            PricingConfidenceService
            .calculate_confidence(
                "ai_generated",
                ai_similarity=0.60,
            )
        )

        return {
            "rate": ai_rate,
            "source": "ai_generated",
            "confidence": confidence,
        }

    def _get_org_rate(self, item):

        return (
            RateLibrary.objects.filter(
                organization=self.project.organization,
                description__icontains=item[
                    "description"
                ],
            )
            .order_by("-created_at")
            .first()
        )

    def _generate_ai_rate(self, item):

        return 15000