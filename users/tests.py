from django.test import TestCase

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
