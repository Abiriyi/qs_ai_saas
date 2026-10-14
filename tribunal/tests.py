# tribunal/tests.py
from django.test import TestCase

from audit.models import AuditEvent
from boq.models import BoQ
from core.tenant import reset_current_org, set_current_org
from projects.models import Project
from tribunal.models import TribunalCaseStatus, TribunalDecision
from tribunal.services import TribunalError, TribunalService
from users.models import Organization, User


class TribunalServiceTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Tribunal Org", type="firm")
        self.user = User.objects.create_user(
            email="adjudicator@example.com",
            organization=self.organization,
            password="strong-pass-123",
        )
        self.token = set_current_org(self.organization)
        self.project = Project.objects.create(
            organization=self.organization,
            created_by=self.user,
            name="Disputed project",
        )
        self.boq = BoQ.objects.create(
            organization=self.organization,
            project=self.project,
            name="Disputed BoQ",
            status="draft",
        )

    def tearDown(self):
        reset_current_org(self.token)

    def test_open_case_freezes_project_and_boq(self):
        case = TribunalService.open_case(
            project=self.project,
            raised_by=self.user,
            title="Rate dispute",
            boq=self.boq,
        )
        self.project.refresh_from_db()
        self.boq.refresh_from_db()

        self.assertEqual(case.status, TribunalCaseStatus.OPEN)
        self.assertTrue(case.reference.startswith("TRB-"))
        self.assertTrue(self.project.is_frozen)
        self.assertTrue(self.boq.is_frozen)
        self.assertTrue(
            AuditEvent.objects.filter(action="case_opened", category="tribunal").exists()
        )

    def test_decide_upheld_keeps_boq_frozen(self):
        case = TribunalService.open_case(
            project=self.project, raised_by=self.user, title="Scope dispute", boq=self.boq
        )
        TribunalService.decide(
            case=case,
            decision=TribunalDecision.UPHELD,
            decided_by=self.user,
            notes="Original stands",
        )
        self.project.refresh_from_db()
        self.boq.refresh_from_db()

        self.assertEqual(case.status, TribunalCaseStatus.DECIDED)
        self.assertTrue(self.boq.is_frozen)
        self.assertTrue(AuditEvent.objects.filter(action="case_decided").exists())

    def test_decide_amended_releases_freeze(self):
        case = TribunalService.open_case(
            project=self.project, raised_by=self.user, title="Quantity dispute", boq=self.boq
        )
        TribunalService.decide(
            case=case,
            decision=TribunalDecision.AMENDED,
            decided_by=self.user,
            notes="Adjust quantity",
        )
        self.project.refresh_from_db()
        self.boq.refresh_from_db()

        self.assertFalse(self.project.is_frozen)
        self.assertFalse(self.boq.is_frozen)

    def test_cannot_decide_twice(self):
        case = TribunalService.open_case(
            project=self.project, raised_by=self.user, title="Double dispute"
        )
        TribunalService.decide(
            case=case, decision=TribunalDecision.DISMISSED, decided_by=self.user
        )
        with self.assertRaises(TribunalError):
            TribunalService.decide(
                case=case, decision=TribunalDecision.UPHELD, decided_by=self.user
            )

    def test_withdraw_releases_freeze(self):
        case = TribunalService.open_case(
            project=self.project, raised_by=self.user, title="Withdraw dispute", boq=self.boq
        )
        TribunalService.withdraw(case, self.user)
        self.project.refresh_from_db()
        self.boq.refresh_from_db()

        self.assertEqual(case.status, TribunalCaseStatus.WITHDRAWN)
        self.assertFalse(self.project.is_frozen)
        self.assertFalse(self.boq.is_frozen)


class TribunalAPITests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Tribunal API Org", type="firm")
        self.user = User.objects.create_user(
            email="api-adjudicator@example.com",
            organization=self.organization,
            password="strong-pass-123",
        )
        self.token = set_current_org(self.organization)
        self.project = Project.objects.create(
            organization=self.organization,
            created_by=self.user,
            name="API project",
        )
        self.client.force_login(self.user)

    def tearDown(self):
        reset_current_org(self.token)

    def test_create_and_decide_case_over_api(self):
        response = self.client.post(
            "/api/tribunal/",
            {"project_id": str(self.project.id), "title": "API dispute"},
        )
        self.assertEqual(response.status_code, 201)
        case_id = response.json()["id"]

        decide = self.client.post(
            f"/api/tribunal/{case_id}/decide/",
            {"decision": "dismissed", "notes": "no merit"},
        )
        self.assertEqual(decide.status_code, 200)
        self.assertEqual(decide.json()["decision"], "dismissed")

    def test_list_requires_authentication(self):
        self.client.logout()
        response = self.client.get("/api/tribunal/")
        self.assertEqual(response.status_code, 403)


class TribunalPageTests(TestCase):
    def test_tribunal_dashboard_requires_login(self):
        response = self.client.get("/tribunal/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response["Location"])

    def test_tribunal_dashboard_renders(self):
        organization = Organization.objects.create(name="Tribunal Page Org", type="firm")
        user = User.objects.create_user(
            email="page-adjudicator@example.com",
            organization=organization,
            password="strong-pass-123",
        )
        self.client.force_login(user)
        response = self.client.get("/tribunal/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tribunal")

