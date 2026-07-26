"""Thin wrappers around the existing CSV/Excel/Word export functions.

DRF allows ``APIView.get`` to return a plain ``HttpResponse`` directly —
the renderer is bypassed, so the existing functions in ``ems.csv_gen`` and
``ems.broadsheet`` (which already build correct ``Content-Type`` and
``Content-Disposition`` headers) can be used as-is.
"""

from datetime import datetime

from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.views import APIView

from ems import csv_gen
from ems.models import SeatArrangement
from ems.views import (
    generate_attendance_sheets as legacy_generate_attendance_sheets,
    generate_broadsheet as legacy_generate_broadsheet,
)


class TimetableExportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return csv_gen.export_department_timetable(request)


class DistributionExportView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        return csv_gen.export_distribution(request)


class ArrangementExportView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        return csv_gen.export_arrangements(request)


class AttendanceSheetsView(APIView):
    # DRF's IsAdminUser checks ``is_staff``, which the user serializer sets to
    # ``bool(role)`` — i.e. every admin-side role (super admin, data officer,
    # faculty officer, exam committee) but not department officers, who have a
    # null role. That is exactly the intended audience for attendance sheets.
    permission_classes = [IsAdminUser]

    def get(self, request):
        params = request.query_params
        date = params.get("date")
        period = params.get("period")
        hall_id = params.get("hall_id")
        if not all([date, period, hall_id]):
            raise ValidationError(
                {"detail": "date, period, and hall_id are required."}
            )
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError as exc:
            raise ValidationError(
                {"detail": "date must be YYYY-MM-DD."}
            ) from exc

        # The legacy view answers every failure with messages.error() plus a
        # redirect to a template route. Over the API that 302 is followed by
        # the caller's blob request, so the HTML landing page was saved as
        # "attendance-<date>.zip" and the UI reported a successful download.
        # Do the same checks up front and fail loudly instead, so the legacy
        # function is only ever entered on a path that returns the real zip.
        placed = SeatArrangement.objects.filter(
            date=date, period=period, hall_id=hall_id, seat_number__isnull=False
        )
        if not placed.exists():
            if SeatArrangement.objects.filter(
                date=date, period=period, hall_id=hall_id
            ).exists():
                raise NotFound(
                    {"detail": "No students are seated in this hall for that slot."}
                )
            raise NotFound(
                {
                    "detail": "No seat allocation found for that hall, date, "
                    "and period. Generate the allocation first."
                }
            )
        return legacy_generate_attendance_sheets(request)


class BroadsheetView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        return legacy_generate_broadsheet(request)
