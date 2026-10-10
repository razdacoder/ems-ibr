"""Platform data in the public schema: plans, schools and their hostnames.

Each ``School`` is a Postgres schema holding its own ``ems`` tables, picked
per request from the Host header (``tenancy.middleware.SchoolMiddleware``).
The public schema is a ``School`` row too, ``schema_name="public"``, serving
``admin.<base>`` and ``api.<base>`` (spec 0003).
"""
from django.core.exceptions import ValidationError
from django.db import models
from django_tenants.models import DomainMixin, TenantMixin

from tenancy.features import KEYS


def validate_feature_keys(value):
    if value is None:
        return
    if not isinstance(value, list) or not all(isinstance(k, str) for k in value):
        raise ValidationError("Features must be a list of feature keys.")
    unknown = sorted(set(value) - KEYS)
    if unknown:
        raise ValidationError(f"Unknown feature keys: {', '.join(unknown)}.")


class Plan(models.Model):
    """A tier of limits and features. Deactivated, never deleted."""

    code = models.SlugField(unique=True)
    name = models.CharField(max_length=100)
    # Null means unlimited.
    max_students = models.PositiveIntegerField(null=True, blank=True)
    max_staff_users = models.PositiveIntegerField(null=True, blank=True)
    features = models.JSONField(default=list, validators=[validate_feature_keys])
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class School(TenantMixin):
    """One school, living in its own schema ``school_<slug>``.

    Rows are never deleted, so a slug stays reserved even after a purge.
    """

    class Status(models.TextChoices):
        PROVISIONING = "provisioning", "Provisioning"
        ACTIVE = "active", "Active"
        FAILED = "failed", "Failed"
        SUSPENDED = "suspended", "Suspended"
        PENDING_DELETION = "pending_deletion", "Pending deletion"
        PURGED = "purged", "Purged"

    # Schools whose schema is in use and must follow every deploy's
    # migrations. Provisioning and failed schemas are rebuilt from scratch.
    LIVE_STATUSES = (Status.ACTIVE, Status.SUSPENDED, Status.PENDING_DELETION)

    # The schema is created by provisioning, never as a side effect of save().
    auto_create_schema = False

    slug = models.SlugField(max_length=30, unique=True)
    name = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PROVISIONING
    )
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="schools")
    # Null means "use the plan's value" (tenancy.limits.effective).
    max_students_override = models.PositiveIntegerField(null=True, blank=True)
    max_staff_users_override = models.PositiveIntegerField(null=True, blank=True)
    features_override = models.JSONField(
        null=True, blank=True, validators=[validate_feature_keys]
    )
    first_admin_name = models.CharField(max_length=255)
    first_admin_email = models.EmailField()
    contact_name = models.CharField(max_length=255, blank=True, default="")
    contact_email = models.EmailField(blank=True, default="")
    country = models.CharField(max_length=2, blank=True, default="")
    timezone = models.CharField(max_length=64, default="Africa/Lagos")
    notes = models.TextField(blank=True, default="")
    plan_started_on = models.DateField(null=True, blank=True)
    renews_on = models.DateField(null=True, blank=True)
    provisioning_error = models.TextField(blank=True, default="")
    provisioning_started_at = models.DateTimeField(null=True, blank=True)
    was_ever_active = models.BooleanField(default=False)
    suspended_at = models.DateTimeField(null=True, blank=True)
    suspended_reason = models.TextField(blank=True, default="")
    deletion_requested_at = models.DateTimeField(null=True, blank=True)
    purge_after = models.DateTimeField(null=True, blank=True)
    # Bucket key of the final export, or "never_active".
    final_export_ref = models.CharField(max_length=255, blank=True, default="")
    purged_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Domain(DomainMixin):
    """A hostname that resolves to a school, e.g. ``unilag.ordo.app``."""
