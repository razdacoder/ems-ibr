import uuid
from datetime import datetime, timedelta

from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ems.api.exceptions import Conflict
from ems.api.permissions import IsAdminStaff, IsJobOwnerOrAdmin
from ems.api.serializers.job import BackgroundJobSerializer
from ems.api.views.constraints import get_or_create_constraints
from ems.api.views.system import _get_or_create_settings
from ems.models import (
    BackgroundJob,
    Class,
    Course,
    Department,
    Distribution,
    Faculty,
    Hall,
    SeatArrangement,
)


def _assert_generation_allowed() -> None:
    """Block generation until session/semester/constraints/excluded-days are set."""
    settings_row = _get_or_create_settings()
    if not (settings_row.session or "").strip() or not (
        settings_row.semester or ""
    ).strip():
        raise ValidationError(
            {
                "detail": (
                    "Academic session and semester must be set in System Settings "
                    "before generation."
                )
            }
        )

    constraints = get_or_create_constraints()
    if constraints.configured_at is None:
        raise ValidationError(
            {
                "detail": (
                    "Generation constraints have not been initialized. "
                    "Open Admin → Constraints and save once before generating."
                )
            }
        )
    if not constraints.excluded_weekdays:
        raise ValidationError(
            {
                "detail": (
                    "Configure at least one excluded weekday in Admin → "
                    "Constraints before generating."
                )
            }
        )

    # Every department must belong to a faculty so CBE auto-split can
    # bucket classes by faculty.
    deps_without_faculty = list(
        Department.objects.filter(faculty__isnull=True)
        .values_list("name", flat=True)
        .order_by("name")
    )
    if deps_without_faculty:
        sample = ", ".join(deps_without_faculty[:5])
        suffix = "…" if len(deps_without_faculty) > 5 else ""
        raise ValidationError(
            {
                "detail": (
                    "These departments have no faculty assigned: "
                    f"{sample}{suffix}. "
                    "Assign every department to a faculty in Admin → Faculties "
                    "before generating."
                )
            }
        )

    # Every faculty must be mapped to a CBE group in the constraints.
    faculty_groups = constraints.cbe_faculty_groups or {}
    unmapped = list(
        Faculty.objects.exclude(slug__in=faculty_groups.keys())
        .values_list("name", flat=True)
        .order_by("name")
    )
    if unmapped:
        sample = ", ".join(unmapped[:5])
        suffix = "…" if len(unmapped) > 5 else ""
        raise ValidationError(
            {
                "detail": (
                    "These faculties have no CBE group assigned: "
                    f"{sample}{suffix}. "
                    "Set a group for each faculty in Admin → Constraints."
                )
            }
        )


class JobViewSet(viewsets.ReadOnlyModelViewSet):
    """List and inspect background jobs.

    - Admins see every job; everyone else only their own.
    - Includes a custom ``destroy`` (admin only) and ``retry`` action.
    """

    serializer_class = BackgroundJobSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "job_id"
    lookup_value_regex = "[\\w-]+"

    def get_queryset(self):
        qs = BackgroundJob.objects.all().select_related("created_by")
        params = self.request.query_params
        if status_filter := params.get("status"):
            qs = qs.filter(status=status_filter)
        if job_type := params.get("job_type"):
            qs = qs.filter(job_type=job_type)
        if not self.request.user.is_staff:
            qs = qs.filter(created_by=self.request.user)
        return qs

    def get_permissions(self):
        if self.action in ("destroy", "retry"):
            return [IsAdminStaff()]
        return [IsAuthenticated()]

    def check_object_permissions(self, request, obj):
        super().check_object_permissions(request, obj)
        if self.action == "retrieve" and not IsJobOwnerOrAdmin().has_object_permission(
            request, self, obj
        ):
            self.permission_denied(request, message="Not your job.")

    @action(detail=True, methods=["delete"])
    def destroy_job(self, request, job_id=None):
        return self.destroy(request, job_id=job_id)

    def destroy(self, request, *args, **kwargs):
        job = self.get_object()
        if job.status == "running":
            raise Conflict("Refusing to delete a running job.")
        job.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def retry(self, request, job_id=None):
        job = self.get_object()
        if job.status != "failed":
            raise Conflict("Only failed jobs can be retried.")

        new_id = str(uuid.uuid4())
        new_job = BackgroundJob.objects.create(
            job_id=new_id,
            job_type=job.job_type,
            status="pending",
            created_by=request.user,
            params=job.params,
        )

        # Re-dispatch the matching Celery task with the original params.
        params = job.params or {}
        task = _TASK_MAP.get(job.job_type)
        if task:
            transaction.on_commit(
                lambda: task.apply_async(
                    args=_task_args(job.job_type, new_id, request.user.id, params)
                )
            )
        return Response({"job_id": new_job.job_id}, status=status.HTTP_202_ACCEPTED)


def _task_args(job_type, job_id, user_id, params):
    if job_type == "timetable":
        return [
            job_id,
            user_id,
            params.get("start_date"),
            params.get("end_date"),
        ]
    return [
        job_id,
        user_id,
        params.get("date"),
        params.get("period"),
    ]


# Lazy lookup so import order with celery is benign.
def _import_task(name):
    from ems import tasks

    return getattr(tasks, name)


class _TaskRegistry(dict):
    def __getitem__(self, key):
        return self.get(key)


_TASK_MAP = _TaskRegistry()


def _populate_task_map():
    if _TASK_MAP:
        return
    _TASK_MAP["timetable"] = _import_task("generate_timetable_task")
    _TASK_MAP["distribution"] = _import_task("generate_distribution_task")
    _TASK_MAP["allocation"] = _import_task("generate_allocation_task")


# Generate endpoints --------------------------------------------------------


