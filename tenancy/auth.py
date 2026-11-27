"""Platform admin sessions: bearer tokens and the sign in challenge.

Platform tokens only work on the public urlconf (``console.<base>``), and
school tokens never work there: every platform view sets
``PlatformTokenAuthentication`` and nothing else (spec 0003, child 0003).
"""
import hashlib
import secrets
from datetime import timedelta

from django.core import signing
from django.utils import timezone
from rest_framework import status
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import APIException, AuthenticationFailed

from tenancy.models import PlatformAdmin, PlatformToken

PLATFORM_TOKEN_TTL = timedelta(hours=12)
# How stale a session's last_used_at may get before a request refreshes it.
TOUCH_EVERY = timedelta(minutes=5)
CHALLENGE_MAX_AGE = 300  # seconds between the password and the code
KEYWORD = b"bearer"

STEP_TOTP = "totp"
STEP_ENROLL = "enroll"

_challenge_signer = signing.TimestampSigner(salt="tenancy.platform.challenge")


class ChallengeExpired(APIException):
    status_code = status.HTTP_410_GONE
    default_detail = "This sign in has expired. Start again."
    default_code = "challenge_expired"


def hash_key(key):
    return hashlib.sha256(key.encode()).hexdigest()


def issue_token(admin, request=None):
    """Start a 12 hour session; returns ``(key, token)``. Only the hash is kept."""
    from tenancy.audit import request_ip

    key = secrets.token_urlsafe(32)
    now = timezone.now()
    token = PlatformToken.objects.create(
        key_hash=hash_key(key),
        admin=admin,
        expires_at=now + PLATFORM_TOKEN_TTL,
        user_agent=(request.META.get("HTTP_USER_AGENT", "") if request else "")[:255],
        ip=request_ip(request) if request else None,
        last_used_at=now,
    )
    admin.last_login = token.created_at
    admin.save(update_fields=["last_login"])
    return key, token


def make_challenge(admin, step):
    return _challenge_signer.sign(f"{admin.pk}:{step}")


def read_challenge(challenge, step):
    """The active admin a challenge was issued to, for this step, or 410."""
    try:
        value = _challenge_signer.unsign(challenge or "", max_age=CHALLENGE_MAX_AGE)
    except signing.BadSignature:  # includes SignatureExpired
        raise ChallengeExpired()
    admin_id, _, signed_step = value.partition(":")
    if signed_step != step:
        raise ChallengeExpired()
    admin = PlatformAdmin.objects.filter(pk=admin_id, is_active=True).first()
    if admin is None:
        raise ChallengeExpired()
    return admin


class PlatformTokenAuthentication(BaseAuthentication):
    """``Authorization: Bearer <key>``, checked against the stored hash."""

    def authenticate(self, request):
        parts = get_authorization_header(request).split()
        if not parts or parts[0].lower() != KEYWORD:
            return None
        if len(parts) != 2:
            raise AuthenticationFailed("Invalid token header.")
        try:
            key = parts[1].decode()
        except UnicodeError:
            raise AuthenticationFailed("Invalid token header.")

        token = (
            PlatformToken.objects.select_related("admin")
            .filter(key_hash=hash_key(key))
            .first()
        )
        if token is None:
            raise AuthenticationFailed("Invalid token.")
        if token.expires_at <= timezone.now():
            token.delete()
            raise AuthenticationFailed("Your session has expired. Sign in again.")
        if not token.admin.is_active:
            raise AuthenticationFailed("Invalid token.")
        now = timezone.now()
        if token.last_used_at is None or now - token.last_used_at > TOUCH_EVERY:
            PlatformToken.objects.filter(pk=token.pk).update(last_used_at=now)
            token.last_used_at = now
        return token.admin, token

    def authenticate_header(self, request):
        # Makes DRF answer 401 rather than 403 when no token is sent.
        return "Bearer"
