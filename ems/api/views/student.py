from rest_framework import permissions, status, viewsets
from rest_framework.response import Response

from ems.api.permissions import IsAdminStaff
from ems.api.serializers.student import (
    StudentSerializer,
    assert_student_deletable,
)
from ems.models import Student


class StudentViewSet(viewsets.ModelViewSet):
    serializer_class = StudentSerializer

    def get_queryset(self):
        qs = Student.objects.all().select_related("department", "level").order_by(
            "matric_no"
        )
        params = self.request.query_params
        if query := params.get("query"):
            qs = (
                qs.filter(first_name__icontains=query)
                | qs.filter(last_name__icontains=query)
                | qs.filter(matric_no__icontains=query)
            )
        if dept := params.get("department"):
            qs = qs.filter(department__slug=dept.upper())
        if class_id := params.get("class"):
            qs = qs.filter(level_id=class_id)
        user = self.request.user
        if user.is_authenticated and not user.is_staff and user.department_id:
            qs = qs.filter(department_id=user.department_id)
        return qs

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [permissions.IsAuthenticated()]
        return [IsAdminStaff()]

    def perform_destroy(self, instance):
        assert_student_deletable(instance)
        cls = instance.level
        instance.delete()
        if cls is not None:
            cls.size = Student.objects.filter(
                level=cls, department=cls.department
            ).count()
            cls.save(update_fields=["size"])

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
