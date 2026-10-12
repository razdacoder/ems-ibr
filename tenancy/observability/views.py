"""Observability in the console (``/api/platform/``, platform staff only), and
the browser error ingest endpoint on every host (spec 0004, API surface).
"""
import json

from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django_tenants.utils import get_public_schema_name
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from ems.api.pagination import DefaultPagination
from tenancy import audit
from tenancy.models import ErrorEvent, ErrorGroup, SchoolHealth
from tenancy.observability import capture, counters, health
from tenancy.views import PlatformView

COUNT_FIELDS = ("server_errors", "client_errors", "ws_errors", "js_errors", "job_failures", "requests")


def _school_ref(school):
    if school is None:
        return None
    return {"id": school.pk, "name": school.name, "slug": school.slug, "status": school.status}


def _health_fields(row):
    """``health``, ``reason``, counts and ``computed_at``; nulls before the
    first ``observe_health`` run."""
    return {
        "health": row.status if row else None,
        "reason": row.reason if row else "",
        **{f: getattr(row, f) if row else 0 for f in COUNT_FIELDS},
        "computed_at": row.computed_at if row else None,
    }


def _paginate(view, request, rows):
    paginator = DefaultPagination()
    page = paginator.paginate_queryset(rows, request, view=view)
    return paginator.get_paginated_response(page)


class HealthListView(PlatformView):
    """Every counted school plus Platform, worst first (AC-14)."""

    def get(self, request):
        healths = {h.school_id: h for h in SchoolHealth.objects.all()}
        open_groups = health.open_group_counts()
        rows = [
            {"school": _school_ref(school), **_health_fields(healths.get(school.pk)),
             "open_groups": open_groups.get(school.pk, 0)}
            for school in health.counted_schools().order_by("name")
        ]
        rows.insert(
            0,
            {"school": None, **_health_fields(healths.get(None)), "open_groups": open_groups.get(None, 0)},
        )
        # Not yet computed sorts after healthy.
        rows.sort(key=lambda r: (health.SEVERITY.get(r["health"], 3), -r["server_errors"]))
        return _paginate(self, request, rows)


def _health_detail(school_id):
    row = SchoolHealth.objects.filter(school_id=school_id).first()
    return {**_health_fields(row), "buckets": health.hourly_series(school_id)}


class SchoolHealthView(PlatformView):
    def get(self, request, pk):
        from tenancy.school_views import schools

        school = get_object_or_404(schools(), pk=pk)
        return Response(_health_detail(school.pk))


class PlatformHealthView(PlatformView):
    def get(self, request):
        return Response(_health_detail(None))


class ErrorGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = ErrorGroup
        fields = [
            "id", "title", "culprit", "exc_type", "source", "kind", "status",
            "count", "first_seen", "last_seen", "last_release",
        ]


class ErrorGroupDetailSerializer(ErrorGroupSerializer):
    school = serializers.SerializerMethodField()
    resolved_by = serializers.SerializerMethodField()

    class Meta(ErrorGroupSerializer.Meta):
        fields = ErrorGroupSerializer.Meta.fields + [
            "school", "last_opened_at", "resolved_at", "resolved_by",
        ]

    def get_school(self, obj):
        return _school_ref(obj.school)

    def get_resolved_by(self, obj):
        return obj.resolved_by.name if obj.resolved_by else None


class ErrorEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = ErrorEvent
        fields = ["id", "occurred_at", "message", "stack", "context", "release"]


def _choice(params, name, choices):
    value = params.get(name, "")
    if value and value not in choices:
        raise ValidationError({name: [f"Must be one of: {', '.join(choices)}."]})
    return value


class ErrorGroupListView(PlatformView):
    """A school's (or Platform's) error groups, newest ``last_seen`` first."""

    def get(self, request):
        params = request.query_params
        school = params.get("school", "")
        if school == "platform":
            groups = ErrorGroup.objects.filter(school__isnull=True)
        elif school.isdigit():
            groups = ErrorGroup.objects.filter(school_id=int(school))
        else:
            raise ValidationError({"school": ["Give a school id or \"platform\"."]})
        for name, field in (("status", ErrorGroup.Status), ("source", ErrorGroup.Source), ("kind", ErrorGroup.Kind)):
            value = _choice(params, name, field.values)
            if value:
                groups = groups.filter(**{name: value})
        paginator = DefaultPagination()
        page = paginator.paginate_queryset(groups.order_by("-last_seen", "-id"), request, view=self)
        return paginator.get_paginated_response(ErrorGroupSerializer(page, many=True).data)


def _group(pk):
    return get_object_or_404(
        ErrorGroup.objects.select_related("school", "resolved_by"), pk=pk
    )


class ErrorGroupDetailView(PlatformView):
    def get(self, request, pk):
        return Response(ErrorGroupDetailSerializer(_group(pk)).data)


