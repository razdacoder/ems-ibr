"""Joining a school by invite (spec 0003, child 0004).

Super admins invite staff from the Users page. The emailed link opens
``/invite/<token>`` on the school's host, which reads the invite and accepts
it here without any sign in.
"""
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from ems import invites
from ems.api.exceptions import Conflict
from ems.api.pagination import DefaultPagination
from ems.api.permissions import IsSuperAdmin
from ems.api.serializers.invite import (
    AcceptInviteSerializer,
    CreateInviteSerializer,
    InviteSerializer,
)
from ems.api.serializers.user import DepartmentRefSerializer, UserSerializer
from tenancy import limits

JUST_INVITED = "This email was invited a moment ago. Refresh the list."


def _send(request, **fields):
    """Invite on behalf of the signed in admin; 409 if the email has a user."""
    if invites.user_exists(fields["email"]):
        raise Conflict(invites.USER_EXISTS)
    try:
        with transaction.atomic():
            # Open invites hold a seat too, except the one a resend replaces.
            limits.assert_can_add_staff(
                1, count_invites=True, except_email=fields["email"].strip().lower()
            )
            return invites.invite(request.tenant, invited_by=request.user, **fields)
    except IntegrityError:
        # Two admins inviting the same email at once: one open invite only.
        raise Conflict(JUST_INVITED)


class InviteListView(generics.ListAPIView):
    """Open invites (expired ones included, so they can be resent)."""

    permission_classes = [IsSuperAdmin]
    serializer_class = InviteSerializer
    pagination_class = DefaultPagination

    def get_queryset(self):
        return invites.open_invites().select_related("department", "invited_by")

    def post(self, request):
        serializer = CreateInviteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        created = _send(request, **serializer.validated_data)
        return Response(InviteSerializer(created).data, status=status.HTTP_201_CREATED)


class InviteRevokeView(APIView):
    permission_classes = [IsSuperAdmin]

    def post(self, request, pk):
        invite = get_object_or_404(invites.open_invites(), pk=pk)
        invite.revoked_at = timezone.now()
        invite.save(update_fields=["revoked_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class InviteResendView(APIView):
    """Replace an open invite with a fresh 7 day link; the old one stops working."""

    permission_classes = [IsSuperAdmin]

    def post(self, request, pk):
        invite = get_object_or_404(invites.open_invites(), pk=pk)
        created = _send(
            request, email=invite.email, role=invite.role, department=invite.department
        )
        return Response(InviteSerializer(created).data, status=status.HTTP_202_ACCEPTED)


class InviteTokenView(APIView):
    """No sign in: the token in the link is the credential."""

    permission_classes = [permissions.AllowAny]
    authentication_classes = []


class InviteDetailView(InviteTokenView):
    def get(self, request, token):
        invite = invites.find(token)
        return Response(
            {
                "school_name": request.tenant.name,
                "email": invite.email,
                "role": invite.role,
                "department": (
                    DepartmentRefSerializer(invite.department).data
                    if invite.department
                    else None
                ),
            }
        )


class InviteAcceptView(InviteTokenView):
    def post(self, request, token):
        serializer = AcceptInviteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user, key = invites.accept(token, **serializer.validated_data)
        return Response({"token": key, "user": UserSerializer(user).data})
