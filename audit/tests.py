# audit/tests.py
from django.test import TestCase

from audit.models import AuditEvent
from audit.services import AuditService
from core.tenant import reset_current_org, set_current_org
from users.models import Organization, User


class AuditServiceTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Audit Org", type="firm")
        self.other_org = Organization.objects.create(name="Other Org", type="firm")
        self.user = User.objects.create_user(
            email="auditor@example.com",
            organization=self.organization,
            password="strong-pass-123",
        )

    def test_log_creates_event_for_current_org(self):
        token = set_current_org(self.organization)
        try:
            event = AuditService.log(
                action="test_action",
                actor=self.user,
                model_name="BoQ",
                object_id="abc",
                category="boq",
                message="hello",
                payload={"k": "v"},
            )
        finally:
            reset_current_org(token)

        self.assertIsNotNone(event)
        self.assertEqual(event.organization, self.organization)
        self.assertEqual(event.actor, self.user)
        self.assertEqual(event.action, "test_action")
        self.assertEqual(event.category, "boq")
        self.assertEqual(event.payload, {"k": "v"})

    def test_log_falls_back_to_actor_organization(self):
        # No tenant context set: the service derives the org from the actor.
        event = AuditService.log(action="actor_org", actor=self.user)
        self.assertIsNotNone(event)
        self.assertEqual(event.organization, self.organization)

    def test_log_is_fail_safe(self):
        # Auditing is a side-effect: if the write raises, log() must swallow it
        # and return None rather than breaking the caller's business flow.
        from unittest.mock import patch

        with patch(
            "audit.models.AuditEvent.objects.create",
            side_effect=Exception("db down"),
        ):
            result = AuditService.log(action="boom", organization=self.organization)
        self.assertIsNone(result)

    def test_for_current_org_scopes_events(self):
        token = set_current_org(self.organization)
        try:
            AuditEvent.objects.create(
                organization=self.organization, action="mine", category="boq"
            )
            AuditEvent.objects.create(
                organization=self.other_org, action="theirs", category="boq"
            )
            events = AuditEvent.objects.for_current_org()
        finally:
            reset_current_org(token)

        actions = {e.action for e in events}
        self.assertIn("mine", actions)
        self.assertNotIn("theirs", actions)


class AuditAPITests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Audit API Org", type="firm")
        self.user = User.objects.create_user(
            email="api-auditor@example.com",
            organization=self.organization,
            password="strong-pass-123",
        )
        self.client.force_login(self.user)

    def test_list_requires_authentication(self):
        self.client.logout()
        response = self.client.get("/api/audit/")
        self.assertEqual(response.status_code, 403)

    def test_list_returns_only_current_org_events(self):
        other_org = Organization.objects.create(name="Other API Org", type="firm")
        AuditEvent.objects.create(organization=self.organization, action="mine", category="boq")
        AuditEvent.objects.create(organization=other_org, action="theirs", category="boq")

        response = self.client.get("/api/audit/")
        self.assertEqual(response.status_code, 200)
        actions = {row["action"] for row in response.json()["results"]}
        self.assertIn("mine", actions)
        self.assertNotIn("theirs", actions)

    def test_list_filters_by_category(self):
        AuditEvent.objects.create(organization=self.organization, action="a", category="boq")
        AuditEvent.objects.create(organization=self.organization, action="b", category="pricing")

        response = self.client.get("/api/audit/?category=pricing")
        self.assertEqual(response.status_code, 200)
        actions = {row["action"] for row in response.json()["results"]}
        self.assertEqual(actions, {"b"})


class AuditPageTests(TestCase):
    def test_audit_trail_requires_login(self):
        response = self.client.get("/audit/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response["Location"])

    def test_audit_trail_renders_for_current_org(self):
        organization = Organization.objects.create(name="Audit Page Org", type="firm")
        user = User.objects.create_user(
            email="page-auditor@example.com",
            organization=organization,
            password="strong-pass-123",
        )
        AuditEvent.objects.create(
            organization=organization, action="approved", category="boq"
        )
        self.client.force_login(user)

        response = self.client.get("/audit/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Audit trail")
        self.assertContains(response, "approved")
