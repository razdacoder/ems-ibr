"""Alert emails for new and returning errors, failing schools, and platform
wide incidents (AC-17, AC-18, AC-19), sent through ``tenancy.alerts``.

Throttles live in Redis. If Redis is down nothing is sent: pending groups
stay pending and go out on a later sweep, and the console shows everything.
"""
import time

from django.db.models import F, Q
from django.utils import timezone

from tenancy import alerts as platform_alerts
from tenancy.models import ErrorGroup, School
from tenancy.observability import counters

COOLDOWN_SECONDS = 60 * 60
SPIKE_SECONDS = 6 * 60 * 60
INCIDENT_SECONDS = 30 * 60
INCIDENT_WINDOW_SECONDS = 10 * 60
INCIDENT_SCHOOLS = 5
GROUPS_LISTED = 20

RECENT_KEY = "obs:alert:recent"
INCIDENT_KEY = "obs:alert:incident"


def cooldown_key(key):
    return f"obs:alert:cool:{key}"


def spike_key(key):
    return f"obs:alert:spike:{key}"


def pending_groups():
    """Open server side errors not yet emailed since they last (re)opened."""
    return (
        ErrorGroup.objects.filter(status=ErrorGroup.Status.OPEN, kind=ErrorGroup.Kind.ERROR)
        .exclude(source=ErrorGroup.Source.JS)
        .filter(Q(alerted_at__isnull=True) | Q(alerted_at__lt=F("last_opened_at")))
        .order_by("-last_opened_at")
    )


def _name(school):
    return f"{school.name} ({school.slug})" if school else "Platform"


def _path(school_id):
    return f"/schools/{school_id}#errors" if school_id else "/health"


def new_errors_email(school, groups):
    regressed = sum(1 for g in groups if g.first_seen != g.last_opened_at)
    noun = "error" if len(groups) == 1 else "errors"
    headline = f"{len(groups)} new {noun} at {school.name if school else 'Platform'}"
    if regressed == len(groups):
        headline = f"{len(groups)} {noun} came back at {school.name if school else 'Platform'}"
    lines = [f"School: {_name(school)}"]
    for group in groups[:GROUPS_LISTED]:
        tag = "came back" if group.first_seen != group.last_opened_at else "new"
        lines.append(f"[{tag}] {group.title} · {group.culprit} · {group.count} so far")
    if len(groups) > GROUPS_LISTED:
        lines.append(f"…and {len(groups) - GROUPS_LISTED} more in the console.")
    platform_alerts.send(headline, lines, _path(school.pk if school else None))


def spike_email(school, health):
    platform_alerts.send(
        f"{school.name if school else 'Platform'} is failing",
        [
            f"School: {_name(school)}",
            f"Why: {health.reason}",
            f"Last hour: {health.server_errors} server errors, {health.client_errors} 4xx, "
            f"{health.ws_errors} WebSocket errors, {health.js_errors} browser errors, "
            f"{health.requests} requests.",
        ],
        _path(school.pk if school else None),
    )


def incident_email(keys):
    ids = [int(k) for k in keys if k != "platform"]
    names = {s.pk: s.name for s in School.objects.filter(pk__in=ids)}
    listed = [names.get(i, f"School {i}") for i in ids] + (["Platform"] if "platform" in keys else [])
    platform_alerts.send(
        f"Platform wide incident: {len(listed)} schools alerting at once",
        [
            "Many schools hit errors within 10 minutes, so this is likely one shared cause.",
            "Schools: " + ", ".join(sorted(listed)),
            "Per school alert emails are held for 30 minutes. Everything still shows in the console.",
        ],
        "/health",
    )


def _redis_ok():
    return counters.run(lambda r: r.get("obs:alert:probe") or True) is not None


def _may_email(key):
    """Register ``key`` as about to email. False while an incident holds
    per school emails, or when this send tips one off."""
    now = time.time()

    def check(redis):
        if redis.exists(INCIDENT_KEY):
            return False
        redis.zadd(RECENT_KEY, {key: now})
        redis.zremrangebyscore(RECENT_KEY, "-inf", now - INCIDENT_WINDOW_SECONDS)
        if redis.zcard(RECENT_KEY) > INCIDENT_SCHOOLS:
            if redis.set(INCIDENT_KEY, "1", nx=True, ex=INCIDENT_SECONDS):
                return "incident"
            return False
        return True

    result = counters.run(check)
    if result == "incident":
        keys = counters.run(lambda r: list(r.zrange(RECENT_KEY, 0, -1)))
        incident_email(keys or [key])
        return False
    return bool(result)


def _take(name, seconds):
    return bool(counters.run(lambda r: r.set(name, "1", nx=True, ex=seconds)))


def _cooling(key):
    return bool(counters.run(lambda r: r.exists(cooldown_key(key))))


def sweep(turned_failing=(), now=None):
    """Send what's due. ``turned_failing`` is ``[(school_id, SchoolHealth)]``."""
    if not _redis_ok():
        return
    now = now or timezone.now()

    by_school = {}
    for group in pending_groups().select_related("school"):
        by_school.setdefault(group.school_id, []).append(group)

    for school_id, groups in by_school.items():
        key = counters.school_key(school_id)
        if _cooling(key) or not _may_email(key):
            continue
        if not _take(cooldown_key(key), COOLDOWN_SECONDS):
            continue
        new_errors_email(groups[0].school, groups)
        ErrorGroup.objects.filter(pk__in=[g.pk for g in groups]).update(alerted_at=now)

    for school_id, health in turned_failing:
        key = counters.school_key(school_id)
        if counters.run(lambda r: r.exists(spike_key(key))) or not _may_email(key):
            continue
        if _take(spike_key(key), SPIKE_SECONDS):
            spike_email(health.school if school_id else None, health)

