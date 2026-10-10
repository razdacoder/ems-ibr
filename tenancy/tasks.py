"""Platform background work, queued from the public schema."""
import logging

from celery import shared_task
from django.core.mail import send_mail

logger = logging.getLogger(__name__)

EMAIL_MAX_RETRIES = 3


@shared_task(bind=True, ignore_result=True, max_retries=EMAIL_MAX_RETRIES)
def send_email(self, to, subject, body):
    """Send one plain text email over SMTP, so no request waits on it.

    A failure is retried 3 times with backoff (1, 2, 4 minutes), then logged.
    Whatever link the email carried stays valid and can be resent.
    """
    try:
        send_mail(subject, body, None, [to])
    except Exception as exc:
        if self.request.retries >= EMAIL_MAX_RETRIES:
            logger.exception("Giving up emailing %r: %s", to, subject)
            return
        raise self.retry(exc=exc, countdown=60 * 2**self.request.retries)
