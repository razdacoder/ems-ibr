"""Token authentication for WebSocket connections.

Browsers cannot set arbitrary headers on the WebSocket constructor, so the
token is passed as a query-string parameter (``?token=<key>``). This
middleware parses that parameter and attaches the corresponding user to
``scope`` before the consumer accepts the connection. The token is looked
up in the socket's own school (``scope["school"]``, set by
``tenancy.ws.SchoolScopeMiddleware``), so a token from another school
finds nobody.
"""

from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser

from tenancy.ws import in_school


def _user_for(token_key: str):
    # Imported lazily so AppRegistryNotReady is not a concern.
    from rest_framework.authtoken.models import Token

    try:
        return Token.objects.select_related("user").get(key=token_key).user
    except Token.DoesNotExist:
        return AnonymousUser()


@database_sync_to_async
def _resolve(scope, token_key: str | None):
    if not token_key:
        return AnonymousUser()
    return in_school(scope, _user_for, token_key)


class TokenAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        query_string = scope.get("query_string", b"").decode()
        params = parse_qs(query_string)
        token_key = (params.get("token") or [None])[0]
        scope["user"] = await _resolve(scope, token_key)
        return await super().__call__(scope, receive, send)
