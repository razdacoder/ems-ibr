"""Request side of tenancy: health checks, then picking the school by host."""
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
