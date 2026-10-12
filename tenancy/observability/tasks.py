"""Observability beat tasks (spec 0004). Both run in the public schema."""
import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from tenancy.models import ErrorEvent, ErrorGroup, HealthBucket, SchoolHealth
from tenancy.observability import alerts, health

logger = logging.getLogger("ordo.observability")

PRUNE_BATCH = 1000


@shared_task(ignore_result=True)
def observe_health():
    """Copy counters into buckets, recompute every school's status, and send
    what's due (beat, every 5 minutes; AC-12, AC-13, AC-17 to AC-19)."""
    if not settings.OBSERVABILITY_ENABLED:
        return
    turned_failing = health.observe()
    if turned_failing is None:
        logger.warning("Redis unreachable: health left as it was")
        return
    alerts.sweep(turned_failing)


def _delete_in_batches(queryset):
    model = queryset.model
    deleted = 0
    while True:
        ids = list(queryset.values_list("pk", flat=True)[:PRUNE_BATCH])
        if not ids:
            return deleted
        deleted += model.objects.filter(pk__in=ids).delete()[0]


@shared_task(ignore_result=True)
def prune_observability():
    """Delete old events, buckets and closed groups (beat, daily 03:30 UTC;
    AC-20). Open groups are never pruned."""
    now = timezone.now()
    _delete_in_batches(
        ErrorEvent.objects.filter(occurred_at__lt=now - timedelta(days=settings.OBS_EVENT_KEEP_DAYS))
    )
    _delete_in_batches(
        HealthBucket.objects.filter(hour__lt=now - timedelta(days=settings.OBS_BUCKET_KEEP_DAYS))
    )
    stale_groups = ErrorGroup.objects.filter(
        status__in=(ErrorGroup.Status.RESOLVED, ErrorGroup.Status.IGNORED),
        last_seen__lt=now - timedelta(days=settings.OBS_GROUP_KEEP_DAYS),
    )
    # Their events first, in batches, so no one delete cascades through
    # thousands of rows.
    _delete_in_batches(ErrorEvent.objects.filter(group__in=stale_groups))
    _delete_in_batches(stale_groups)


def purge_school(school):
    """Every observability row of a school being purged."""
    _delete_in_batches(ErrorEvent.objects.filter(school=school))
    _delete_in_batches(ErrorEvent.objects.filter(group__school=school))
    _delete_in_batches(ErrorGroup.objects.filter(school=school))
    HealthBucket.objects.filter(school=school).delete()
    SchoolHealth.objects.filter(school=school).delete()
