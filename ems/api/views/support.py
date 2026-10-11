"""Ordo support on the school host: redeem a console ticket, end the visit.

The ticket is the redeem call's only credential; ending needs the support
token itself (spec 0003, child 0006).
"""
from django.db import transaction
from rest_framework import serializers, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from tenancy import support


class _RedeemSerializer(serializers.Serializer):
    ticket = serializers.CharField(max_length=200)


class SupportRedeemView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = _RedeemSerializer(data=request.data)
        if not serializer.is_valid():
            raise support.TicketGone()
        session, token = support.redeem(request, serializer.validated_data["ticket"])
        return Response({"token": token.key, "expires_at": session.expires_at})


class SupportEndView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not request.user.is_support:
            raise PermissionDenied("Only an Ordo support session can be ended here.")
        with transaction.atomic():
            session = support.current_session(request.user, request.tenant)
            if session is not None:
                support.end(request, session)
            else:
                # Closed from the console a moment ago: the token still goes.
                request.auth.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
