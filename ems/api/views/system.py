from django.db.models import Count, Prefetch, Sum
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ems.api.permissions import IsAdminStaff
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
    """Singleton resource: GET returns the row, PATCH updates it."""

    def get_permissions(self):
        if self.request.method.upper() == "PATCH":
            return [IsAdminStaff()]
        return [IsAuthenticated()]

    def get(self, request):
        return Response(SystemSettingsSerializer(_get_or_create_settings()).data)

    def patch(self, request):
        instance = _get_or_create_settings()
        serializer = SystemSettingsSerializer(
            instance, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


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
            students_total = (
                Class.objects.aggregate(total=Sum("size"))["total"] or 0
            )

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
                students_total = (
                    dept_classes.aggregate(total=Sum("size"))["total"] or 0
                )
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


class ResetSystemView(APIView):
    permission_classes = [IsAdminStaff]

    def post(self, request):
        SeatArrangement.objects.all().delete()
        Distribution.objects.all().delete()
        DistributionItem.objects.all().delete()
        TimeTable.objects.all().delete()
        Hall.objects.all().delete()
        Course.objects.all().delete()
        Class.objects.all().delete()
        Student.objects.all().delete()
        Department.objects.all().delete()

        settings = _get_or_create_settings()
        settings.has_timetable = False
        settings.save(update_fields=["has_timetable"])
        return Response({"detail": "System reset complete."})


class EnableBulkUploadView(APIView):
    permission_classes = [IsAdminStaff]

    def post(self, request):
        settings = _get_or_create_settings()
        settings.has_timetable = False
        settings.save(update_fields=["has_timetable"])
        return Response({"detail": "Bulk upload enabled."})
