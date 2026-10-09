from django.core.exceptions import ValidationError
from django.test import TestCase

from decimal import Decimal

from core.models import BaseTenantModel
from core.tenant import get_current_org, reset_current_org, set_current_org
from boq.models import BoQ, BoQItem, BoQSection
from projects.models import Project
from users.models import Organization, User


class TenantContextTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Tenant context org",
            type="firm",
        )

    def test_set_and_reset_current_org_round_trip(self):
        token = set_current_org(self.organization)

        self.assertIs(get_current_org(), self.organization)

        reset_current_org(token)
        self.assertIsNone(get_current_org())

    def test_queryset_requires_context_for_writes(self):
        user = User.objects.create_user(
            email="tenant-user@example.com",
            organization=self.organization,
            password="strong-pass-123",
        )
        token = set_current_org(self.organization)
        try:
            project = Project.objects.create(
                organization=self.organization,
                created_by=user,
                name="Context validated project",
            )
        finally:
            reset_current_org(token)

        reset_current_org(set_current_org(None))
        with self.assertRaises(ValidationError):
            Project.objects.filter(pk=project.pk).update(name="Changed without tenant")

    def test_base_tenant_model_rejects_cross_organization_write(self):
        other_org = Organization.objects.create(
            name="Other org",
            type="firm",
        )
        user = User.objects.create_user(
            email="owner@example.com",
            organization=self.organization,
            password="strong-pass-123",
        )
        token = set_current_org(self.organization)
        try:
            project = Project.objects.create(
                organization=self.organization,
                created_by=user,
                name="Original project",
            )
        finally:
            reset_current_org(token)

        token = set_current_org(other_org)
        try:
            project.organization = self.organization
            with self.assertRaises(ValidationError):
                project.save()
        finally:
            reset_current_org(token)


class TenantModelBehaviorTests(TestCase):
    def test_project_created_with_current_org_is_scoped_to_org(self):
        organization = Organization.objects.create(
            name="Scoped org",
            type="firm",
        )
        user = User.objects.create_user(
            email="scoped@example.com",
            organization=organization,
            password="strong-pass-123",
        )
        token = set_current_org(organization)
        try:
            project = Project.objects.create(
                organization=organization,
                created_by=user,
                name="Scoped project",
            )
        finally:
            reset_current_org(token)

        self.assertEqual(project.status, "draft")
        self.assertFalse(project.is_frozen)
        self.assertEqual(str(project), "Scoped project")

    def test_for_current_org_filters_queryset_to_active_tenant(self):
        org_one = Organization.objects.create(name="Org one", type="firm")
        org_two = Organization.objects.create(name="Org two", type="firm")
        user_one = User.objects.create_user(
            email="one@example.com",
            organization=org_one,
            password="strong-pass-123",
        )
        user_two = User.objects.create_user(
            email="two@example.com",
            organization=org_two,
            password="strong-pass-123",
        )

        token = set_current_org(org_one)
        try:
            project_one = Project.objects.create(
                organization=org_one,
                created_by=user_one,
                name="Org one project",
            )
        finally:
            reset_current_org(token)

        token = set_current_org(org_two)
        try:
            Project.objects.create(
                organization=org_two,
                created_by=user_two,
                name="Should not be visible",
            )
        finally:
            reset_current_org(token)

        token = set_current_org(org_one)
        try:
            queryset = Project.objects.for_current_org()
        finally:
            reset_current_org(token)

        ids = set(queryset.values_list("id", flat=True))
        self.assertEqual({project_one.id}, ids)


class HomePageTests(TestCase):
    def test_home_page_renders(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "QS AI")


