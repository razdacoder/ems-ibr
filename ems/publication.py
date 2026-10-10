"""Timetable publication: a generated timetable is a draft until a super
admin publishes it.

Admin-side users (``is_staff``: every role) always see the timetable and
everything planned from it. Department officers see it only once it is
published, and publishing is what notifies them (``ems.notifications``).
A new timetable, or a reset that clears it, goes back to draft.
"""

from django.utils import timezone

from ems.models import SystemSettings


def _settings() -> SystemSettings:
    obj = SystemSettings.objects.first()
    if obj is None:
        obj = SystemSettings.objects.create(session="2024/2025", semester="1st Semester")
    return obj


def is_published() -> bool:
    row = SystemSettings.objects.only("timetable_published_at").first()
    return bool(row and row.timetable_published_at)


def visible_to(user) -> bool:
    """Whether ``user`` may see the timetable and what is planned from it."""
    return bool(user.is_staff or is_published())


def publish(user) -> SystemSettings:
    """Mark the timetable published by ``user``. Publishing again keeps the
    first publication time."""
    row = _settings()
    if row.timetable_published_at is None:
        row.timetable_published_at = timezone.now()
        row.timetable_published_by = user
        row.save(update_fields=["timetable_published_at", "timetable_published_by"])
    return row


def unpublish():
    """Back to draft. Returns when it had been published, or None."""
    row = _settings()
    published_at = row.timetable_published_at
    if published_at is not None:
        clear(row)
    return published_at


def clear(row=None) -> None:
    """Back to draft without telling anyone: the timetable it covered is
    gone or replaced."""
    row = row or SystemSettings.objects.first()
    if row is None:
        return
    row.timetable_published_at = None
    row.timetable_published_by = None
    row.save(update_fields=["timetable_published_at", "timetable_published_by"])
