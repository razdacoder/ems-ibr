"""School token authentication: DRF's token, plus the support cut off.

An Ordo support user's token stops working the moment its
``support_expires_at`` passes, with no sweeper in between
(spec 0003, child 0006). ``auth_ws`` applies the same rule to sockets.
"""
from django.utils import timezone
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed

from ems.api.exceptions import CodedAPIException


class SupportExpired(CodedAPIException, AuthenticationFailed):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = "This Ordo support session has ended."
    default_code = "support_expired"


def support_expired(user):
    expires = getattr(user, "support_expires_at", None)
    return expires is not None and expires <= timezone.now()


class SchoolTokenAuthentication(TokenAuthentication):
    def authenticate_credentials(self, key):
        user, token = super().authenticate_credentials(key)
        if support_expired(user):
            raise SupportExpired()
        return user, token
