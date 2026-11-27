"""Console tools beyond the school lifecycle: backup health, usage history,
staff search, the schools CSV and announcements (spec 0003 follow-ups).

All of it reads the public schema; nothing here enters a school's schema.
"""
import csv
from datetime import timedelta

from django.conf import settings
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.response import Response

from tenancy import audit, limits
from tenancy.models import Announcement, BackupRun, StaffDirectoryEntry, UsageSnapshot
from tenancy.permissions import IsPlatformOwner, IsPlatformStaff
from tenancy.views import PlatformView

# The backup container calls itself unhealthy past this (deploy/compose.prod.yml).
BACKUP_STALE_AFTER = timedelta(hours=26)
USAGE_MAX_DAYS = 400
STAFF_SEARCH_MIN = 3
STAFF_SEARCH_LIMIT = 50


def backup_summary(now):
    """Health of the nightly backup for the dashboard."""
    recent = list(BackupRun.objects.all()[:14])
    last_ok = next((r for r in recent if r.ok), None) or BackupRun.objects.filter(ok=True).first()
    return {
        "configured": bool(settings.BACKUP_BUCKET),
        "stale": last_ok is None or now - last_ok.started_at > BACKUP_STALE_AFTER,
        "last_success": last_ok and {
            "started_at": last_ok.started_at,
            "size_bytes": last_ok.size_bytes,
            "key": last_ok.key,
        },
        "last_run": recent[0] and {
            "started_at": recent[0].started_at,
            "ok": recent[0].ok,
            "error": recent[0].error[-300:],
        } if recent else None,
        "recent": [
            {"started_at": r.started_at, "ok": r.ok, "size_bytes": r.size_bytes}
            for r in reversed(recent)
        ],
    }


class SchoolUsageView(PlatformView):
    """A school's nightly snapshots, oldest first, and its effective limits."""

    def get(self, request, pk):
        from tenancy.school_views import schools

        school = get_object_or_404(schools(), pk=pk)
        try:
            days = min(max(int(request.query_params.get("days", 90)), 7), USAGE_MAX_DAYS)
        except ValueError:
            days = 90
        since = timezone.now().date() - timedelta(days=days)
        snapshots = UsageSnapshot.objects.filter(school=school, taken_on__gt=since).order_by("taken_on")
        effective = limits.effective(school)
        return Response(
            {
                "limits": {
                    "max_students": effective.max_students,
                    "max_staff_users": effective.max_staff_users,
                },
                "snapshots": [
                    {
                        "date": s.taken_on,
                        "students": s.students,
                        "staff_users": s.staff_users,
                        "jobs": s.jobs_last_24h,
                        "last_activity_at": s.last_activity_at,
                    }
                    for s in snapshots
                ],
            }
        )


