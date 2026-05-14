"""Read endpoints for timetable, distribution, allocation, hall allocation,
and distribution statistics. The generate/manual-assign endpoints live in
``jobs.py``; these are the corresponding GETs."""

from datetime import datetime

from django.db.models import Count, Q, Sum
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from django.db.models import Sum

from ems.models import (
    Class,
    Course,
    Distribution,
    GenerationConstraints,
    Hall,
    SeatArrangement,
    TimeTable,
)
from ems.utils import hall_effective_capacity


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


class TimetableEstimateView(APIView):
    """Estimate the minimum exam-window span needed to schedule every class
    without conflicts, given the current course catalog and constraints.

    Two binding constraints:

    1. Per-class load — a class can sit at most one exam per period (AM/PM).
       Given X AM courses + Y PM courses on the busiest class, you need at
       least max(X, Y) valid exam days.

    2. Hall seat throughput — total seat demand across all PBE courses must
       fit into (days × seats-per-period × utilization). Independent for AM
       and PM. When seat demand dominates, this is what causes most skips.

    The recommended day count is the max of both, plus a small buffer for
    conflict resolution.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        constraints = GenerationConstraints.objects.first()
        excluded_weekdays = set(
            (constraints.excluded_weekdays if constraints else None) or [6]
        )
        overrides_raw = (
            constraints.class_period_overrides if constraints else None
        ) or {}
        overrides = {
            (k or "").strip().lower(): (v or "").upper()
            for k, v in overrides_raw.items()
        }
        utilization = (
            float(constraints.pbe_hall_utilization) if constraints else 0.9
        )
        pattern = (
            constraints.seat_pattern if constraints else "checkerboard"
        )

        # ─── Per-class load (1 exam per class per period) ───────────────
        worst_am = worst_pm = worst_total = 0
        class_count = 0
        for cls in Class.objects.all().prefetch_related("courses").only("id", "name"):
            class_count += 1
            am = pm = 0
            key = (cls.name or "").strip().lower()
            default_period = overrides.get(key, "AM")
            for course in cls.courses.all():
                if course.exam_type == "CBE":
                    am += 1
                elif default_period == "PM":
                    pm += 1
                else:
                    am += 1
            worst_am = max(worst_am, am)
            worst_pm = max(worst_pm, pm)
            worst_total = max(worst_total, max(am, pm))

        # ─── Seat-throughput (PBE only; CBE is computer-based) ──────────
        # Use allocation-reachable seats for the active pattern so the
        # estimate matches what timetable and distribution will budget.
        total_effective_seats = sum(
            hall_effective_capacity(h.rows, h.columns, pattern)
            for h in Hall.objects.all().only("rows", "columns")
        )
        seats_per_period = int(total_effective_seats * utilization)

        am_seat_demand = pm_seat_demand = 0
        for course in (
            Course.objects.filter(exam_type="PBE")
            .prefetch_related("courses")
        ):
            seats = sum(cls.size for cls in course.courses.all())
            # split_course's logic: PM only if any class is mapped to PM;
            # else AM (default).
            period = "AM"
            for cls in course.courses.all():
                if overrides.get((cls.name or "").strip().lower()) == "PM":
                    period = "PM"
                    break
            if period == "PM":
                pm_seat_demand += seats
            else:
                am_seat_demand += seats

        def _ceil_div(a: int, b: int) -> int:
            return -(-a // b) if b else 0

        am_days_for_seats = _ceil_div(am_seat_demand, seats_per_period)
        pm_days_for_seats = _ceil_div(pm_seat_demand, seats_per_period)
        throughput_days = max(am_days_for_seats, pm_days_for_seats)

        min_exam_days = max(worst_total, throughput_days)
        recommended_exam_days = max(
            min_exam_days, int(round(min_exam_days * 1.2))
        )

        valid_per_week = max(1, 7 - len(excluded_weekdays))
        full_weeks = recommended_exam_days // valid_per_week
        remainder = recommended_exam_days % valid_per_week
        min_calendar_days = full_weeks * 7 + remainder

        # Surface which constraint dominates so the UI can explain the number.
        bottleneck = "per_class" if worst_total >= throughput_days else "seat_throughput"

        return Response(
            {
                "min_exam_days": min_exam_days,
                "recommended_exam_days": recommended_exam_days,
                "min_calendar_days": min_calendar_days,
                "min_calendar_weeks": (
                    round(min_calendar_days / 7, 1) if min_calendar_days else 0
                ),
                "excluded_weekdays": sorted(excluded_weekdays),
                "valid_exam_days_per_week": valid_per_week,
                "class_count": class_count,
                "worst_class_am": worst_am,
                "worst_class_pm": worst_pm,
                "per_class_min_days": worst_total,
                "throughput_min_days": throughput_days,
                "am_seat_demand": am_seat_demand,
                "pm_seat_demand": pm_seat_demand,
                "seats_per_period": seats_per_period,
                "bottleneck": bottleneck,
                "seat_pattern": pattern,
            }
        )


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
