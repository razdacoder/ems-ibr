"""Token authentication for WebSocket connections.

Browsers cannot set arbitrary headers on the WebSocket constructor, so the
token is passed as a query-string parameter (``?token=<key>``). This
middleware parses that parameter and attaches the corresponding user to
``scope`` before the consumer accepts the connection.
"""

from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser


@database_sync_to_async
def _resolve(token_key: str | None):
    if not token_key:
        return AnonymousUser()
    # Imported lazily so AppRegistryNotReady is not a concern.
    from rest_framework.authtoken.models import Token

    try:
        return Token.objects.select_related("user").get(key=token_key).user
    except Token.DoesNotExist:
        return AnonymousUser()


class TokenAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        query_string = scope.get("query_string", b"").decode()
        params = parse_qs(query_string)
        token_key = (params.get("token") or [None])[0]
        scope["user"] = await _resolve(token_key)
        return await super().__call__(scope, receive, send)
