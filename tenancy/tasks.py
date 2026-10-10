"""Platform background work: email, and building a school's schema.

Provisioning is queued from the public schema and stays there, entering the
new school's schema with ``schema_context`` (spec 0003, child 0004).
"""
import logging
from datetime import timedelta

from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone
from django_tenants.utils import schema_context

from tenancy.models import PlatformAuditLog, School

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
