from decimal import Decimal

from django.test import SimpleTestCase, TestCase

from boq.models import BoQ, BoQItem, BoQSection
from core.tenant import reset_current_org, set_current_org
from pricing.services.boq_pricing_service import BoQPricingService
from pricing.services.pricing_pipeline import PricingPipeline
from projects.models import Project
from qs_ai_project.ai_pricing import get_rate_from_library
from users.models import Organization, User


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


class BoQTotalAmountTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Pricing Org", type="firm")
        self.user = User.objects.create_user(
            email="pricer@example.com",
            organization=self.organization,
            password="strong-pass-123",
        )
        self.token = set_current_org(self.organization)
        self.project = Project.objects.create(
            organization=self.organization,
            created_by=self.user,
            name="Pricing project",
        )
        self.boq = BoQ.objects.create(
            organization=self.organization,
            project=self.project,
            name="Estimate",
            status="draft",
        )
        self.section = BoQSection.objects.create(
            organization=self.organization,
            boq=self.boq,
            name="Substructure",
            order=1,
        )

    def tearDown(self):
        reset_current_org(self.token)

    def test_recalculate_total_sums_item_amounts(self):
        BoQItem.objects.create(
            organization=self.organization,
            section=self.section,
            item_no="A1",
            description="Excavation",
            unit="m3",
            quantity=Decimal("10"),
            rate=Decimal("50"),
            amount=Decimal("500"),
        )
        BoQItem.objects.create(
            organization=self.organization,
            section=self.section,
            item_no="A2",
            description="Concrete",
            unit="m3",
            quantity=Decimal("4"),
            rate=Decimal("100"),
            amount=Decimal("400"),
        )

        total = BoQPricingService.recalculate_total(self.boq)
        self.boq.refresh_from_db()

        self.assertEqual(total, Decimal("900"))
        self.assertEqual(self.boq.total_amount, Decimal("900"))

    def test_price_boq_sets_total_and_audits(self):
        BoQItem.objects.create(
            organization=self.organization,
            section=self.section,
            item_no="B1",
            description="Blockwork",
            unit="m2",
            quantity=Decimal("20"),
            rate=Decimal("0"),
            amount=Decimal("0"),
        )

        summary = BoQPricingService.price_boq(self.boq, actor=self.user)
        self.boq.refresh_from_db()

        self.assertEqual(summary["items"], 1)
        # Blockwork has a real rate in the CSV library, so the total must be > 0.
        self.assertGreater(self.boq.total_amount, Decimal("0"))
        from audit.models import AuditEvent

        self.assertTrue(
            AuditEvent.objects.filter(action="boq_priced", category="pricing").exists()
        )

