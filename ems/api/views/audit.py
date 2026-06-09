import csv
from datetime import datetime

from django.http import HttpResponse
from rest_framework import viewsets
from rest_framework.decorators import action

from ems.api.permissions import IsSuperAdmin
from ems.api.serializers.audit import AuditLogSerializer
from ems.models import AuditLog


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only system audit trail — super admins only.

    Filters (all optional, AND-combined):
      * ``query``       — substring match on action / email / path
      * ``user``        — user id
      * ``object_type`` — e.g. "user", "department"
      * ``status``      — "success" or "failed" (by recorded status code)
      * ``date_from`` / ``date_to`` — YYYY-MM-DD bounds on created_at
    """

    serializer_class = AuditLogSerializer
    permission_classes = [IsSuperAdmin]

    def get_queryset(self):
        qs = AuditLog.objects.all().select_related("user")
        params = self.request.query_params

        if query := params.get("query"):
            qs = (
                qs.filter(action__icontains=query)
                | qs.filter(user_email__icontains=query)
                | qs.filter(path__icontains=query)
            )
        if user_id := params.get("user"):
            qs = qs.filter(user_id=user_id)
        if object_type := params.get("object_type"):
            qs = qs.filter(object_type=object_type)
        if status_filter := params.get("status"):
            if status_filter == "success":
                qs = qs.filter(status_code__gte=200, status_code__lt=400)
            elif status_filter == "failed":
                qs = qs.exclude(status_code__gte=200, status_code__lt=400)
        if date_from := params.get("date_from"):
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to := params.get("date_to"):
            qs = qs.filter(created_at__date__lte=date_to)

        return qs

    @action(detail=False, methods=["get"], url_path="export")
    def export(self, request):
        """Stream the (filtered) trail as CSV."""
        rows = self.get_queryset()
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"audit-log-{timestamp}.csv"
        response = HttpResponse(
            content_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
        writer = csv.writer(response)
        writer.writerow(
            [
                "Timestamp",
                "User",
                "Email",
                "Action",
                "Method",
                "Path",
                "Object type",
                "Object id",
                "Status",
                "IP address",
            ]
        )
        for log in rows.iterator():
            user_name = ""
            if log.user_id and log.user:
                user_name = (
                    f"{log.user.first_name} {log.user.last_name}".strip()
                    or log.user.email
                )
            writer.writerow(
                [
                    log.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    user_name,
                    log.user_email,
                    log.action,
                    log.method,
                    log.path,
                    log.object_type,
                    log.object_id,
                    log.status_code if log.status_code is not None else "",
                    log.ip_address or "",
                ]
            )
        return response
