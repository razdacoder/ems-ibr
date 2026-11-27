"""Emails to the Ordo team when something on the platform needs a person.

Sent to ``PLATFORM_ALERT_EMAILS`` when set, otherwise to every active Owner
who has accepted their invite. Alerts never raise: a failed alert is logged
and the work that triggered it carries on.
"""
import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def recipients():
    if settings.PLATFORM_ALERT_EMAILS:
        return list(settings.PLATFORM_ALERT_EMAILS)
    from tenancy.models import PlatformAdmin

    owners = PlatformAdmin.objects.filter(role=PlatformAdmin.Role.OWNER, is_active=True)
    return [o.email for o in owners if o.has_usable_password()]


def console_url(path=""):
    host = f"{settings.PLATFORM_CONSOLE_SUBDOMAIN}.{settings.PLATFORM_BASE_DOMAIN}"
    return f"{settings.PLATFORM_URL_SCHEME}://{host}/console{path}"


def send(headline, lines, path="", *, now=False):
    """Email every recipient. Queued after commit, or sent here with ``now``
    (the backup service has no worker to queue to)."""
    try:
        to = recipients()
        if not to:
            logger.warning("No one to send the alert %r to.", headline)
            return
        context = {"headline": headline, "lines": lines, "url": console_url(path)}
        subject = f"[Ordo] {headline}"
        if now:
            text = render_to_string("emails/platform_alert.txt", context)
            html = render_to_string("emails/platform_alert.html", context)
            message = EmailMultiAlternatives(subject, text, None, to)
            message.attach_alternative(html, "text/html")
            message.send()
            return
        from tenancy.tasks import send_email

        def queue():
            for address in to:
                send_email.delay(address, subject, "platform_alert", context)

        transaction.on_commit(queue)
    except Exception:
        logger.exception("Could not send the alert %r.", headline)


def school_setup_failed(school, error):
    send(
        f"Setting up {school.name} failed",
        [f"School: {school.name} ({school.slug})", f"Error: {error[:500]}", "Retry it from the school's page."],
        f"/schools/{school.pk}",
    )


def export_failed(school, error):
    send(
        f"The pre-deletion backup of {school.name} failed",
        [
            f"School: {school.name} ({school.slug})",
            f"Error: {error[:500]}",
            "The school won't be purged without a backup. Check the export bucket, then restore and delete it again.",
        ],
        f"/schools/{school.pk}",
    )


def backup_failed(error, next_try):
    send(
        "The nightly database backup failed",
        [
            f"Error: {error[-500:]}",
            f"Retries are used up. The next scheduled run is {next_try:%Y-%m-%d %H:%M} UTC.",
            "Until then the newest backup is older than a day.",
        ],
        now=True,
    )


def renewals_due(schools, today):
    lines = []
    for school in schools:
        days = (school.renews_on - today).days
        when = (
            "renews today" if days == 0
            else f"lapsed {-days} day{'s' if days != -1 else ''} ago" if days < 0
            else f"renews in {days} day{'s' if days != 1 else ''}"
        )
        lines.append(f"{school.name} ({school.slug}) {when}, on {school.renews_on:%d %b %Y}")
    send(f"{len(lines)} school plan{'s' if len(lines) != 1 else ''} up for renewal", lines)
