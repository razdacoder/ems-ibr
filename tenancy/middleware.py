"""Request side of tenancy: health checks, picking the school by host, and
refusing API calls while a school isn't open for use."""
from django.db import connection
from django.http import HttpResponse, HttpResponseNotFound, JsonResponse
from django.http.request import split_domain_port
from django.utils import timezone
from django_tenants.middleware.main import TenantMainMiddleware
from django_tenants.utils import get_public_schema_name

from tenancy.models import Domain, School

HEALTHZ_PATH = "/healthz"


class HealthzMiddleware:
    """Answer ``/healthz`` before anything reads the Host header.

    Proxies and platforms probe with whatever host they like, so this runs
    ahead of ``ALLOWED_HOSTS`` and never touches ``Domain``.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path != HEALTHZ_PATH:
            return self.get_response(request)
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
        except Exception:
            return HttpResponse("unavailable", status=503, content_type="text/plain")
        return HttpResponse("ok", content_type="text/plain")


def school_not_found(request):
    """Same answer for unknown and purged hosts, so nothing reveals which exist."""
    if request.path.startswith("/api/"):
        return JsonResponse({"detail": "School not found."}, status=404)
    return HttpResponseNotFound("School not found.", content_type="text/plain")


STATUS_PATH = "/api/school/status/"
BRANDING_PATH = "/api/system/branding/"
SUPPORT_REDEEM_PATH = "/api/support/redeem/"

SUSPENDED_DETAIL = "This school's access is suspended. Contact Ordo."
NOT_READY_DETAIL = "This school is still being set up."


def status_gate(request, school):
    """The refusal for a school that isn't ``active``, or None to go on.

    Only ``/api/*`` is gated. Celery tasks never pass through here, so a job
    already running finishes (spec 0003, child 0004).
    """
    if school.status == School.Status.ACTIVE or not request.path.startswith("/api/"):
        return None
    if request.method == "GET" and request.path == STATUS_PATH:
        return None
    if school.status in (School.Status.SUSPENDED, School.Status.PENDING_DELETION):
        # The schema is live, so the suspended page can stay branded.
        if request.method == "GET" and request.path == BRANDING_PATH:
            return None
        # Ordo support may still come in to help (spec 0003, child 0006).
        if (
            school.status == School.Status.SUSPENDED
            and request.method == "POST"
            and request.path == SUPPORT_REDEEM_PATH
        ):
            return None
        if _has_live_support_token(request):
            return None
        return JsonResponse(
            {"detail": SUSPENDED_DETAIL, "code": "school_suspended"}, status=403
        )
    # Provisioning or failed: there may be no tables to read yet.
    return JsonResponse({"detail": NOT_READY_DETAIL, "code": "school_not_ready"}, status=503)


def _has_live_support_token(request):
    """Whether the request carries an unexpired Ordo support token.

    The one place outside DRF that reads ``Authorization`` itself: DRF only
    authenticates inside the view, after this gate.
    """
    from rest_framework.authtoken.models import Token

    keyword, _, key = request.META.get("HTTP_AUTHORIZATION", "").partition(" ")
    if keyword != "Token" or not key.strip():
        return False
    return Token.objects.filter(
        key=key.strip(),
        user__is_active=True,
        user__support_expires_at__gt=timezone.now(),
    ).exists()


class SchoolMiddleware(TenantMainMiddleware):
    """Point the connection at the school the Host header names.

    A host outside ``ALLOWED_HOSTS`` raises ``DisallowedHost`` from
    ``get_host()``, which Django turns into a plain 400.
    """

    def __call__(self, request):
        try:
            return super().__call__(request)
        finally:
            # Daphne reuses threads for sync code: a zone must never carry over.
            timezone.deactivate()

    @staticmethod
    def hostname_from_request(request):
        domain, _port = split_domain_port(request.get_host())
        return domain

    def process_request(self, request):
        connection.set_schema_to_public()
        hostname = self.hostname_from_request(request)
        domain = (
            Domain.objects.select_related("tenant").filter(domain=hostname).first()
        )
        school = domain.tenant if domain else None
        if school is None or school.status == School.Status.PURGED:
            return school_not_found(request)

        school.domain_url = hostname
        request.tenant = school
        connection.set_tenant(school)
        self.setup_url_routing(request)
        if school.schema_name != get_public_schema_name():
            timezone.activate(school.timezone)
            return status_gate(request, school)
