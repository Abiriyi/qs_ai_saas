from django.test import SimpleTestCase

from pricing.services.pricing_pipeline import PricingPipeline
from qs_ai_project.ai_pricing import get_rate_from_library


class PricingIntegrationTests(SimpleTestCase):
    def test_library_lookup_returns_rate(self):
        rate = get_rate_from_library("Blockwork", unit="m2", location="Kaduna")

        self.assertIsNotNone(rate)
        self.assertGreater(rate, 0)

    def test_pipeline_returns_rate_with_confidence(self):
        project = type("Project", (), {"organization": type("Org", (), {"id": "org-123"})()})()
        item = {
            "element": "Blockwork",
            "description": "Blockwork to external walls",
            "unit": "m2",
            "location": "Kaduna",
        }

        result = PricingPipeline(project).price_item(item)

        self.assertIn("rate", result)
        self.assertIn("source", result)
        self.assertIn("confidence", result)
        self.assertGreaterEqual(result["confidence"], 0)
