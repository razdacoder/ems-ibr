"""Read endpoints for timetable, distribution, allocation, hall allocation,
and distribution statistics. The generate/manual-assign endpoints live in
``jobs.py``; these are the corresponding GETs."""

from datetime import datetime

from django.db.models import Count, Q, Sum
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ems.models import (
    Distribution,
    Hall,
    SeatArrangement,
    TimeTable,
)


class TimetableListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        date = request.query_params.get("date")
        period = request.query_params.get("period")
        qs = TimeTable.objects.all().select_related("course", "class_obj__department")
        if date:
            qs = qs.filter(date=date)
        if period:
            qs = qs.filter(period=period)
        if not request.user.is_staff and request.user.department_id:
            qs = qs.filter(class_obj__department_id=request.user.department_id)
        rows = [
            {
                "id": t.id,
                "date": str(t.date),
                "period": t.period,
                "course": {"id": t.course_id, "code": t.course.code, "name": t.course.name},
                "class": {
                    "id": t.class_obj_id,
                    "name": t.class_obj.name,
                    "department": {
                        "id": t.class_obj.department_id,
                        "name": t.class_obj.department.name,
                        "slug": t.class_obj.department.slug,
                    },
                },
            }
            for t in qs.order_by("date", "period", "class_obj__department__name", "class_obj__name")
        ]
        return Response({"generated": TimeTable.objects.exists(), "results": rows})


class TimetableDatesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        dates = list(
            TimeTable.objects.values_list("date", flat=True).distinct().order_by("date")
        )
        return Response({"dates": [str(d) for d in dates]})


class DistributionListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        date = request.query_params.get("date")
        period = request.query_params.get("period")
        qs = Distribution.objects.all().select_related("hall")
        if date:
            qs = qs.filter(date=date)
        if period:
            qs = qs.filter(period=period)
        if not request.user.is_staff and request.user.department_id:
            qs = qs.filter(
                items__schedule__class_obj__department_id=request.user.department_id
            ).distinct()

        results = []
        for d in qs.prefetch_related("items__schedule__course", "items__schedule__class_obj__department"):
            results.append(
                {
                    "id": d.id,
                    "date": d.date,
                    "period": d.period,
                    "hall": {
                        "id": d.hall_id,
                        "name": d.hall.name,
                        "capacity": d.hall.capacity,
                    },
                    "items": [
                        {
                            "id": item.id,
                            "no_of_students": item.no_of_students,
                            "schedule": {
                                "id": item.schedule_id,
                                "course_code": item.schedule.course.code,
                                "course_name": item.schedule.course.name,
                                "class_name": item.schedule.class_obj.name,
                                "department_slug": item.schedule.class_obj.department.slug,
                            },
                        }
                        for item in d.items.all()
                    ],
                }
            )
        return Response(
            {"generated": Distribution.objects.exists(), "results": results}
        )


class DistributionStatisticsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        date = request.query_params.get("date")
        period = request.query_params.get("period")
        if not date or not period:
            return Response({"detail": "date and period are required."}, status=400)

        distributions = Distribution.objects.filter(date=date, period=period)
        agg = distributions.aggregate(
            total_halls=Count("id", distinct=True),
        )
        items_qs = (
            distributions.values_list("items__no_of_students", flat=True)
        )
        total_seats = sum(s or 0 for s in items_qs)
        return Response(
            {
                "date": date,
                "period": period,
                "halls_used": agg["total_halls"] or 0,
                "students_seated": total_seats,
            }
        )


class AllocationListView(APIView):
    """Aggregated by hall — drives the allocation summary page."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        date = request.query_params.get("date")
        period = request.query_params.get("period")
        qs = SeatArrangement.objects.all()
        if date:
            qs = qs.filter(date=date)
        if period:
            qs = qs.filter(period=period)
        if not request.user.is_staff and request.user.department_id:
            qs = qs.filter(cls__department_id=request.user.department_id)
        rows = (
            qs.values("hall_id", "hall__name", "date", "period")
            .annotate(
                placed=Count("id", filter=Q(seat_number__isnull=False)),
                not_placed=Count("id", filter=Q(seat_number__isnull=True)),
            )
            .order_by("hall__name")
        )
        return Response(
            {
                "generated": SeatArrangement.objects.exists(),
                "results": list(rows),
            }
        )


class HallAllocationView(APIView):
    """Full seat grid + placed/unplaced lists for one hall."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        date = request.query_params.get("date")
        period = request.query_params.get("period")
        hall_id = request.query_params.get("hall_id")
        if not all([date, period, hall_id]):
            return Response(
                {"detail": "date, period, and hall_id are required."},
                status=400,
            )
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            return Response(
                {"detail": "date must be in YYYY-MM-DD format."},
                status=400,
            )
        try:
            hall = Hall.objects.get(pk=hall_id)
        except (Hall.DoesNotExist, ValueError):
            return Response({"detail": "Hall not found."}, status=404)

        qs = SeatArrangement.objects.filter(
            date=date, period=period, hall_id=hall_id
        ).select_related("student", "course", "cls", "cls__department")
        if not request.user.is_staff and request.user.department_id:
            qs = qs.filter(cls__department_id=request.user.department_id)

        placed = []
        unplaced = []
        for sa in qs:
            row = {
                "id": sa.id,
                "seat_number": sa.seat_number,
                "course": {"id": sa.course_id, "code": sa.course.code},
                "class": {"id": sa.cls_id, "name": sa.cls.name},
                "student": (
                    {
                        "id": sa.student_id,
                        "matric_no": sa.student.matric_no,
                        "first_name": sa.student.first_name,
                        "last_name": sa.student.last_name,
                    }
                    if sa.student_id
                    else None
                ),
            }
            (placed if sa.seat_number is not None else unplaced).append(row)

        return Response(
            {
                "hall": {
                    "id": hall.id,
                    "name": hall.name,
                    "rows": hall.rows,
                    "columns": hall.columns,
                    "capacity": hall.capacity,
                },
                "date": date,
                "period": period,
                "placed": placed,
                "unplaced": unplaced,
            }
        )
