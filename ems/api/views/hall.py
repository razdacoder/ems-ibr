from rest_framework import viewsets

from ems.api.permissions import IsAdminStaff
from ems.api.serializers.hall import HallSerializer
from ems.models import Hall


class HallViewSet(viewsets.ModelViewSet):
    serializer_class = HallSerializer
    permission_classes = [IsAdminStaff]

    def get_queryset(self):
        qs = Hall.objects.all().order_by("name")
        if query := self.request.query_params.get("query"):
            qs = qs.filter(name__icontains=query)
        return qs
