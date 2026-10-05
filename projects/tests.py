from django.test import TestCase

from core.tenant import reset_current_org, set_current_org
from projects.models import Project
from users.models import Organization, User


class ProjectModelTests(TestCase):
    def test_project_defaults_to_draft_and_is_not_frozen(self):
        organization = Organization.objects.create(
            name="Project org",
            type="firm",
        )
        user = User.objects.create_user(
            email="project-owner@example.com",
            organization=organization,
            password="strong-pass-123",
        )

        token = set_current_org(organization)
        try:
            project = Project.objects.create(
                organization=organization,
                created_by=user,
                name="Initial estimate",
            )
        finally:
            reset_current_org(token)

        self.assertEqual(project.status, "draft")
        self.assertFalse(project.is_frozen)
        self.assertEqual(str(project), "Initial estimate")

    def test_project_can_be_created_only_for_current_org(self):
        organization = Organization.objects.create(
            name="Current org",
            type="firm",
        )
        other_organization = Organization.objects.create(
            name="Other org",
            type="firm",
        )
        user = User.objects.create_user(
            email="current-org-user@example.com",
            organization=organization,
            password="strong-pass-123",
        )

        token = set_current_org(organization)
        try:
            project = Project.objects.create(
                organization=organization,
                created_by=user,
                name="Current tenant project",
            )
        finally:
            reset_current_org(token)

        self.assertEqual(project.organization, organization)
        self.assertNotEqual(project.organization, other_organization)
        self.assertEqual(project.status, "draft")
