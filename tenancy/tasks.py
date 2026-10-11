"""Platform background work: email, building a school's schema, the final
export and purge of a deleted one, and closing expired support sessions.

Every task here is queued from the public schema and stays there, entering a
school's schema with ``schema_context`` (spec 0003, child 0004).
"""
import logging
from datetime import timedelta

from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone
from django_tenants.utils import schema_context

from tenancy import exports
from tenancy.models import Domain, PlatformAuditLog, School, SupportSession

logger = logging.getLogger(__name__)

EMAIL_MAX_RETRIES = 3

# Longer than the 30 minute hard limit, so a task still running is never
# marked failed under its own feet.
STALE_PROVISIONING_AFTER = timedelta(minutes=35)
STALE_PROVISIONING_ERROR = "Provisioning did not finish (worker stopped)."


@shared_task(bind=True, ignore_result=True, max_retries=EMAIL_MAX_RETRIES)
def send_email(self, to, subject, template, context):
    """Send ``emails/<template>.txt`` (plus its ``.html``) over SMTP.

    Runs on a worker so no request waits on SMTP. A failure is retried 3
    times with backoff (1, 2, 4 minutes), then logged. Whatever link the
    email carried stays valid and can be resent.
    """
    text = render_to_string(f"emails/{template}.txt", context)
    html = render_to_string(f"emails/{template}.html", context)
    message = EmailMultiAlternatives(subject, text, None, [to])
    message.attach_alternative(html, "text/html")
    try:
        message.send()
    except Exception as exc:
        if self.request.retries >= EMAIL_MAX_RETRIES:
            logger.exception("Giving up emailing %r (template %s)", to, template)
            return
        raise self.retry(exc=exc, countdown=60 * 2**self.request.retries)


def _audit(school, action, **detail):
    PlatformAuditLog.objects.create(school=school, action=action, detail=detail)


@shared_task(ignore_result=True)
def provision_school(school_id):
    """Create and migrate the school's schema, seed it, invite its first admin.

    Ends ``active``, or ``failed`` with the error kept for the console.
    """
    with transaction.atomic():
        school = School.objects.select_for_update().get(pk=school_id)
        if school.status != School.Status.PROVISIONING:
            return

    try:
        school.create_schema(check_if_exists=True, verbosity=0)
        with schema_context(school.schema_name):
            from ems import invites
            from ems.models import SystemSettings, User

            # A redelivered task finds the row already there.
            if not SystemSettings.objects.exists():
                SystemSettings.objects.create(
                    institution_name=school.name,
                    contact_email=school.contact_email,
                )
            invites.invite(
                school,
                email=school.first_admin_email,
                role=User.Role.SUPER_ADMIN,
                name=school.first_admin_name,
            )
    except Exception as exc:
        logger.exception("Provisioning %s failed", school.schema_name)
        with transaction.atomic():
            school = School.objects.select_for_update().get(pk=school_id)
            if school.status == School.Status.PROVISIONING:
                school.status = School.Status.FAILED
                school.provisioning_error = str(exc)[:2000]
                school.save(update_fields=["status", "provisioning_error"])
                _audit(school, "school_provisioning_failed", error=school.provisioning_error)
        return

    with transaction.atomic():
        school = School.objects.select_for_update().get(pk=school_id)
        if school.status != School.Status.PROVISIONING:
            return
        school.status = School.Status.ACTIVE
        school.was_ever_active = True
        school.provisioning_error = ""
        school.save(update_fields=["status", "was_ever_active", "provisioning_error"])
        _audit(school, "school_provisioned")


@shared_task(ignore_result=True)
def fail_stale_provisioning():
    """Mark ``failed`` any school whose provisioning worker died (beat, 10 min).

    A worker killed by the hard time limit or a deploy never reports back;
    after this, Retry works as usual.
    """
    cutoff = timezone.now() - STALE_PROVISIONING_AFTER
    with transaction.atomic():
        stale = School.objects.select_for_update(skip_locked=True).filter(
            status=School.Status.PROVISIONING, provisioning_started_at__lte=cutoff
        )
        for school in stale:
            school.status = School.Status.FAILED
            school.provisioning_error = STALE_PROVISIONING_ERROR
            school.save(update_fields=["status", "provisioning_error"])
            _audit(school, "school_provisioning_failed", error=STALE_PROVISIONING_ERROR)


