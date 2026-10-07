from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm

from documents.enums import DocumentStatus
from documents.models import UploadedDocument
from documents.tasks import process_document_task
from projects.models import Project
from users.models import Organization

User = get_user_model()


PROJECT_TYPE_CHOICES = [
    ("residential", "Residential"),
    ("commercial", "Commercial"),
    ("infrastructure", "Infrastructure"),
    ("industrial", "Industrial"),
]


class UserLoginForm(AuthenticationForm):
    username = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(
            attrs={
                "placeholder": "you@company.com",
                "autocomplete": "email",
            }
        ),
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "••••••••",
                "autocomplete": "current-password",
            }
        ),
    )
    remember_me = forms.BooleanField(required=False)


class OrganizationSignupForm(forms.Form):
    company = forms.CharField(
        max_length=255,
        label="Company",
        widget=forms.TextInput(
            attrs={"placeholder": "Northbridge QS"}
        ),
    )
    email = forms.EmailField(
        label="Work email",
        widget=forms.EmailInput(
            attrs={
                "placeholder": "ava@company.com",
                "autocomplete": "email",
            }
        ),
    )
    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Create a password",
                "autocomplete": "new-password",
            }
        ),
    )
    confirm_password = forms.CharField(
        label="Confirm password",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Repeat your password",
                "autocomplete": "new-password",
            }
        ),
    )

    def clean_email(self):
        email = self.cleaned_data["email"].strip()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords do not match.")

        return cleaned_data

    def save(self):
        company_name = self.cleaned_data["company"].strip()
        organization = Organization.objects.create(
            name=company_name,
            type="firm",
        )
        user = User.objects.create_user(
            email=self.cleaned_data["email"].strip(),
            organization=organization,
            password=self.cleaned_data["password"],
            role="owner",
        )
        return user


class ProjectIntakeForm(forms.Form):
    name = forms.CharField(
        max_length=255,
        label="Project name",
        widget=forms.TextInput(attrs={"placeholder": "North Tower Residences"}),
    )
    description = forms.CharField(
        label="Project brief",
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 5,
                "placeholder": "Briefly describe the scope, deliverables, and any key assumptions.",
            }
        ),
    )
    client_name = forms.CharField(
        max_length=255,
        required=False,
        label="Client",
        widget=forms.TextInput(attrs={"placeholder": "Urban Crest Developments"}),
    )
    location = forms.CharField(
        max_length=255,
        required=False,
        label="Location",
        widget=forms.TextInput(attrs={"placeholder": "Manchester, UK"}),
    )
    project_type = forms.ChoiceField(
        choices=PROJECT_TYPE_CHOICES,
        initial="residential",
        label="Project type",
    )
    file = forms.FileField(
        required=False,
        label="Project file",
    )

    def save(self, user):
        project_description = self.cleaned_data.get("description") or (
            f"Client: {self.cleaned_data.get('client_name', 'N/A')} | "
            f"Location: {self.cleaned_data.get('location', 'N/A')} | "
            f"Type: {self.cleaned_data.get('project_type', 'N/A')}"
        )

        project = Project.objects.create(
            organization=user.organization,
            created_by=user,
            name=self.cleaned_data["name"],
            description=project_description,
        )

        uploaded_file = self.cleaned_data.get("file")
        if uploaded_file:
            document = UploadedDocument.objects.create(
                organization=user.organization,
                project=project,
                file=uploaded_file,
                original_filename=uploaded_file.name,
                status=DocumentStatus.PENDING,
            )
            process_document_task.delay(str(document.id), org_id=str(document.organization_id))

        return project
