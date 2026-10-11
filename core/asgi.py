"""ASGI config — HTTP via the standard Django app, WebSockets via Channels."""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

# IMPORTANT: build the HTTP app *before* importing anything that touches
# Django models. ``get_asgi_application`` runs ``django.setup()``, which is
# what populates the model registry. Imports below this line are safe.
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402

from ems.api.auth_ws import TokenAuthMiddleware  # noqa: E402
from ems.api.routing import websocket_urlpatterns  # noqa: E402
from tenancy.ws import SchoolOriginValidator, SchoolScopeMiddleware  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        # The dashboard is served from the school's own host, so the origin
        # is any <slug>.<base>. The school comes from the Host header, before
        # the token is looked up in that school's schema.
        "websocket": SchoolOriginValidator(
            SchoolScopeMiddleware(
                TokenAuthMiddleware(URLRouter(websocket_urlpatterns))
            ),
        ),
    }
)
