from django.db.models import Count
from rest_framework import permissions, status, viewsets
from rest_framework.response import Response

from ems.api.permissions import IsDataOfficer
from ems.api.serializers.department import (
    DepartmentSerializer,
    assert_department_deletable,
)
from ems.models import Department


class DepartmentViewSet(viewsets.ModelViewSet):
    """CRUD for Department. Lookup is by slug to mirror existing URL patterns."""

    serializer_class = DepartmentSerializer
    lookup_field = "slug"
    lookup_value_regex = "[-A-Za-z0-9_]+"

    def get_queryset(self):
        qs = Department.objects.all().order_by("name")
        qs = qs.annotate(
            _class_count=Count("class_dep", distinct=True),
            _student_count=Count("student", distinct=True),
        )
        query = self.request.query_params.get("query")
        if query:
            qs = qs.filter(name__icontains=query) | qs.filter(slug__icontains=query)
        return qs

    def paginate_queryset(self, queryset):
        # Allow consumers (e.g. the faculty form picker) to fetch every
        # department in one request by passing ?all=true.
        all_param = self.request.query_params.get("all")
        if all_param and all_param.lower() in ("1", "true", "yes"):
            return None
        return super().paginate_queryset(queryset)

    def get_permissions(self):
        return [IsDataOfficer()]

    def perform_destroy(self, instance):
        assert_department_deletable(instance)
        instance.delete()

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
