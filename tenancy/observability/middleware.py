"""Request side capture: the request id, per school counters (AC-7), and
unhandled exceptions in views (AC-1)."""
import re
import sys
import uuid

from django.core.signals import got_request_exception
from django.dispatch import receiver

from tenancy.observability import capture, counters

REQUEST_ID_HEADER = "X-Request-ID"
_REQUEST_ID = re.compile(r"^[0-9a-f]{32}$")


def _request_id(request):
    incoming = request.META.get("HTTP_X_REQUEST_ID", "").lower()
    return incoming if _REQUEST_ID.match(incoming) else uuid.uuid4().hex


def _school_id(request):
    from django_tenants.utils import get_public_schema_name

    tenant = getattr(request, "tenant", None)
    if tenant is None or tenant.schema_name == get_public_schema_name():
        return None
    return tenant.pk


class RequestObservabilityMiddleware:
    """Placed right after ``SchoolMiddleware``, so the school is known."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.ordo_request_id = _request_id(request)
        response = self.get_response(request)
        response[REQUEST_ID_HEADER] = request.ordo_request_id
        try:
            if capture.enabled() and request.path.startswith("/api/"):
                counts = {"requests": 1}
                if 400 <= response.status_code < 500:
                    counts["client_errors"] = 1
                counters.incr(_school_id(request), **counts)
        except Exception:
            capture.logger.exception("Counting a request failed")
        return response


def request_context(request):
    """The AC-8 request fields: method, route, user, role, support, id."""
    user = getattr(request, "user", None)
    signed_in = bool(user is not None and getattr(user, "is_authenticated", False))
    match = getattr(request, "resolver_match", None)
    return {
        "method": request.method,
        "route": (match.route if match and match.route else "<unresolved>"),
        "status": 500,
        "user_id": user.pk if signed_in else None,
        "role": getattr(user, "role", None) if signed_in else None,
        "support": (getattr(user, "support_expires_at", None) is not None) if signed_in else None,
        "request_id": getattr(request, "ordo_request_id", None),
    }


@receiver(got_request_exception, dispatch_uid="ordo_observability_request_exception")
def request_exception(sender, request=None, **kwargs):
    try:
        exc = sys.exc_info()[1]
        if exc is None or request is None:
            return
        context = request_context(request)
        capture.capture_exception(exc, "api", culprit=context["route"], **context)
    except Exception:
        capture.logger.exception("Capturing a request exception failed")
