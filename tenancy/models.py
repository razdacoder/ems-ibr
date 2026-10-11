"""Platform data in the public schema: plans, schools and their hostnames.

Each ``School`` is a Postgres schema holding its own ``ems`` tables, picked
per request from the Host header (``tenancy.middleware.SchoolMiddleware``).
The public schema is a ``School`` row too, ``schema_name="public"``, serving
``console.<base>`` and ``api.<base>`` (spec 0003). Platform admins, their
tokens and the console audit log live here as well.
"""
from django.contrib.auth.hashers import (
    check_password,
    is_password_usable,
    make_password,
)
from django.core.exceptions import ValidationError
from django.db import connection, models, transaction
from django_tenants.models import DomainMixin, TenantMixin
from django_tenants.utils import get_public_schema_name

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
    created_by = models.ForeignKey(
        "PlatformAdmin",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="schools_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def drop_schema(self, batch_size=None):
        """Drop this school's schema and every table in it, if it exists.

        With ``batch_size``, tables go first in batches, each in its own
        transaction: one ``DROP SCHEMA ... CASCADE`` takes a lock per object
        and runs out of ``max_locks_per_transaction`` on a big schema. Call
        it that way only outside ``atomic()``.
        """
        if self.schema_name == get_public_schema_name():
            raise ValueError("The public schema is never dropped.")
        quote = connection.ops.quote_name
        schema = quote(self.schema_name)
        if batch_size:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT tablename FROM pg_tables WHERE schemaname = %s",
                    [self.schema_name],
                )
                tables = [row[0] for row in cursor.fetchall()]
            for start in range(0, len(tables), batch_size):
                names = ", ".join(
                    f"{schema}.{quote(t)}" for t in tables[start : start + batch_size]
                )
                with transaction.atomic(), connection.cursor() as cursor:
                    cursor.execute(f"DROP TABLE IF EXISTS {names} CASCADE")
        with connection.cursor() as cursor:
            cursor.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")


class Domain(DomainMixin):
    """A hostname that resolves to a school, e.g. ``unilag.ordo.app``."""


class PlatformAdmin(models.Model):
    """A member of the Ordo team, signing in at ``console.<base>``.

    Deliberately not ``AUTH_USER_MODEL``: it only exists in the public schema,
    so a platform account can never turn up as a user inside a school.
    """

    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        SUPPORT = "support", "Support"

    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255)
    # Unusable until the invite is accepted (tenancy.invites).
    password = models.CharField(max_length=128)
    role = models.CharField(max_length=10, choices=Role.choices)
    # Fernet encrypted (tenancy.totp). Replaced on every login until confirmed.
    totp_secret = models.TextField(blank=True, default="")
    totp_confirmed_at = models.DateTimeField(null=True, blank=True)
    # The last accepted timestep: a code at or before it is a replay.
    totp_last_step = models.BigIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    last_login = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # DRF treats whatever authentication returns as request.user.
    is_authenticated = True
    is_anonymous = False

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        # Matched case insensitively at login, so stored in one case.
        self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    @property
    def is_owner(self):
        return self.role == self.Role.OWNER

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        def upgrade(raw):
            self.set_password(raw)
            self.save(update_fields=["password"])

        return check_password(raw_password, self.password, upgrade)

    def set_unusable_password(self):
        # A fresh random value each time, which also voids any invite link
        # signed over the old one.
        self.password = make_password(None)

    def has_usable_password(self):
        return is_password_usable(self.password)


class PlatformToken(models.Model):
    """A console session. Only the SHA-256 of the key is stored."""

    key_hash = models.CharField(max_length=64, primary_key=True)
    admin = models.ForeignKey(
        PlatformAdmin, on_delete=models.CASCADE, related_name="tokens"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()


class PlatformAuditLog(models.Model):
    """Every console write, sign in and failed attempt.

    Failed attempts double as the lockout counter (tenancy.lockout).
    """

    admin = models.ForeignKey(
        PlatformAdmin,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_entries",
    )
    school = models.ForeignKey(
        School,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="platform_audit_entries",
    )
    action = models.CharField(max_length=64)
    detail = models.JSONField(default=dict, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["school", "-created_at"]),
            models.Index(fields=["action", "-created_at"]),
        ]


class SupportSession(models.Model):
    """A platform admin's visit to a school as its Ordo support user.

    The ticket is the one time credential in the link the console opens;
    only its SHA-256 is stored. Redeeming it starts the session, which
    lasts at most an hour (spec 0003, child 0006). ``tenant_user_id`` is the
    shadow user's id in the school's schema; no foreign key crosses schemas.
    """

    admin = models.ForeignKey(
        PlatformAdmin, on_delete=models.PROTECT, related_name="support_sessions"
    )
    school = models.ForeignKey(
        School, on_delete=models.PROTECT, related_name="support_sessions"
    )
    reason = models.TextField()
    ticket_hash = models.CharField(max_length=64, unique=True)
    ticket_expires_at = models.DateTimeField()
    ticket_used_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    tenant_user_id = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["school", "-created_at"])]


class UsageSnapshot(models.Model):
    """One day's usage of a school, taken nightly by ``snapshot_usage``.

    The console's school list shows the latest one, so listing schools never
    has to enter every schema. Kept 400 days (spec 0003, child 0005).
    """

    school = models.ForeignKey(
        School, on_delete=models.CASCADE, related_name="usage_snapshots"
    )
    taken_on = models.DateField()
    students = models.PositiveIntegerField()
    staff_users = models.PositiveIntegerField()
    jobs_last_24h = models.PositiveIntegerField()
    last_activity_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-taken_on"]
        constraints = [
            models.UniqueConstraint(fields=["school", "taken_on"], name="usage_snapshot_per_day")
        ]
