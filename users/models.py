import uuid
from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    PermissionsMixin,
    BaseUserManager,
)


# -----------------------
# Organization Model
# -----------------------
class Organization(models.Model):
    PLAN_CHOICES = [
        ("solo", "Solo"),
        ("team", "Team"),
        ("enterprise", "Enterprise"),
    ]

    TYPE_CHOICES = [
        ("individual", "Individual"),
        ("firm", "Firm"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    name = models.CharField(max_length=255)

    type = models.CharField(max_length=20, choices=TYPE_CHOICES)

    subscription_plan = models.CharField(
        max_length=20,
        choices=PLAN_CHOICES,
        default="solo",
    )

    max_users = models.PositiveIntegerField(default=1)
    max_projects = models.PositiveIntegerField(default=5)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.type == "individual":
            self.max_users = 1
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# -----------------------
# User Manager
# -----------------------
class UserManager(BaseUserManager):
    def create_user(self, email, organization=None, password=None, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address")

        email = self.normalize_email(email)

        # Allow system-level creation (e.g. superuser setup)
        if not organization and not extra_fields.get("is_superuser", False):
            raise ValueError("User must belong to an organization")

        user = self.model(
            email=email,
            organization=organization,
            **extra_fields,
        )

        user.set_password(password)
        user.save(using=self._db)
        return user


    def create_superuser(self, email, organization, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", "owner")

        return self.create_user(email, organization, password, **extra_fields)


# -----------------------
# Custom User Model
# -----------------------
class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ("owner", "Owner"),
        ("qs", "Quantity Surveyor"),
        ("viewer", "Viewer"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    email = models.EmailField(unique=True)

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="users",
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default="qs",
    )

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["organization"]

    def __str__(self):
        return self.email


