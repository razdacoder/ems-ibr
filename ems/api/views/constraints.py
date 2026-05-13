from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ems.api.permissions import IsAdminStaff
from ems.api.serializers.constraints import GenerationConstraintsSerializer
from ems.models import GenerationConstraints


def get_or_create_constraints() -> GenerationConstraints:
    obj = GenerationConstraints.objects.first()
    if not obj:
        obj = GenerationConstraints.objects.create()
    return obj


class GenerationConstraintsView(APIView):
    """Singleton resource for generation constraints.

    GET: any authenticated user (read-only).
    PATCH: admin only. Sets ``configured_at`` / ``configured_by`` on save.
    """

    def get_permissions(self):
        if self.request.method.upper() == "PATCH":
            return [IsAdminStaff()]
        return [IsAuthenticated()]

    def get(self, request):
        return Response(
            GenerationConstraintsSerializer(get_or_create_constraints()).data
        )

    def patch(self, request):
        instance = get_or_create_constraints()
        serializer = GenerationConstraintsSerializer(
            instance, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        instance.configured_at = timezone.now()
        instance.configured_by = request.user
        instance.save(update_fields=["configured_at", "configured_by"])
        return Response(
            GenerationConstraintsSerializer(instance).data
        )


