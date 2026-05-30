import logging

from pricing.models import RateLibrary
from pricing.services.confidence import (
    PricingConfidenceService
)

logger = logging.getLogger(__name__)


class PricingPipeline:

    def __init__(self, project):
        self.project = project

    def price_item(self, item):

        rate = self._get_org_rate(item)

        if rate:

            source = "org_library"
            rate_value = rate.rate

            confidence = (
                PricingConfidenceService
                .calculate_confidence(source)
            )

        else:

            source = "ai_generated"
            rate_value = self._generate_ai_rate(item)

            confidence = (
                PricingConfidenceService
                .calculate_confidence(
                    source,
                    ai_similarity=0.60,
                )
            )

        pricing_result = {
            "rate": rate_value,
            "source": source,
            "confidence": confidence,
        }

        logger.info(
            "pricing_completed",
            extra={
                "tenant_id": str(
                    self.project.organization.id
                ),
                "project_id": str(
                    self.project.id
                ),
                "item_description": item["description"],
                "source": source,
                "confidence": confidence,
            }
        )

        return pricing_result

    def _get_org_rate(self, item):

        return (
            RateLibrary.objects.filter(
                organization=self.project.organization,
                description__icontains=item["description"],
            )
            .order_by("-created_at")
            .first()
        )

    def _generate_ai_rate(self, item):

        return 15000

        