from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from ems import upload_handlers
from ems.api.permissions import IsAdminStaff, UploadsUnlocked
from ems.models import Class, Department


class _BaseUploadView(APIView):
    permission_classes = [IsAdminStaff, UploadsUnlocked]
    parser_classes = [MultiPartParser, FormParser]

    handler_attr: str = ""

    def _file(self, request):
        f = request.FILES.get("file")
        if not f:
            return Response(
                {"detail": "No file uploaded — attach a CSV under the 'file' field."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return f


class DepartmentUploadView(_BaseUploadView):
    def post(self, request):
        f = self._file(request)
        if isinstance(f, Response):
            return f
        try:
            result = upload_handlers.upload_departments(f)
        except upload_handlers.UploadError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)


class HallUploadView(_BaseUploadView):
    def post(self, request):
        f = self._file(request)
        if isinstance(f, Response):
            return f
        try:
            result = upload_handlers.upload_halls(f)
        except upload_handlers.UploadError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)


class CourseUploadView(_BaseUploadView):
    def post(self, request):
        f = self._file(request)
        if isinstance(f, Response):
            return f
        try:
            result = upload_handlers.upload_courses(f)
        except upload_handlers.UploadError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)


class ClassesForDepartmentUploadView(_BaseUploadView):
    def post(self, request, dept_slug):
        department = get_object_or_404(Department, slug=dept_slug)
        f = self._file(request)
        if isinstance(f, Response):
            return f
        try:
            result = upload_handlers.upload_classes_for_department(f, department)
        except upload_handlers.UploadError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)


class ClassCoursesUploadView(_BaseUploadView):
    def post(self, request, class_id):
        cls = get_object_or_404(Class, pk=class_id)
        f = self._file(request)
        if isinstance(f, Response):
            return f
        try:
            result = upload_handlers.upload_class_courses(f, cls)
        except upload_handlers.UploadError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)


class ClassStudentsUploadView(_BaseUploadView):
    def post(self, request, class_id):
        cls = get_object_or_404(Class, pk=class_id)
        f = self._file(request)
        if isinstance(f, Response):
            return f
        try:
            result = upload_handlers.upload_class_students(f, cls)
        except upload_handlers.UploadError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)


class BulkUploadView(_BaseUploadView):
    """POST /api/uploads/bulk/ with `upload_type` field selecting the dispatcher."""

    def post(self, request):
        f = self._file(request)
        if isinstance(f, Response):
            return f
        upload_type = request.data.get("upload_type", "").strip()
        handler = upload_handlers.BULK_HANDLERS.get(upload_type)
        if not handler:
            return Response(
                {
                    "detail": (
                        "upload_type must be one of: "
                        + ", ".join(sorted(upload_handlers.BULK_HANDLERS))
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            result = handler(f)
        except upload_handlers.UploadError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"upload_type": upload_type, **result})
