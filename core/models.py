import uuid
from django.core.exceptions import FieldDoesNotExist, ValidationError
from django.db import models
from django.utils import timezone
from core.tenant import get_current_org


class TenantQuerySet(models.QuerySet):
    def for_current_org(self):
        org = get_current_org()
        if org:
            return self.filter(organization=org)
        return self.none()

    def delete(self):
        org = get_current_org()
        if not org:
            raise ValidationError("Tenant context is required for writes.")
        return models.QuerySet.delete(
            self.filter(organization=org)
        )

    def update(self, **kwargs):
        org = get_current_org()
        if not org:
            raise ValidationError("Tenant context is required for writes.")

        for name, value in kwargs.items():
            field_name = name.split("__", 1)[0]
            field = next(
                (
                    candidate
                    for candidate in self.model._meta.concrete_fields
                    if field_name in (candidate.name, candidate.attname)
                ),
                None,
            )
            if field is None:
                raise FieldDoesNotExist(field_name)
            if field.name == "organization":
                value_id = getattr(value, "pk", value)
                if str(value_id) != str(org.pk):
                    raise ValidationError(
                        "Cannot write a record for another organization."
                    )
                continue

            if not isinstance(field, models.ForeignKey):
                continue

            related_model = field.remote_field.model
            try:
                related_model._meta.get_field("organization")
            except FieldDoesNotExist:
                continue

            related_id = getattr(value, "pk", value)
            related_org_id = (
                related_model._base_manager.filter(pk=related_id)
                .values_list("organization_id", flat=True)
                .first()
            )
            if (
                related_org_id is not None
                and str(related_org_id) != str(org.pk)
            ):
                raise ValidationError(
                    f"{field.name} belongs to another organization."
                )

        return models.QuerySet.update(
            self.filter(organization=org),
            **kwargs,
        )

    def bulk_create(self, objs, *args, **kwargs):
        for obj in objs:
            obj._validate_tenant_write()
        return super().bulk_create(objs, *args, **kwargs)

    def bulk_update(self, objs, fields, *args, **kwargs):
        for obj in objs:
            obj._validate_tenant_write()
        return super().bulk_update(objs, fields, *args, **kwargs)


class TenantManager(models.Manager.from_queryset(TenantQuerySet)):

    def get_queryset(self):

        qs = super().get_queryset().filter(
            deleted_at__isnull=True
        )

        org = get_current_org()

        if org:
            if isinstance(org, models.Model):
                return qs.filter(organization=org)
            return qs

        return qs.none()
        
class BaseTenantModel(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    organization = models.ForeignKey(
        "users.Organization",
        on_delete=models.CASCADE,
    )

    deleted_at = models.DateTimeField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()

    class Meta:
        abstract = True

    def _validate_tenant_write(self):
        org = get_current_org()
        if not org:
            raise ValidationError("Tenant context is required for writes.")

        if not self.organization_id:
            self.organization = org

        if str(self.organization_id) != str(org.pk):
            raise ValidationError(
                "Cannot write a record for another organization."
            )

        for field in self._meta.concrete_fields:
            if not isinstance(field, models.ForeignKey):
                continue
            if field.name == "organization":
                continue

            related_model = field.remote_field.model
            try:
                related_model._meta.get_field("organization")
            except FieldDoesNotExist:
                continue

            related_id = getattr(self, field.attname)
            if related_id is None:
                continue

            related_object = self._state.fields_cache.get(field.name)
            if related_object is not None:
                related_org_id = related_object.organization_id
            else:
                related_org_id = (
                    related_model._base_manager.filter(pk=related_id)
                    .values_list("organization_id", flat=True)
                    .first()
                )

            if (
                related_org_id is not None
                and str(related_org_id) != str(self.organization_id)
            ):
                raise ValidationError(
                    f"{field.name} belongs to another organization."
                )

    def save(self, *args, **kwargs):
        self._validate_tenant_write()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        org = get_current_org()
        if not org:
            raise ValidationError("Tenant context is required for writes.")
        if str(self.organization_id) != str(org.pk):
            raise ValidationError(
                "Cannot write a record for another organization."
            )
        return super().delete(*args, **kwargs)

    def soft_delete(self):
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at"])   



