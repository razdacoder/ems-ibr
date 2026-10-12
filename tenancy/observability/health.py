"""Each school's health over the last hour (AC-12) and its hourly buckets
(AC-13), computed by ``observe_health`` every 5 minutes.

Counts come from the Redis counters, never from scanning events. If Redis
can't be reached, nothing is written: ``SchoolHealth`` keeps its last value
and the stale ``computed_at`` shows it.
"""
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.db.models import Avg
from django.utils import timezone
from django_tenants.utils import get_public_schema_name

from tenancy.models import ErrorGroup, HealthBucket, School, SchoolHealth
from tenancy.observability import counters

WINDOW = timedelta(minutes=60)
BASELINE = timedelta(hours=168)
SEVERITY = {
    SchoolHealth.Status.FAILING: 0,
    SchoolHealth.Status.DEGRADED: 1,
    SchoolHealth.Status.HEALTHY: 2,
}


def counted_schools():
    """Schools whose status is computed: every live one (AC-12)."""
    return School.objects.filter(status__in=School.LIVE_STATUSES).exclude(
        schema_name=get_public_schema_name()
    )


def hour_start(at):
    return at.replace(minute=0, second=0, microsecond=0)


def _plural(n, one, many=None):
    return f"{n} {one if n == 1 else (many or one + 's')}"


@dataclass
class Verdict:
    status: str
    reason: str


def _server_side_groups(school_id):
    return (
        ErrorGroup.objects.filter(school_id=school_id, kind=ErrorGroup.Kind.ERROR)
        .exclude(source=ErrorGroup.Source.JS)
    )


def baseline_4xx(school_id, now):
    """Average hourly 4xx over the 7 days before the current hour."""
    start = hour_start(now)
    value = HealthBucket.objects.filter(
        school_id=school_id, hour__gte=start - BASELINE, hour__lt=start
    ).aggregate(avg=Avg("client_errors"))["avg"]
    return value or 0


def evaluate(school_id, totals, now):
    """The AC-12 rules, in order. ``totals`` are the last 60 minutes."""
    server = totals["server_errors"]
    if server >= settings.OBS_FAILING_ERRORS:
        return Verdict(SchoolHealth.Status.FAILING, f"{_plural(server, 'server error')} in the last hour")
    fresh = (
        _server_side_groups(school_id)
        .filter(status=ErrorGroup.Status.OPEN, last_opened_at__gte=now - WINDOW)
        .order_by("-last_opened_at")
        .first()
    )
    if fresh is not None:
        what = "New error" if fresh.first_seen == fresh.last_opened_at else "Error came back"
        return Verdict(SchoolHealth.Status.FAILING, f"{what}: {fresh.title}"[:255])

    if server >= 1:
        return Verdict(SchoolHealth.Status.DEGRADED, f"{_plural(server, 'server error')} in the last hour")
    js = totals["js_errors"]
    if js >= settings.OBS_JS_DEGRADED:
        return Verdict(SchoolHealth.Status.DEGRADED, f"{_plural(js, 'browser error')} in the last hour")
    client = totals["client_errors"]
    if client >= settings.OBS_4XX_SPIKE_MIN:
        usual = baseline_4xx(school_id, now)
        if client >= settings.OBS_4XX_SPIKE_FACTOR * usual:
            return Verdict(
                SchoolHealth.Status.DEGRADED,
                f"Spike in 4xx responses: {client} in the last hour, usually about {round(usual)}",
            )
    ws = totals["ws_errors"]
    if ws >= settings.OBS_WS_SPIKE:
        return Verdict(SchoolHealth.Status.DEGRADED, f"{_plural(ws, 'WebSocket error')} in the last hour")
    return Verdict(SchoolHealth.Status.HEALTHY, "No problems in the last hour")


def _copy_buckets(school_id, now):
    """Set (not add) the current and previous hours' buckets from Redis,
    so running twice does no harm. False if Redis is down."""
    key = counters.school_key(school_id)
    hours = [hour_start(now), hour_start(now) - timedelta(hours=1)]
    hashes = counters.read_hashes([counters.hour_key(key, h) for h in hours])
    if hashes is None:
        return False
    for hour in hours:
        values = hashes[counters.hour_key(key, hour)]
        HealthBucket.objects.update_or_create(
            school_id=school_id,
            hour=hour,
            defaults={f: values.get(f, 0) for f in counters.FIELDS},
        )
    return True


def observe(now=None):
    """Steps 1 and 2 of ``observe_health`` for every counted school plus
    Platform. Returns the schools that just turned ``failing``, as
    ``(school_id, SchoolHealth)``, or None if Redis is down."""
    now = now or timezone.now()
    targets = [None, *counted_schools().values_list("pk", flat=True)]
    turned_failing = []
    for school_id in targets:
        if not _copy_buckets(school_id, now):
            return None
        totals = counters.last_minutes(counters.school_key(school_id), now)
        if totals is None:
            return None
        verdict = evaluate(school_id, totals, now)
        previous = SchoolHealth.objects.filter(school_id=school_id).values_list("status", flat=True).first()
        health, _ = SchoolHealth.objects.update_or_create(
            school_id=school_id,
            defaults={
                "status": verdict.status,
                "reason": verdict.reason[:255],
                "server_errors": totals["server_errors"],
                "client_errors": totals["client_errors"],
                "ws_errors": totals["ws_errors"],
                "js_errors": totals["js_errors"],
                "job_failures": totals["job_failures"],
                "requests": totals["requests"],
                "computed_at": now,
            },
        )
        if verdict.status == SchoolHealth.Status.FAILING and previous != SchoolHealth.Status.FAILING:
            turned_failing.append((school_id, health))
    return turned_failing


def open_group_counts():
    """``{school_id: open groups}``, Platform under None."""
    from django.db.models import Count

    rows = (
        ErrorGroup.objects.filter(status=ErrorGroup.Status.OPEN)
        .values("school_id")
        .annotate(n=Count("id"))
    )
    return {row["school_id"]: row["n"] for row in rows}


def hourly_series(school_id, now=None):
    """168 hourly points ending with the current hour, zero filled."""
    now = now or timezone.now()
    end = hour_start(now)
    start = end - BASELINE + timedelta(hours=1)
    stored = {
        b.hour: b
        for b in HealthBucket.objects.filter(school_id=school_id, hour__gte=start, hour__lte=end)
    }
    points = []
    for i in range(168):
        hour = start + timedelta(hours=i)
        bucket = stored.get(hour)
        point = {"hour": hour}
        for f in counters.FIELDS:
            point[f] = getattr(bucket, f) if bucket else 0
        points.append(point)
    return points
