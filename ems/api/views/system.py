from django.db import transaction
from django.db.models import Count, Prefetch, Sum
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ems.api.permissions import IsSuperAdmin
from ems.api.serializers.system import SystemSettingsSerializer
from ems.models import (
    Class,
    Course,
    Department,
    Distribution,
    DistributionItem,
    Hall,
    SeatArrangement,
    Student,
    SystemSettings,
    TimeTable,
)


def _get_or_create_settings() -> SystemSettings:
    obj = SystemSettings.objects.first()
    if not obj:
        obj = SystemSettings.objects.create(
            session="2024/2025", semester="1st Semester"
        )
    return obj


class SystemSettingsView(APIView):
    """Singleton resource: GET returns the row, PATCH updates it.

    Accepts multipart/form-data so the institution logo can be uploaded
    alongside the other configuration fields.
    """

    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        if self.request.method.upper() == "PATCH":
            return [IsSuperAdmin()]
        return [IsAuthenticated()]

    def get(self, request):
        return Response(
            SystemSettingsSerializer(
                _get_or_create_settings(), context={"request": request}
            ).data
        )

    def patch(self, request):
        instance = _get_or_create_settings()
        serializer = SystemSettingsSerializer(
            instance,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class BrandingView(APIView):
    """Public institution branding for the UI (logo + names).

    Unauthenticated so the login screen can display the institution mark
    before a token exists. Exposes only non-sensitive branding fields.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        settings_obj = _get_or_create_settings()
        logo = settings_obj.logo
        logo_url = None
        if logo:
            logo_url = request.build_absolute_uri(logo.url)
        return Response(
            {
                "institution_name": settings_obj.institution_name,
                "institution_short_name": settings_obj.institution_short_name,
                "logo_url": logo_url,
                "brand_color": settings_obj.brand_color,
            }
        )


class DashboardStatsView(APIView):
    """Aggregated counts + shared-courses breakdown — drives the home page."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        settings = _get_or_create_settings()
        user = request.user

        if user.is_staff:
            departments_count = Department.objects.count()
            halls_count = Hall.objects.count()
            courses_count = Course.objects.count()
            classes_count = Class.objects.count()
            # Live uploaded student count (falls back to declared size when a
            # class has no students uploaded yet).
            students_total = Class.objects.total_effective_size()

            shared_qs = (
                Course.objects.annotate(
                    dept_count=Count("courses__department", distinct=True)
                )
                .filter(dept_count__gt=1)
                .prefetch_related(
                    Prefetch(
                        "courses",
                        queryset=Class.objects.select_related("department").only(
                            "id", "name", "department__name", "department_id"
                        ),
                        to_attr="prefetched_classes",
                    )
                )
                .order_by("-dept_count")
            )
            shared_courses = []
            for course in shared_qs:
                dept_map: dict[str, list[str]] = {}
                for cls in course.prefetched_classes:
                    dept_map.setdefault(cls.department.name, []).append(cls.name)
                shared_courses.append(
                    {
                        "code": course.code,
                        "name": course.name,
                        "dept_count": course.dept_count,
                        "departments": [
                            {"name": k, "classes": v} for k, v in dept_map.items()
                        ],
                    }
                )
        else:
            dept = user.department
            if dept:
                dept_classes = Class.objects.filter(department=dept)
                departments_count = 1
                halls_count = Hall.objects.count()
                courses_count = (
                    Course.objects.filter(courses__in=dept_classes).distinct().count()
                )
                classes_count = dept_classes.count()
                students_total = dept_classes.total_effective_size()
            else:
                departments_count = halls_count = courses_count = 0
                classes_count = students_total = 0
            shared_courses = []

        return Response(
            {
                "departments_count": departments_count,
                "halls_count": halls_count,
                "courses_count": courses_count,
                "classes_count": classes_count,
                "students_count": students_total,
                "shared_courses_count": len(shared_courses),
                "shared_courses": shared_courses,
                "settings": SystemSettingsSerializer(settings).data,
            }
        )


def _reset_allocation() -> None:
    """Clear seat allocations only."""
    SeatArrangement.objects.all().delete()


def _reset_distribution() -> None:
    """Clear distribution. Allocation depends on it, so clear that too."""
    _reset_allocation()
    Distribution.objects.all().delete()
    DistributionItem.objects.all().delete()


def _reset_timetable() -> None:
    """Clear the timetable. Distribution (and allocation) depend on it."""
    _reset_distribution()
    TimeTable.objects.all().delete()


def _reset_all() -> None:
    """Wipe everything, including departments, halls, courses and students."""
    _reset_timetable()
    Hall.objects.all().delete()
    Course.objects.all().delete()
    Class.objects.all().delete()
    Student.objects.all().delete()
    Department.objects.all().delete()


# scope -> (handler, whether it should unlock uploads, message)
_RESET_SCOPES = {
    "allocation": (_reset_allocation, False, "Seat allocations cleared."),
    "distribution": (
        _reset_distribution,
        False,
        "Distribution and seat allocations cleared.",
    ),
    "timetable": (
        _reset_timetable,
        True,
        "Timetable, distribution and seat allocations cleared.",
    ),
    "all": (_reset_all, True, "System reset complete."),
}


class ResetSystemView(APIView):
    permission_classes = [IsSuperAdmin]

    def post(self, request):
        scope = request.data.get("scope", "all")
        entry = _RESET_SCOPES.get(scope)
        if entry is None:
            return Response(
                {
                    "detail": (
                        f"Unknown reset scope '{scope}'. Expected one of: "
                        f"{', '.join(_RESET_SCOPES)}."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        handler, unlock_uploads, message = entry
        with transaction.atomic():
            handler()
            if unlock_uploads:
                settings = _get_or_create_settings()
                settings.has_timetable = False
                settings.save(update_fields=["has_timetable"])

        return Response({"detail": message})


class EnableBulkUploadView(APIView):
    permission_classes = [IsSuperAdmin]

    def post(self, request):
        settings = _get_or_create_settings()
        settings.has_timetable = False
        settings.save(update_fields=["has_timetable"])
        return Response({"detail": "Bulk upload enabled."})
