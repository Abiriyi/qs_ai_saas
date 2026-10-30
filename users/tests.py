import re

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator

from users.models import Organization, User


class OrganizationModelTests(TestCase):
    def test_individual_organization_enforces_single_user_limit(self):
        organization = Organization.objects.create(
            name="Solo practice",
            type="individual",
        )

        self.assertEqual(organization.max_users, 1)
        self.assertEqual(organization.subscription_plan, "solo")

    def test_firm_organization_keeps_custom_limits(self):
        organization = Organization.objects.create(
            name="Consulting firm",
            type="firm",
            max_users=12,
            max_projects=40,
        )

        self.assertEqual(organization.max_users, 12)
        self.assertEqual(organization.max_projects, 40)


class UserManagerTests(TestCase):
    def test_user_requires_org_during_regular_creation(self):
        with self.assertRaisesMessage(ValueError, "User must belong to an organization"):
            User.objects.create_user(
                email="no-org@example.com",
                password="strong-pass-123",
            )

    def test_superuser_can_be_created_without_explicit_org(self):
        organization = Organization.objects.create(
            name="Owner org",
            type="firm",
        )

        user = User.objects.create_superuser(
            email="owner@example.com",
            organization=organization,
            password="strong-pass-123",
        )

        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertEqual(user.role, "owner")
        self.assertEqual(str(user), "owner@example.com")

    def test_user_can_be_created_with_org_and_defaults(self):
        organization = Organization.objects.create(
            name="Team org",
            type="firm",
        )

        user = User.objects.create_user(
            email="qs@example.com",
            organization=organization,
            password="strong-pass-123",
        )

        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertEqual(user.organization, organization)
        self.assertEqual(user.role, "qs")


class UserModelValidationTests(TestCase):
    def test_normal_user_cannot_create_without_organization(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(
                email="missing-org@example.com",
                password="strong-pass-123",
                organization=None,
            )


class PasswordResetFlowTests(TestCase):
    """End-to-end tests for the password reset flow."""

    def setUp(self):
        self.organization = Organization.objects.create(
            name="Test Org", type="firm"
        )
        self.user = User.objects.create_user(
            email="reset-user@example.com",
            organization=self.organization,
            password="OldPass123!",
            role="qs",
        )

    def test_reset_form_page_loads(self):
        response = self.client.get(reverse("password_reset"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "password_reset_form.html")

    def test_request_reset_sends_email(self):
        """Requesting a reset for a known email sends a reset email."""
        self.assertEqual(len(mail.outbox), 0)
        response = self.client.post(
            reverse("password_reset"),
            {"email": "reset-user@example.com"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("password_reset_done"))

        # One email should have been sent
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.subject, "Reset your QS AI password")
        self.assertIn("reset-user@example.com", email.to)
        # The email body contains the reset URL path (not the URL name)
        self.assertIn("/password-reset/", email.body)
        uidb64 = urlsafe_base64_encode(force_bytes(self.user.pk))
        self.assertIn(uidb64, email.body)

    def test_request_reset_for_unknown_email_still_sends_no_error(self):
        """A reset for an unknown email should not leak whether the account exists."""
        response = self.client.post(
            reverse("password_reset"),
            {"email": "does-not-exist@example.com"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 0)

    def test_reset_link_sets_new_password(self):
        """Following the reset link lets the user set a new password."""
        # Request the reset so an email is generated
        self.client.post(
            reverse("password_reset"),
            {"email": "reset-user@example.com"},
        )
        self.assertEqual(len(mail.outbox), 1)

        # Extract uidb64 and token from the email body link
        email_body = mail.outbox[0].body
        match = re.search(
            r"/password-reset/([^/]+)/([^/]+)/", email_body
        )
        self.assertIsNotNone(match, "Reset link not found in email body")
        uidb64, token = match.group(1), match.group(2)

        # Confirm page should show the form with a valid link.
        # Django 5.2 redirects from /<token>/ to /set-password/ to avoid
        # leaking the token in the Referer header.
        response = self.client.get(
            reverse("password_reset_confirm", args=[uidb64, token]),
            follow=True,
        )
        self.assertEqual(
            response.status_code,
            200,
            f"Expected 200, got {response.status_code}. "
            f"Redirect chain: {response.redirect_chain}",
        )
        self.assertTrue(response.context["validlink"])

        # The set-password URL is the last URL in the redirect chain.
        set_password_url = response.redirect_chain[-1][0]

        # Submit the new password at the set-password URL.
        response = self.client.post(
            set_password_url,
            {
                "new_password1": "NewPass456!",
                "new_password2": "NewPass456!",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("password_reset_complete"))

        # After a successful reset, the token is invalidated because the
        # user's password changed (the token hash incorporates it).
        response = self.client.get(
            reverse("password_reset_confirm", args=[uidb64, token]),
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["validlink"])

        # The user should be able to log in with the new password
        self.assertTrue(
            self.client.login(
                email="reset-user@example.com", password="NewPass456!"
            )
        )
        self.assertFalse(
            self.client.login(
                email="reset-user@example.com", password="OldPass123!"
            )
        )

    def test_reset_confirm_with_invalid_token(self):
        """An invalid token should render the invalid-link page."""
        response = self.client.get(
            reverse("password_reset_confirm", args=["invalid-uid", "bad-token"])
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["validlink"])