class ErrorEventListView(PlatformView):
    def get(self, request, pk):
        group = _group(pk)
        paginator = DefaultPagination()
        page = paginator.paginate_queryset(
            group.events.order_by("-occurred_at", "-id"), request, view=self
        )
        return paginator.get_paginated_response(ErrorEventSerializer(page, many=True).data)


STATUS_ACTIONS = {
    ErrorGroup.Status.OPEN: "error_group.reopen",
    ErrorGroup.Status.RESOLVED: "error_group.resolve",
    ErrorGroup.Status.IGNORED: "error_group.ignore",
}


class ErrorGroupStatusView(PlatformView):
    """Owner or Support sets a group open, resolved or ignored (AC-16)."""

    def post(self, request, pk):
        status = request.data.get("status")
        if status not in STATUS_ACTIONS:
            raise ValidationError({"status": ["Must be one of: open, resolved, ignored."]})
        with transaction.atomic():
            group = get_object_or_404(ErrorGroup.objects.select_for_update(), pk=pk)
            if group.status != status:
                group.status = status
                group.resolved_by = request.user
                group.resolved_at = timezone.now() if status == ErrorGroup.Status.RESOLVED else None
                group.save(update_fields=["status", "resolved_by", "resolved_at"])
                audit.record(request, STATUS_ACTIONS[status], group.school, group_id=group.pk)
        return Response(ErrorGroupDetailSerializer(_group(pk)).data)


# Browser error ingest (AC-5).

INGEST_MAX_BYTES = 16 * 1024
STACK_MAX_BYTES = 8 * 1024
TEXT_MAX = 2000
THROTTLE_TTL = 120


def ingest_ip(request):
    """The leftmost ``X-Forwarded-For`` entry, else the socket peer
    (spec 0004, Value sourcing)."""
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    first = forwarded.split(",")[0].strip()
    return first or request.META.get("REMOTE_ADDR") or "unknown"


def _token_user(request):
    """The signed in user if a valid token came along, else None."""
    from rest_framework.exceptions import AuthenticationFailed
    from rest_framework.request import Request

    tenant = getattr(request, "tenant", None)
    on_school = tenant is not None and tenant.schema_name != get_public_schema_name()
    if on_school:
        from ems.api.auth import SchoolTokenAuthentication as auth_class
    else:
        from tenancy.auth import PlatformTokenAuthentication as auth_class
    try:
        result = auth_class().authenticate(Request(request))
    except AuthenticationFailed:
        return None
    return result[0] if result else None


def _parse(body):
    try:
        data = json.loads(body)
    except (ValueError, UnicodeDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    if not all(isinstance(data.get(name), str) for name in ("name", "message", "path")):
        return None
    if not data["name"].strip() or not data["path"].strip():
        return None
    for name in ("stack", "release"):
        if data.get(name) is not None and not isinstance(data[name], str):
            return None
    if len((data.get("stack") or "").encode()) > STACK_MAX_BYTES:
        return None
    return data


def _throttled(request):
    """Over the per IP or per school limit. With Redis down nothing can be
    counted, so reports are dropped rather than let through unlimited."""
    from django.conf import settings

    minute = counters.minute_stamp(timezone.now())
    school = counters.school_key(capture.current_school_id())
    by_ip = counters.hit(f"obs:js:ip:{ingest_ip(request)}:{minute}", THROTTLE_TTL)
    by_school = counters.hit(f"obs:js:school:{school}:{minute}", THROTTLE_TTL)
    if by_ip is None or by_school is None:
        return True
    return by_ip > settings.OBS_JS_IP_PER_MIN or by_school > settings.OBS_JS_SCHOOL_PER_MIN


@csrf_exempt
@require_POST
def ingest_js_error(request):
    """``POST /api/telemetry/errors/``: no token needed, nothing read back."""
    length = request.META.get("CONTENT_LENGTH") or "0"
    if (length.isdigit() and int(length) > INGEST_MAX_BYTES) or len(request.body) > INGEST_MAX_BYTES:
        return JsonResponse({"detail": "Report too large."}, status=413)
    data = _parse(request.body)
    if data is None:
        return JsonResponse({"detail": "Malformed error report."}, status=400)
    if not capture.enabled() or _throttled(request):
        return HttpResponse(status=204)

    user = _token_user(request)
    page = data["path"].split("?")[0].split("#")[0]
    capture.capture_js(
        data["name"][:255],
        data["message"][:TEXT_MAX],
        data.get("stack") or "",
        page,
        data.get("release") or "",
        user_id=user.pk if user else None,
        role=getattr(user, "role", None) if user else None,
        user_agent=request.META.get("HTTP_USER_AGENT", "")[:255],
    )
    return HttpResponse(status=204)