@shared_task(ignore_result=True)
def close_expired_support_sessions():
    """Record the end of support sessions that ran out (beat, 10 min).

    Bookkeeping only: the token already stopped working at ``expires_at``
    (spec 0003, child 0006).
    """
    with transaction.atomic():
        expired = SupportSession.objects.select_for_update(skip_locked=True).filter(
            started_at__isnull=False,
            ended_at__isnull=True,
            expires_at__lt=timezone.now(),
        )
        for session in expired:
            session.ended_at = session.expires_at
            session.save(update_fields=["ended_at"])
            PlatformAuditLog.objects.create(
                admin_id=session.admin_id,
                school_id=session.school_id,
                action="support_ended",
                detail={"session_id": session.pk, "reason": "expired"},
            )


EXPORT_MAX_RETRIES = 3
# How long an export waits for a running job before looking again.
EXPORT_WAIT_SECONDS = 5 * 60
# Tables dropped per transaction when purging, under the 256 lock minimum.
PURGE_DROP_BATCH = 100


def _has_active_job(school):
    with schema_context(school.schema_name):
        from ems.api.views.jobs import fail_stale_jobs
        from ems.models import BackgroundJob

        # A killed worker's job would otherwise hold the export back forever.
        fail_stale_jobs()
        return BackgroundJob.objects.filter(status__in=("pending", "running")).exists()


@shared_task(bind=True, ignore_result=True, max_retries=EXPORT_MAX_RETRIES)
def export_school(self, school_id):
    """Dump a school marked for deletion into the export bucket.

    Waits while a job is still writing, so the dump never holds a half
    written run. Restored meanwhile: stops, and removes anything uploaded.
    """
    school = School.objects.get(pk=school_id)
    if school.status != School.Status.PENDING_DELETION or school.final_export_ref:
        return
    if _has_active_job(school):
        export_school.apply_async(args=(school_id,), countdown=EXPORT_WAIT_SECONDS)
        return

    try:
        key = exports.export_schema(school.schema_name)
    except Exception as exc:
        if self.request.retries >= EXPORT_MAX_RETRIES:
            logger.exception("Exporting %s failed", school.schema_name)
            _audit(school, "export_failed", error=str(exc)[:2000])
            return
        raise self.retry(exc=exc, countdown=60 * 2**self.request.retries)

    with transaction.atomic():
        school = School.objects.select_for_update().get(pk=school_id)
        if school.status == School.Status.PENDING_DELETION and not school.final_export_ref:
            school.final_export_ref = key
            school.save(update_fields=["final_export_ref"])
            _audit(school, "school_exported", key=key)
            return
    # Restored (or exported twice) while dumping: the bucket keeps nothing
    # it doesn't have to.
    exports.delete_export(key)


@shared_task(ignore_result=True)
def purge_schools():
    """Remove every school whose grace period ran out (beat, daily 02:00 UTC).

    Never drops a schema without a verified backup: the ``never_active``
    sentinel, or a non empty export object in the bucket.
    """
    due = School.objects.filter(
        status=School.Status.PENDING_DELETION, purge_after__lte=timezone.now()
    ).values_list("pk", flat=True)
    for school_id in list(due):
        try:
            _purge(school_id)
        except Exception:
            logger.exception("Purging school %s failed; trying again tomorrow", school_id)


def _purge(school_id):
    school = School.objects.get(pk=school_id)
    # Restore needs now < purge_after, so nothing can bring it back from here.
    if school.status != School.Status.PENDING_DELETION or school.purge_after > timezone.now():
        return
    if not exports.is_verified(school.final_export_ref):
        logger.error(
            "Not purging %s: no verified export (final_export_ref=%r)",
            school.schema_name,
            school.final_export_ref,
        )
        return

    school.drop_schema(batch_size=PURGE_DROP_BATCH)
    exports.delete_media(school.schema_name)
    with transaction.atomic():
        school = School.objects.select_for_update().get(pk=school_id)
        Domain.objects.filter(tenant=school).delete()
        school.status = School.Status.PURGED
        school.purged_at = timezone.now()
        school.save(update_fields=["status", "purged_at"])
        _audit(school, "school_purged", export=school.final_export_ref)
    # Last, so a failure here never leaves a school that can't pass the
    # backup check again. An object left behind is logged for cleanup.
    try:
        exports.delete_export(school.final_export_ref)
    except Exception:
        logger.exception(
            "Purged %s but could not delete its export %r",
            school.schema_name,
            school.final_export_ref,
        )
