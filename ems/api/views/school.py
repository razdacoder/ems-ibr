"""``GET /api/school/``: this school's plan, as the dashboard needs it.

The effective features and limits decide what the dashboard shows, and the
live counts drive the "N of M used" lines (spec 0003, child 0005).
``GET /api/school/status/`` says whether the school is open at all, and is
the one call the status gate always lets through (child 0004).
"""
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ems.models import Student
from tenancy import limits, support


class SchoolView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        school = request.tenant
        effective = limits.effective(school)
        return Response(
            {
                "name": school.name,
                "slug": school.slug,
                "status": school.status,
                "timezone": school.timezone,
                "features": sorted(effective.features),
                "limits": {
                    "max_students": effective.max_students,
                    "max_staff_users": effective.max_staff_users,
                },
                "usage": {
                    "students": Student.objects.count(),
                    "staff_users": limits.staff_in_use(),
                },
                "support": _support(request),
            }
        )


def _support(request):
    """The banner's details, for an Ordo support token only (child 0006)."""
    session = support.current_session(request.user, request.tenant)
    if session is None:
        return None
    return {
        "active": True,
        "expires_at": request.user.support_expires_at,
        "admin_name": session.admin.name,
    }


class SchoolStatusView(APIView):
    """Name and status, for the suspended and "being set up" pages.

    No authentication, so a stale token can't turn it into a 401. The reason
    for a suspension stays in the console.
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        school = request.tenant
        return Response({"name": school.name, "status": school.status})
