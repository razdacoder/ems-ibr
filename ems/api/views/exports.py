"""Thin wrappers around the existing CSV/Excel/Word export functions.

DRF allows ``APIView.get`` to return a plain ``HttpResponse`` directly —
the renderer is bypassed, so the existing functions in ``ems.csv_gen`` and
``ems.broadsheet`` (which already build correct ``Content-Type`` and
``Content-Disposition`` headers) can be used as-is.
"""

from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.views import APIView

from ems import csv_gen
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
    permission_classes = [IsAdminUser]

    def get(self, request):
        params = request.query_params
        if not all([params.get("date"), params.get("period"), params.get("hall_id")]):
            raise ValidationError(
                {"detail": "date, period, and hall_id are required."}
            )
        return legacy_generate_attendance_sheets(request)


class BroadsheetView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        return legacy_generate_broadsheet(request)
