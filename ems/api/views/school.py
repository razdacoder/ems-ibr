"""``GET /api/school/``: this school's plan, as the dashboard needs it.

The effective features and limits decide what the dashboard shows, and the
live counts drive the "N of M used" lines (spec 0003, child 0005).
"""
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ems.models import Student
from tenancy import limits


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
                # Support sessions arrive with build slice 10.
                "support": None,
            }
        )
