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


class RestFrameworkConfigTests(TestCase):
    """Guards the global DRF defaults that harden the API."""

    def test_default_permission_is_authenticated(self):
        from django.conf import settings

        classes = settings.REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"]
        self.assertIn(
            "rest_framework.permissions.IsAuthenticated",
            classes,
        )

    def test_default_pagination_is_configured(self):
        from django.conf import settings

        self.assertEqual(
            settings.REST_FRAMEWORK["DEFAULT_PAGINATION_CLASS"],
            "core.pagination.StandardResultsSetPagination",
        )

    def test_throttling_disabled_in_tests(self):
        # Tests must stay deterministic; throttling state lives in Redis.
        from django.conf import settings

        self.assertEqual(settings.REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"], [])


class SentryScrubberTests(TestCase):
    """The before_send scrubber must never leak secrets to Sentry."""

    def _scrub(self, value):
        from core.sentry import _scrub_value

        return _scrub_value(value)

    def test_redacts_known_secret_shapes_in_strings(self):
        sample = (
            "failed: sk-proj-ABCDEF123 and tid_TOPSECRET and "
            "tsec_ALSOSECRET and eyJhbGci.eyJzdWIi.sig"
        )
        out = self._scrub(sample)
        self.assertNotIn("sk-proj-ABCDEF123", out)
        self.assertNotIn("tid_TOPSECRET", out)
        self.assertNotIn("tsec_ALSOSECRET", out)
        self.assertNotIn("eyJhbGci.eyJzdWIi.sig", out)

    def test_redacts_sensitive_keys_but_keeps_others(self):
        from core.sentry import _scrub_mapping

        cleaned = _scrub_mapping(
            {
                "api_key": "sk-proj-LEAK",
                "authorization": "Bearer abc",
                "name": "keep-me",
                "nested": {"password": "p", "count": 3},
            }
        )
        self.assertEqual(cleaned["api_key"], "[Filtered]")
        self.assertEqual(cleaned["authorization"], "[Filtered]")
        self.assertEqual(cleaned["name"], "keep-me")
        self.assertEqual(cleaned["nested"]["password"], "[Filtered]")
        self.assertEqual(cleaned["nested"]["count"], 3)

    def test_init_sentry_noops_without_dsn(self):
        from core.sentry import init_sentry

        # No SENTRY_DSN in the test environment -> must be a safe no-op.
        self.assertFalse(init_sentry())



class AdminRegistrationTests(TestCase):
    """
    Every core model must be reachable in Django admin. The tenant-scoped
    admin reads through ``_base_manager`` so a superuser can list records even
    though the default manager is empty without a request tenant context.
    """

    def setUp(self):
        self.org = Organization.objects.create(name="Admin Reg Org", type="firm")
        self.admin_user = User.objects.create_superuser(
            email="admin-reg@example.com",
            organization=self.org,
            password="strong-pass-123",
        )
        self.client.force_login(self.admin_user)

    def test_model_changelists_render(self):
        from django.urls import reverse

        changelists = [
            "admin:users_organization_changelist",
            "admin:users_user_changelist",
            "admin:projects_project_changelist",
            "admin:documents_uploadeddocument_changelist",
            "admin:boq_boq_changelist",
            "admin:boq_boqsection_changelist",
            "admin:boq_boqitem_changelist",
            "admin:pricing_ratelibrary_changelist",
            "admin:tribunal_tribunalcase_changelist",
            "admin:audit_auditevent_changelist",
        ]
        for name in changelists:
            with self.subTest(changelist=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)



class LoginThrottleTests(TestCase):
    """The login form must be rate-limited to resist brute-force attempts."""

    def setUp(self):
        # Cache is locmem in tests; clear it so counters don't leak across tests.
        from django.core.cache import cache

        cache.clear()

    def test_login_is_throttled_after_burst_of_attempts(self):
        from core.ratelimit import LOGIN_PER_IP_LIMIT

        url = "/login/"
        payload = {
            "login_submit": "1",
            "login-username": "victim@example.com",
            "login-password": "wrong-password",
        }

        # A few failures below the limit still render the form (200).
        for _ in range(LOGIN_PER_IP_LIMIT):
            response = self.client.post(url, payload)
        self.assertEqual(response.status_code, 429)

    def test_login_below_limit_is_not_throttled(self):
        # The email-scoped limit is the binding one for a single account, so
        # a handful of failures just under it must still render the form.
        from core.ratelimit import LOGIN_PER_EMAIL_LIMIT

        url = "/login/"
        payload = {
            "login_submit": "1",
            "login-username": "ok@example.com",
            "login-password": "wrong",
        }
        for _ in range(LOGIN_PER_EMAIL_LIMIT - 1):
            response = self.client.post(url, payload)
        self.assertEqual(response.status_code, 200)

    def test_successful_login_still_works(self):
        organization = Organization.objects.create(name="Login QS", type="firm")
        User.objects.create_user(
            email="real@example.com",
            organization=organization,
            password="strong-pass-123",
        )
        response = self.client.post(
            "/login/",
            {
                "login_submit": "1",
                "login-username": "real@example.com",
                "login-password": "strong-pass-123",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/dashboard/", response["Location"])


class PasswordResetTests(TestCase):
    """Full password-reset flow: request -> email -> confirm -> sign in."""

    def setUp(self):
        from django.core.cache import cache

        cache.clear()
        self.organization = Organization.objects.create(name="Reset QS", type="firm")
        self.user = User.objects.create_user(
            email="reset@example.com",
            organization=self.organization,
            password="old-pass-123",
        )

    def test_reset_request_sends_email(self):
        from django.core import mail

        response = self.client.post(
            "/password-reset/",
            {"email": self.user.email},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.user.email, mail.outbox[0].to)

    def test_reset_flow_changes_password_and_allows_signin(self):
        from django.core import mail
        from django.urls import reverse
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        from django.contrib.auth.tokens import default_token_generator

        response = self.client.post(
            "/password-reset/",
            {"email": self.user.email},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)

        # Build the reset link the same way the emailed link does.
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        confirm_url = reverse("password_reset_confirm", kwargs={"uidb64": uid, "token": token})

        # Django's confirm flow is two-step: GET the link, which stores the
        # token in session and 302-redirects to a tokenless ".../set-password/"
        # URL. Follow that redirect to reach the real form.
        response = self.client.get(confirm_url, follow=True)
        self.assertEqual(response.status_code, 200)

        # The final URL after following is the tokenless set-password endpoint.
        set_password_url = response.request["PATH_INFO"]

        # POST the new password to the session-backed set-password URL.
        response = self.client.post(
            set_password_url,
            {"new_password1": "brand-new-pass-456", "new_password2": "brand-new-pass-456"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("brand-new-pass-456"))

        # The old password must no longer work; the new one signs in.
        self.assertFalse(self.user.check_password("old-pass-123"))
        signin = self.client.post(
            "/login/",
            {
                "login_submit": "1",
                "login-username": "reset@example.com",
                "login-password": "brand-new-pass-456",
            },
        )
        self.assertEqual(signin.status_code, 302)

    def test_unknown_email_does_not_leak(self):
        from django.core import mail

        response = self.client.post(
            "/password-reset/",
            {"email": "nobody@example.com"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        # Same generic success page, no email sent.
        self.assertEqual(len(mail.outbox), 0)

