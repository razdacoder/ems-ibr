"""Authenticator app codes for platform admins (spec 0003, child 0003).

Secrets are stored Fernet encrypted under ``PLATFORM_TOTP_KEY``. A code is
accepted one 30 second step either side of now, and only for a step later
than the last one used, so a code can't be replayed.
"""
import hmac

import pyotp
from cryptography.fernet import Fernet
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db.models import Q
from django.utils import timezone

ISSUER = "Ordo"
VALID_WINDOW = 1


def _fernet():
    if not settings.PLATFORM_TOTP_KEY:
        raise ImproperlyConfigured("PLATFORM_TOTP_KEY must be set.")
    return Fernet(settings.PLATFORM_TOTP_KEY)


def new_secret(admin):
    """Give ``admin`` a fresh unconfirmed secret; returns the otpauth URI."""
    secret = pyotp.random_base32()
    admin.totp_secret = _fernet().encrypt(secret.encode()).decode()
    admin.totp_confirmed_at = None
    admin.totp_last_step = None
    admin.save(update_fields=["totp_secret", "totp_confirmed_at", "totp_last_step"])
    return pyotp.TOTP(secret, issuer=ISSUER).provisioning_uri(
        admin.email, issuer_name=ISSUER
    )


def clear(admin):
    admin.totp_secret = ""
    admin.totp_confirmed_at = None
    admin.totp_last_step = None
    admin.save(update_fields=["totp_secret", "totp_confirmed_at", "totp_last_step"])


def _matching_step(secret, code):
    totp = pyotp.TOTP(secret, issuer=ISSUER)
    now = totp.timecode(timezone.now())
    for step in range(now - VALID_WINDOW, now + VALID_WINDOW + 1):
        if hmac.compare_digest(totp.generate_otp(step), code):
            return step
    return None


def verify(admin, code):
    """Check ``code`` and use it up. False for a wrong code or a replay.

    The step is claimed with a conditional update, so two requests racing
    with the same code can't both win.
    """
    code = (code or "").strip().replace(" ", "")
    if not admin.totp_secret or not code.isdigit():
        return False
    secret = _fernet().decrypt(admin.totp_secret.encode()).decode()
    step = _matching_step(secret, code)
    if step is None:
        return False
    claimed = (
        type(admin)
        .objects.filter(pk=admin.pk)
        .filter(Q(totp_last_step__isnull=True) | Q(totp_last_step__lt=step))
        .update(totp_last_step=step)
    )
    if not claimed:
        return False
    admin.totp_last_step = step
    return True


def pending_secret(admin):
    """A fresh secret for re-enrolling, not saved yet; returns ``(secret, uri)``.

    The admin's current secret keeps working until ``confirm`` succeeds, so
    abandoning the setup halfway never weakens their sign in.
    """
    secret = pyotp.random_base32()
    uri = pyotp.TOTP(secret, issuer=ISSUER).provisioning_uri(admin.email, issuer_name=ISSUER)
    return secret, uri


def seal(secret):
    return _fernet().encrypt(secret.encode()).decode()


def unseal(sealed):
    return _fernet().decrypt(sealed.encode()).decode()


def confirm(admin, secret, code):
    """Make ``secret`` the admin's if ``code`` matches it. False otherwise."""
    code = (code or "").strip().replace(" ", "")
    if not code.isdigit():
        return False
    step = _matching_step(secret, code)
    if step is None:
        return False
    admin.totp_secret = seal(secret)
    admin.totp_confirmed_at = timezone.now()
    admin.totp_last_step = step
    admin.save(update_fields=["totp_secret", "totp_confirmed_at", "totp_last_step"])
    return True
