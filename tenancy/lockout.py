"""Failed sign in counting, read straight from ``PlatformAuditLog``.

No cache: the default cache is per process memory, and the audit log already
holds every failure, so the count holds across processes (spec 0003, child
0003).
"""
from datetime import timedelta

from django.db.models import Max
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import APIException

WINDOW = timedelta(minutes=15)
MAX_PER_EMAIL = 5
MAX_PER_IP = 20
FAILURE_ACTIONS = ("login_failed", "totp_failed")
UNLOCKED = "unlocked"


class TooManyAttempts(APIException):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = "Too many attempts. Try again in 15 minutes."
    default_code = "too_many_attempts"


def check(email, ip):
    """Raise ``TooManyAttempts`` if this email or IP is locked out."""
    from tenancy.models import PlatformAuditLog

    since = timezone.now() - WINDOW
    recent = PlatformAuditLog.objects.filter(created_at__gte=since)
    failures = recent.filter(action__in=FAILURE_ACTIONS)

    # An Owner's unlock clears the email count; failures before it don't count.
    unlocked_at = recent.filter(action=UNLOCKED, detail__email=email).aggregate(
        at=Max("created_at")
    )["at"]
    by_email = failures.filter(detail__email=email)
    if unlocked_at:
        by_email = by_email.filter(created_at__gt=unlocked_at)
    if by_email.count() >= MAX_PER_EMAIL:
        raise TooManyAttempts()
    if ip and failures.filter(ip=ip).count() >= MAX_PER_IP:
        raise TooManyAttempts()