class StaffSearchView(PlatformView):
    """Which school a staff email belongs to, from last night's index."""

    def get(self, request):
        q = request.query_params.get("q", "").strip()
        if len(q) < STAFF_SEARCH_MIN:
            return Response(
                {"detail": f"Type at least {STAFF_SEARCH_MIN} characters."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        entries = (
            StaffDirectoryEntry.objects.filter(Q(email__icontains=q) | Q(name__icontains=q))
            .select_related("school")
            .order_by("email", "school__name")[:STAFF_SEARCH_LIMIT]
        )
        return Response(
            {
                "indexed_at": StaffDirectoryEntry.objects.order_by("-indexed_at")
                .values_list("indexed_at", flat=True)
                .first(),
                "results": [
                    {
                        "email": e.email,
                        "name": e.name,
                        "role": e.role,
                        "is_active": e.is_active,
                        "last_login": e.last_login,
                        "school": {
                            "id": e.school.id,
                            "name": e.school.name,
                            "slug": e.school.slug,
                            "status": e.school.status,
                        },
                    }
                    for e in entries
                ],
            }
        )


class StaffReindexView(PlatformView):
    """Rebuild the staff index now rather than waiting for the night."""

    def post(self, request):
        from tenancy.tasks import index_staff

        index_staff.delay()
        audit.record(request, "staff_reindex_requested")
        return Response(status=status.HTTP_202_ACCEPTED)


CSV_COLUMNS = [
    "name", "slug", "status", "plan", "domain", "country", "contact_name",
    "contact_email", "plan_started_on", "renews_on", "students", "staff_users",
    "jobs_last_24h", "last_activity_at", "usage_taken_on", "created_at",
]


class SchoolExportView(PlatformView):
    """Every school as CSV, with its latest usage, for finance."""

    def get(self, request):
        from tenancy.school_views import SchoolListView

        listing = SchoolListView()
        listing.request = request
        listing.format_kwarg = None
        rows = listing.get_queryset()

        response = HttpResponse(content_type="text/csv; charset=utf-8")
        stamp = timezone.now().strftime("%Y%m%d")
        response["Content-Disposition"] = f'attachment; filename="ordo-schools-{stamp}.csv"'
        writer = csv.writer(response)
        writer.writerow(CSV_COLUMNS)
        for school in rows:
            usage = school.latest_usage[0] if school.latest_usage else None
            domain = next((d.domain for d in school.domains.all() if d.is_primary), "")
            writer.writerow([
                _cell(school.name), school.slug, school.status, school.plan.name, domain,
                school.country, _cell(school.contact_name), school.contact_email,
                school.plan_started_on or "", school.renews_on or "",
                usage.students if usage else "", usage.staff_users if usage else "",
                usage.jobs_last_24h if usage else "",
                usage.last_activity_at.isoformat() if usage and usage.last_activity_at else "",
                usage.taken_on if usage else "", school.created_at.isoformat(),
            ])
        audit.record(request, "schools_exported", rows=len(rows))
        return response


def _cell(value):
    """Defuse spreadsheet formulas in free text (CSV injection)."""
    return "'" + value if value and value[0] in "=+-@\t\r" else value


class AnnouncementSerializer(serializers.ModelSerializer):
    created_by = serializers.SerializerMethodField()
    state = serializers.SerializerMethodField()

    class Meta:
        model = Announcement
        fields = [
            "id", "message", "level", "starts_at", "ends_at", "withdrawn_at",
            "created_by", "created_at", "state",
        ]
        read_only_fields = ["withdrawn_at", "created_by", "created_at"]
        extra_kwargs = {"starts_at": {"required": False}}

    def get_created_by(self, obj):
        return obj.created_by and {"id": obj.created_by.id, "name": obj.created_by.name}

    def get_state(self, obj):
        """``scheduled``, ``showing`` or ``ended``."""
        now = timezone.now()
        if obj.withdrawn_at or (obj.ends_at and obj.ends_at <= now):
            return "ended"
        return "scheduled" if obj.starts_at > now else "showing"

    def validate(self, data):
        starts = data.get("starts_at") or timezone.now()
        if data.get("ends_at") and data["ends_at"] <= starts:
            raise serializers.ValidationError({"ends_at": ["Must be after the start."]})
        data["starts_at"] = starts
        return data


class AnnouncementListView(PlatformView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [IsPlatformOwner()]
        return [IsPlatformStaff()]

    def get(self, request):
        rows = Announcement.objects.select_related("created_by")[:50]
        return Response(AnnouncementSerializer(rows, many=True).data)

    def post(self, request):
        serializer = AnnouncementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        announcement = serializer.save(created_by=request.user)
        audit.record(
            request, "announcement_created", announcement_id=announcement.pk,
            message=announcement.message[:200],
        )
        return Response(AnnouncementSerializer(announcement).data, status=status.HTTP_201_CREATED)


class AnnouncementWithdrawView(PlatformView):
    permission_classes = [IsPlatformOwner]

    def post(self, request, pk):
        announcement = get_object_or_404(Announcement, pk=pk)
        if announcement.withdrawn_at is None:
            announcement.withdrawn_at = timezone.now()
            announcement.save(update_fields=["withdrawn_at"])
            audit.record(request, "announcement_withdrawn", announcement_id=announcement.pk)
        return Response(AnnouncementSerializer(announcement).data)
