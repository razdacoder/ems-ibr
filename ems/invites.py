"""Invites to join a school: the first admin's, and staff invites.

The token is 32 random bytes; only its SHA-256 is stored and the raw token
lives in the emailed link alone. Invites last 7 days, and creating one
revokes any open invite for the same email first, so at most one is open
per email (spec 0003, child 0004). Runs inside the school's schema.
"""
import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import APIException

from ems.api.exceptions import Conflict
from ems.models import Invite, User

INVITE_TTL = timedelta(days=7)

USER_EXISTS = "A user with this email already exists."


class InviteGone(APIException):
    status_code = status.HTTP_410_GONE
    default_detail = (
        "This invite link is no longer valid. Ask your administrator for a new one."
    )
    default_code = "invite_gone"


def hash_token(token):
    return hashlib.sha256(token.encode()).hexdigest()


def open_invites():
    return Invite.objects.filter(accepted_at__isnull=True, revoked_at__isnull=True)


def user_exists(email):
    return User.objects.filter(email__iexact=email).exists()


def role_label(invite):
    if invite.role:
        return User.Role(invite.role).label
    if invite.department_id:
        return f"Department Officer, {invite.department.name}"
    return "Department Officer"


def invite_url(school, token):
    domain = school.get_primary_domain().domain
    return f"{settings.PLATFORM_URL_SCHEME}://{domain}/invite/{token}"


def invite(school, *, email, role, department=None, invited_by=None, name=""):
    """Create an invite and email it once the surrounding transaction commits.

    ``invited_by`` None means Ordo sent it: the first admin's invite. Any open
    invite for the same email is revoked first.
    """
    from tenancy.tasks import send_email

    email = email.strip().lower()
    token = secrets.token_urlsafe(32)
    now = timezone.now()
    with transaction.atomic():
        open_invites().filter(email=email).update(revoked_at=now)
        created = Invite.objects.create(
            email=email,
            role=role or None,
            department=department,
            invited_by=invited_by,
            token_hash=hash_token(token),
            expires_at=now + INVITE_TTL,
        )

    context = {
        "school_name": school.name,
        "name": name,
        "role": role_label(created),
        "url": invite_url(school, token),
        "days": INVITE_TTL.days,
    }
    if invited_by is None:
        template = "school_invite"
        subject = f"Set up {school.name} on Ordo"
    else:
        template = "staff_invite"
        subject = f"You're invited to {school.name} on Ordo"
        context["inviter"] = (
            f"{invited_by.first_name} {invited_by.last_name}".strip() or invited_by.email
        )
    transaction.on_commit(lambda: send_email.delay(email, subject, template, context))
    return created


def find(token, *, lock=False):
    """The open, unexpired invite this raw token names, or 410."""
    queryset = Invite.objects.select_related("department")
    if lock:
        queryset = queryset.select_for_update(of=("self",))
    found = queryset.filter(token_hash=hash_token(token or "")).first()
    if (
        found is None
        or found.accepted_at is not None
        or found.revoked_at is not None
        or found.expires_at <= timezone.now()
    ):
        raise InviteGone()
    return found


@transaction.atomic
def accept(token, *, first_name, last_name, password):
    """Create the invited user and sign them in. Returns ``(user, token key)``.

    The invite row stays locked until the user exists, so two submits of the
    same link can't both land.
    """
    found = find(token, lock=True)
    if user_exists(found.email):
        raise Conflict(USER_EXISTS)
    user = User(
        email=found.email,
        first_name=first_name,
        last_name=last_name,
        role=found.role,
        department=found.department,
        # Any admin side role is staff; a roleless user is a department officer.
        is_staff=bool(found.role),
    )
    try:
        validate_password(password, user=user)
    except DjangoValidationError as exc:
        raise serializers.ValidationError({"password": list(exc.messages)})
    user.set_password(password)
    user.save()
    found.accepted_at = timezone.now()
    found.save(update_fields=["accepted_at"])
    # ems.signals gives every new user a token; this is that one.
    token, _ = Token.objects.get_or_create(user=user)
    return user, token.key
