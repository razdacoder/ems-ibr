"""WebSocket side of tenancy: which school a socket belongs to.

Async consumer code runs on the event loop thread, where the connection is
on no school's schema. So the school is resolved once, at connect, into
``scope["school"]``, and every database call goes through :func:`in_school`
(spec 0003, child 0001).
"""
import re

from channels.db import database_sync_to_async
from channels.security.websocket import OriginValidator
from django.conf import settings
from django.http.request import split_domain_port
from django_tenants.utils import get_public_schema_name, schema_context

from tenancy.models import Domain, School

# Close code for an unknown or purged school, mirroring the HTTP 404.
CLOSE_SCHOOL_NOT_FOUND = 4404
# Close code for a school that isn't active, mirroring the API's refusal
# (403 school_suspended, 503 school_not_ready).
CLOSE_SCHOOL_CLOSED = 4403


def _host(scope):
    for name, value in scope.get("headers", []):
        if name == b"host":
            domain, _port = split_domain_port(value.decode("latin1").lower())
            return domain
    return ""


@database_sync_to_async
def _resolve_school(hostname):
    with schema_context(get_public_schema_name()):
        domain = (
            Domain.objects.select_related("tenant").filter(domain=hostname).first()
        )
    school = domain.tenant if domain else None
    if school is None or school.status == School.Status.PURGED:
        return None
    if school.schema_name == get_public_schema_name():
        return None
    return school


class SchoolScopeMiddleware:
    """Set ``scope["school"]`` from the Host header, or refuse the socket."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        school = await _resolve_school(_host(scope))
        refusal = None
        if school is None:
            refusal = CLOSE_SCHOOL_NOT_FOUND
        elif school.status != School.Status.ACTIVE:
            refusal = CLOSE_SCHOOL_CLOSED
        if refusal:
            # The handshake has to be read before it can be refused.
            await receive()
            await send({"type": "websocket.close", "code": refusal})
            return
        scope = dict(scope, school=school)
        return await self.app(scope, receive, send)


def in_school(scope, fn, *args, **kwargs):
    """Run ``fn`` in the socket's school schema, inside a sync function.

    Connections are per thread, so the switch happens in the same thread as
    the queries. Use it as ``await database_sync_to_async(in_school)(scope,
    fn)``.
    """
    with schema_context(scope["school"].schema_name):
        return fn(*args, **kwargs)


class SchoolOriginValidator(OriginValidator):
    """Accept any ``<slug>.<base>`` origin (``localhost`` ones in debug).

    Channels' own validator treats a leading dot as a wildcard only for bare
    hosts, not for full origins with a scheme and port.
    """

    def __init__(self, application):
        super().__init__(application, [])
        bases = [re.escape(settings.PLATFORM_BASE_DOMAIN)]
        if settings.DEBUG:
            bases.append("localhost")
        self.pattern = re.compile(
            rf"^https?://[a-z0-9-]+\.(?:{'|'.join(bases)})(?::\d+)?$"
        )

    def valid_origin(self, parsed_origin):
        if parsed_origin is None or not parsed_origin.hostname:
            return False
        origin = f"{parsed_origin.scheme}://{parsed_origin.netloc}".lower()
        return bool(self.pattern.match(origin))
