"""Set password links for new platform admins (spec 0003, child 0003).

The link is signed over the admin's current, unusable password hash. Setting
a password changes the hash, so the link works once; resending sets a new
unusable hash, so only the newest link works. Valid for 48 hours.
"""
from django.conf import settings
from django.core import signing
from django.db import transaction
from rest_framework import status
from rest_framework.exceptions import APIException

from tenancy.models import PlatformAdmin
from tenancy.tasks import send_email

MAX_AGE = 48 * 60 * 60

_signer = signing.TimestampSigner(salt="tenancy.platform.invite")


class InviteGone(APIException):
    status_code = status.HTTP_410_GONE
    default_detail = "This invite link is no longer valid. Ask an Owner for a new one."
    default_code = "invite_gone"


def make_token(admin):
    return _signer.sign(f"{admin.pk}:{admin.password}")


def read_token(token):
    """The admin a still valid, unused link was made for, or 410."""
    try:
        value = _signer.unsign(token or "", max_age=MAX_AGE)
    except signing.BadSignature:  # includes SignatureExpired
        raise InviteGone()
    admin_id, _, password = value.partition(":")
    admin = PlatformAdmin.objects.filter(pk=admin_id, is_active=True).first()
    if admin is None or admin.has_usable_password() or admin.password != password:
        raise InviteGone()
    return admin


def accept_url(admin):
    host = f"admin.{settings.PLATFORM_BASE_DOMAIN}"
    return f"{settings.PLATFORM_URL_SCHEME}://{host}/accept?token={make_token(admin)}"


def send(admin):
    """Email ``admin`` a fresh link once the surrounding transaction commits."""
    context = {
        "name": admin.name,
        "role": admin.get_role_display(),
        "url": accept_url(admin),
    }
    transaction.on_commit(
        lambda: send_email.delay(
            admin.email, "Your Ordo console invite", "platform_admin_invite", context
        )
    )
