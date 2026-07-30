from rest_framework import viewsets

from ems.api.pagination import AllowUnpaginatedMixin
from ems.api.permissions import IsAdminStaff, IsDataOfficer
from ems.api.serializers.hall import HallSerializer
from ems.models import Hall


class HallViewSet(AllowUnpaginatedMixin, viewsets.ModelViewSet):
    serializer_class = HallSerializer

    def get_permissions(self):
        # Managing halls stays with data officers, but every admin-side role
        # needs to *read* them: the exports page hall picker feeds the
        # attendance-sheet download, which is open to any staff role
        # (see AttendanceSheetsView). Without this, exam committee members
        # got a 403 on /halls/ and an empty, unusable dropdown.
        if self.action in ("list", "retrieve"):
            return [IsAdminStaff()]
        return [IsDataOfficer()]

    def get_queryset(self):
        qs = Hall.objects.all().order_by("name")
        if query := self.request.query_params.get("query"):
            qs = qs.filter(name__icontains=query)
        return qs
