from rest_framework import permissions, viewsets

from ems.api.permissions import IsAdminStaff
from ems.api.serializers.hall import HallSerializer
from ems.models import Hall


class HallViewSet(viewsets.ModelViewSet):
    serializer_class = HallSerializer

    def get_queryset(self):
        qs = Hall.objects.all().order_by("name")
        if query := self.request.query_params.get("query"):
            qs = qs.filter(name__icontains=query)
        return qs

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [permissions.IsAuthenticated()]
        return [IsAdminStaff()]
