"""ASGI config — HTTP via the standard Django app, WebSockets via Channels."""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

# IMPORTANT: build the HTTP app *before* importing anything that touches
# Django models. ``get_asgi_application`` runs ``django.setup()``, which is
# what populates the model registry. Imports below this line are safe.
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from channels.security.websocket import OriginValidator  # noqa: E402
from django.conf import settings  # noqa: E402

from ems.api.auth_ws import TokenAuthMiddleware  # noqa: E402
from ems.api.routing import websocket_urlpatterns  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        # The dashboard connects from its own origin (app.<domain>), so
        # accept the CORS origins as well as this service's own hosts.
        "websocket": OriginValidator(
            TokenAuthMiddleware(URLRouter(websocket_urlpatterns)),
            [*settings.ALLOWED_HOSTS, *settings.CORS_ALLOWED_ORIGINS],
        ),
    }
)
