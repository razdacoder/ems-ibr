"""Hall Directory + VISA preview (JSON) and export (PDF) endpoints."""

from datetime import datetime

from django.http import HttpResponse
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ems import directory, pdf_gen
from ems.api.views.system import _get_or_create_settings

_DOC_CHOICES = {"hall", "visa"}
_SCOPE_CHOICES = {"slot", "week", "duration"}


def _parse_params(request):
    doc = (request.GET.get("doc") or "hall").lower()
    scope = (request.GET.get("scope") or "slot").lower()
    period = (request.GET.get("period") or "AM").upper()
    if doc not in _DOC_CHOICES:
        raise ValidationError({"detail": "doc must be 'hall' or 'visa'."})
    if scope not in _SCOPE_CHOICES:
        raise ValidationError(
            {"detail": "scope must be 'slot', 'week', or 'duration'."}
        )
    if period not in ("AM", "PM"):
        raise ValidationError({"detail": "period must be 'AM' or 'PM'."})

    date_obj = None
    date_str = request.GET.get("date")
    if date_str and date_str != "None":
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError as exc:
            raise ValidationError({"detail": "date must be YYYY-MM-DD."}) from exc
    if scope in ("slot", "week") and not date_obj:
        raise ValidationError(
            {"detail": "date is required for 'slot' and 'week' scope."}
        )
    return doc, scope, date_obj, period


class DirectoryPreviewView(APIView):
    """JSON preview of the Hall Directory / VISA for the chosen scope."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        doc, scope, date_obj, period = _parse_params(request)
        slots = directory.build_payload(doc, scope, date_obj, period)
        return Response({"doc": doc, "scope": scope, "slots": slots})


class DirectoryExportView(APIView):
    """PDF export of the Hall Directory / VISA for the chosen scope."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        doc, scope, date_obj, period = _parse_params(request)
        payload = directory.build_payload(doc, scope, date_obj, period)
        pdf_bytes = pdf_gen.build_pdf(doc, payload, _get_or_create_settings())
        label = "hall-directory" if doc == "hall" else "visa"
        filename = f"{label}-{scope}.pdf"
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