class _BaseGenerateView(APIView):
    permission_classes = [IsAdminStaff]
    job_type: str = ""

    def _create_job(self, user, params):
        _populate_task_map()
        job_id = str(uuid.uuid4())
        BackgroundJob.objects.create(
            job_id=job_id,
            job_type=self.job_type,
            status="pending",
            created_by=user,
            params=params,
        )
        task = _TASK_MAP[self.job_type]
        transaction.on_commit(
            lambda: task.apply_async(
                args=_task_args(self.job_type, job_id, user.id, params)
            )
        )
        return job_id


class GenerateTimetableView(_BaseGenerateView):
    job_type = "timetable"

    def post(self, request):
        _assert_generation_allowed()
        start = request.data.get("start_date")
        end = request.data.get("end_date")
        if not start or not end:
            raise ValidationError(
                {"detail": "start_date and end_date are required."}
            )

        for resource_qs, message in (
            (Course.objects.exists(), "Cannot generate: no courses in the system."),
            (Class.objects.exists(), "Cannot generate: no classes in the system."),
            (Hall.objects.exists(), "Cannot generate: no halls in the system."),
        ):
            if not resource_qs:
                raise ValidationError({"detail": message})

        missing = Class.objects.filter(courses__isnull=True).select_related(
            "department"
        )
        if missing.exists():
            sample = ", ".join(
                f"{c.department.slug} {c.name}" for c in missing[:5]
            )
            extra = "…" if missing.count() > 5 else ""
            raise ValidationError(
                {
                    "detail": (
                        "Some classes have no courses assigned: "
                        f"{sample}{extra}. Upload class courses first."
                    )
                }
            )

        try:
            start_d = datetime.strptime(start, "%Y-%m-%d").date()
            end_d = datetime.strptime(end, "%Y-%m-%d").date()
        except ValueError:
            raise ValidationError(
                {"detail": "Dates must be in YYYY-MM-DD format."}
            )
        if start_d > end_d:
            raise ValidationError(
                {"detail": "End date must be on or after start date."}
            )

        # Use admin-configured excluded weekdays
        excluded = set(get_or_create_constraints().excluded_weekdays or [])
        days_available = 0
        cursor = start_d
        while cursor <= end_d:
            if cursor.weekday() not in excluded:
                days_available += 1
            cursor += timedelta(days=1)
        max_courses = max(
            (cls.courses.count() for cls in Class.objects.prefetch_related("courses")),
            default=0,
        )
        if days_available < max_courses:
            raise ValidationError(
                {
                    "detail": (
                        f"Selected range gives {days_available} usable days, "
                        f"but at least {max_courses} are needed."
                    )
                }
            )

        job_id = self._create_job(
            request.user, {"start_date": start, "end_date": end}
        )
        return Response({"job_id": job_id}, status=status.HTTP_202_ACCEPTED)


class GenerateDistributionView(_BaseGenerateView):
    job_type = "distribution"

    def post(self, request):
        _assert_generation_allowed()
        date = request.data.get("date")
        period = request.data.get("period")
        if not date or not period:
            raise ValidationError({"detail": "date and period are required."})
        if Distribution.objects.filter(date=date, period=period).exists():
            raise Conflict(
                f"A distribution for {date} ({period}) already exists. "
                "Clear it before regenerating."
            )
        job_id = self._create_job(request.user, {"date": date, "period": period})
        return Response({"job_id": job_id}, status=status.HTTP_202_ACCEPTED)


class GenerateAllocationView(_BaseGenerateView):
    job_type = "allocation"

    def post(self, request):
        _assert_generation_allowed()
        date = request.data.get("date")
        period = request.data.get("period")
        if not date or not period:
            raise ValidationError({"detail": "date and period are required."})
        if not Distribution.objects.filter(date=date, period=period).exists():
            raise ValidationError(
                {
                    "detail": (
                        f"No distribution exists for {date} ({period}). "
                        "Generate the distribution first."
                    )
                }
            )
        if SeatArrangement.objects.filter(date=date, period=period).exists():
            raise Conflict(
                f"Seat allocation for {date} ({period}) already exists."
            )
        job_id = self._create_job(request.user, {"date": date, "period": period})
        return Response({"job_id": job_id}, status=status.HTTP_202_ACCEPTED)


class ManualSeatAssignmentView(APIView):
    """POST /api/allocation/manual-assign/ — body: {seat_arrangement_id, seat_number}."""

    permission_classes = [IsAdminStaff]

    def post(self, request):
        sa_id = request.data.get("seat_arrangement_id")
        seat_number = request.data.get("seat_number")
        if sa_id is None or seat_number is None:
            raise ValidationError(
                {"detail": "seat_arrangement_id and seat_number are required."}
            )
        try:
            sa = SeatArrangement.objects.get(pk=sa_id)
        except SeatArrangement.DoesNotExist as exc:
            raise ValidationError(
                {"detail": "Seat arrangement record not found."}
            ) from exc

        if sa.seat_number is not None:
            raise Conflict("This student is already placed.")

        try:
            seat = int(seat_number)
        except (TypeError, ValueError):
            raise ValidationError({"detail": "seat_number must be an integer."})
        max_seats = (sa.hall.rows or 0) * (sa.hall.columns or 0)
        if seat < 1 or (max_seats and seat > max_seats):
            raise ValidationError(
                {"detail": f"Seat must be between 1 and {max_seats}."}
            )

        if SeatArrangement.objects.filter(
            date=sa.date,
            period=sa.period,
            hall=sa.hall,
            seat_number=seat,
        ).exists():
            raise Conflict(f"Seat {seat} is already occupied.")

        sa.seat_number = seat
        sa.save(update_fields=["seat_number"])
        return Response({"detail": "Seat assigned."})