class FrontendPageTests(TestCase):
    def test_auth_page_renders(self):
        response = self.client.get("/login/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Welcome back")

    def test_dashboard_requires_login(self):
        response = self.client.get("/dashboard/")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response["Location"])

    def test_dashboard_lists_only_current_organization_projects(self):
        organization = Organization.objects.create(name="Alpha QS", type="firm")
        other_org = Organization.objects.create(name="Beta QS", type="firm")
        user = User.objects.create_user(
            email="alpha@example.com",
            organization=organization,
            password="strong-pass-123",
        )
        other_user = User.objects.create_user(
            email="beta@example.com",
            organization=other_org,
            password="strong-pass-123",
        )

        token = set_current_org(organization)
        try:
            Project.objects.create(
                organization=organization,
                created_by=user,
                name="Alpha project one",
            )
        finally:
            reset_current_org(token)

        token = set_current_org(other_org)
        try:
            Project.objects.create(
                organization=other_org,
                created_by=other_user,
                name="Beta project one",
            )
        finally:
            reset_current_org(token)

        self.client.force_login(user)
        response = self.client.get("/dashboard/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Alpha project one")
        self.assertNotContains(response, "Beta project one")

    def test_project_workflow_requires_login(self):
        response = self.client.get("/projects/new/")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response["Location"])

    def test_project_workflow_page_renders_for_authenticated_user(self):
        organization = Organization.objects.create(name="Workflow QS", type="firm")
        user = User.objects.create_user(
            email="workflow@example.com",
            organization=organization,
            password="strong-pass-123",
        )

        self.client.force_login(user)
        response = self.client.get("/projects/new/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Project intake")

    def test_project_detail_requires_login(self):
        organization = Organization.objects.create(name="Detail QS", type="firm")
        user = User.objects.create_user(
            email="detail@example.com",
            organization=organization,
            password="strong-pass-123",
        )
        token = set_current_org(organization)
        try:
            project = Project.objects.create(
                organization=organization,
                created_by=user,
                name="Detail project",
            )
        finally:
            reset_current_org(token)

        response = self.client.get(f"/projects/{project.id}/")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response["Location"])

    def test_project_detail_renders_for_current_organization(self):
        organization = Organization.objects.create(name="Org detail", type="firm")
        other_org = Organization.objects.create(name="Other org", type="firm")
        user = User.objects.create_user(
            email="detail-user@example.com",
            organization=organization,
            password="strong-pass-123",
        )
        token = set_current_org(organization)
        try:
            project = Project.objects.create(
                organization=organization,
                created_by=user,
                name="Current project",
                description="Project summary",
            )
        finally:
            reset_current_org(token)

        other_token = set_current_org(other_org)
        try:
            other_project = Project.objects.create(
                organization=other_org,
                created_by=User.objects.create_user(
                    email="other-user@example.com",
                    organization=other_org,
                    password="strong-pass-123",
                ),
                name="Other project",
            )
        finally:
            reset_current_org(other_token)

        self.client.force_login(user)
        response = self.client.get(f"/projects/{project.id}/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Current project")
        self.assertContains(response, "Project summary")
        self.assertNotContains(response, "Other project")

    def test_pricing_review_requires_login(self):
        organization = Organization.objects.create(name="Pricing QS", type="firm")
        user = User.objects.create_user(
            email="pricing-user@example.com",
            organization=organization,
            password="strong-pass-123",
        )

        token = set_current_org(organization)
        try:
            project = Project.objects.create(
                organization=organization,
                created_by=user,
                name="Pricing review project",
            )
        finally:
            reset_current_org(token)

        response = self.client.get(f"/projects/{project.id}/pricing/")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response["Location"])

    def test_pricing_review_renders_for_current_organization(self):
        organization = Organization.objects.create(name="Pricing org", type="firm")
        user = User.objects.create_user(
            email="pricing-review@example.com",
            organization=organization,
            password="strong-pass-123",
        )

        token = set_current_org(organization)
        try:
            project = Project.objects.create(
                organization=organization,
                created_by=user,
                name="Estimate project",
            )
            boq = BoQ.objects.create(
                organization=organization,
                project=project,
                name="Main estimate",
                status="draft",
                total_amount=Decimal("15420.50"),
                ai_confidence_score=0.94,
            )
            section = BoQSection.objects.create(
                organization=organization,
                boq=boq,
                name="Substructure",
                order=1,
            )
            BoQItem.objects.create(
                organization=organization,
                section=section,
                item_no="A1",
                description="Excavation",
                unit="m3",
                quantity=Decimal("120"),
                rate=Decimal("55.50"),
                amount=Decimal("6660.00"),
                confidence_score=0.95,
            )
        finally:
            reset_current_org(token)

        self.client.force_login(user)
        response = self.client.get(f"/projects/{project.id}/pricing/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Estimate project")
        self.assertContains(response, "Main estimate")
        self.assertContains(response, "Excavation")
        self.assertContains(response, "£15,420.50")

    def test_pricing_review_has_approval_workflow_form(self):
        organization = Organization.objects.create(name="Approval org", type="firm")
        user = User.objects.create_user(
            email="approval-review@example.com",
            organization=organization,
            password="strong-pass-123",
        )

        token = set_current_org(organization)
        try:
            project = Project.objects.create(
                organization=organization,
                created_by=user,
                name="Approval project",
            )
            boq = BoQ.objects.create(
                organization=organization,
                project=project,
                name="Approval estimate",
                status="review_pending",
                total_amount=Decimal("8750.00"),
                ai_confidence_score=0.91,
            )
            section = BoQSection.objects.create(
                organization=organization,
                boq=boq,
                name="Foundations",
                order=1,
            )
            BoQItem.objects.create(
                organization=organization,
                section=section,
                item_no="B2",
                description="Concrete pour",
                unit="m3",
                quantity=Decimal("60"),
                rate=Decimal("95.25"),
                amount=Decimal("5715.00"),
                confidence_score=0.9,
            )
        finally:
            reset_current_org(token)

        self.client.force_login(user)
        response = self.client.get(f"/projects/{project.id}/pricing/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Review decision")
        self.assertContains(response, 'name="decision_action"')
        self.assertContains(response, 'name="decision_reason"')
