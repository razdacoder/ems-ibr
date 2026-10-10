"""Notification service: store a message per user and push it live.

``notify`` is the one way in. It writes a ``Notification`` row per
recipient (the inbox the API serves) and, once the transaction commits,
pushes each one to the recipient's WebSocket group so an open browser shows
it at once. The push is best effort: when the channel layer is down the
rows are still there and the inbox picks them up on its next fetch.
"""

import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.db.models import Count, Max, Min

from ems.models import Department, Notification, TimeTable, User

logger = logging.getLogger(__name__)


def user_group(user_id) -> str:
    """Channel group every open tab of one user joins."""
    return f"notifications_{user_id}"


def serialize(notification: Notification) -> dict:
    return {
        "id": notification.id,
        "kind": notification.kind,
        "title": notification.title,
        "body": notification.body,
        "link": notification.link,
        "data": notification.data,
        "created_at": notification.created_at.isoformat(),
        "read_at": (
            notification.read_at.isoformat() if notification.read_at else None
        ),
    }


def _push(notifications) -> None:
    layer = get_channel_layer()
    if layer is None:
        return
    send = async_to_sync(layer.group_send)
    for n in notifications:
        try:
            send(
                user_group(n.recipient_id),
                {"type": "notification.new", "data": serialize(n)},
            )
        except Exception:
            # Redis down or unreachable: the row is saved, so the inbox
            # still shows it. Log once and stop trying for this batch.
            logger.warning("Notification push failed; inbox only.", exc_info=True)
            return


def notify(
    recipients, *, title, body="", kind=Notification.Kind.GENERAL, link="", data=None
) -> list:
    """Notify every user in ``recipients`` (users or ids; duplicates and
    inactive users are dropped). Returns the saved notifications."""
    ids = {getattr(r, "pk", r) for r in recipients}
    ids = list(
        User.objects.filter(pk__in=ids, is_active=True).values_list("pk", flat=True)
    )
    if not ids:
        return []
    created = Notification.objects.bulk_create(
        Notification(
            recipient_id=uid,
            kind=kind,
            title=title,
            body=body,
            link=link,
            data=data or {},
        )
        for uid in sorted(ids)
    )
    transaction.on_commit(lambda: _push(created))
    return created


def department_users(department_ids):
    """Active users who belong to one of ``department_ids``."""
    return User.objects.filter(department_id__in=department_ids, is_active=True)


# Timetable publication ------------------------------------------------------


def timetable_departments():
    """Departments with at least one paper in the timetable, with how many
    papers and the first and last exam date."""
    return (
        Department.objects.filter(class_dep__timetable_class__isnull=False)
        .annotate(
            papers=Count("class_dep__timetable_class", distinct=True),
            first_date=Min("class_dep__timetable_class__date"),
            last_date=Max("class_dep__timetable_class__date"),
        )
        .order_by("name")
    )


def _date_range(first, last) -> str:
    if first == last:
        return first.strftime("%a %d %b %Y")
    return f"{first.strftime('%d %b')} to {last.strftime('%d %b %Y')}"


def notify_timetable_published(*, department_ids=None, user_ids=None, sender=None):
    """Tell each department its own exam timetable is out, and each user in
    ``user_ids`` that the timetable is published.

    ``department_ids=None`` means every department in the timetable. A user
    named in ``user_ids`` who also belongs to a notified department gets one
    message, the department one. The sender is never notified.

    Returns ``{"departments": n, "users": n}``: departments messaged, users
    reached in all.
    """
    departments = timetable_departments()
    if department_ids is not None:
        departments = departments.filter(pk__in=department_ids)

    skip = {sender.pk} if sender is not None else set()
    reached = set()
    departments_notified = 0
    for dept in departments:
        users = [
            u for u in department_users([dept.pk]).values_list("pk", flat=True)
            if u not in skip
        ]
        if not users:
            continue
        span = _date_range(dept.first_date, dept.last_date)
        notify(
            users,
            kind=Notification.Kind.TIMETABLE_PUBLISHED,
            title="Exam timetable published",
            body=(
                f"{dept.name} has {dept.papers} "
                f"{'paper' if dept.papers == 1 else 'papers'}, {span}."
            ),
            link="/timetable",
            data={
                "department_id": dept.pk,
                "papers": dept.papers,
                "first_date": str(dept.first_date),
                "last_date": str(dept.last_date),
            },
        )
        departments_notified += 1
        reached.update(users)

    extra = set(user_ids or ()) - reached - skip
    if extra and TimeTable.objects.exists():
        first, last = TimeTable.objects.aggregate(
            first=Min("date"), last=Max("date")
        ).values()
        sent = notify(
            extra,
            kind=Notification.Kind.TIMETABLE_PUBLISHED,
            title="Exam timetable published",
            body=f"The exam timetable is out: {_date_range(first, last)}.",
            link="/timetable",
            data={"first_date": str(first), "last_date": str(last)},
        )
        reached.update(n.recipient_id for n in sent)

    return {"departments": departments_notified, "users": len(reached)}


def notify_timetable_withdrawn(*, published_at, sender=None) -> int:
    """Tell everyone told about the publication made at ``published_at``
    that it has been taken down. Returns how many users were told."""
    told = (
        Notification.objects.filter(
            kind=Notification.Kind.TIMETABLE_PUBLISHED,
            created_at__gte=published_at,
        )
        .exclude(recipient_id=getattr(sender, "pk", None))
        .values_list("recipient_id", flat=True)
        .distinct()
    )
    sent = notify(
        told,
        kind=Notification.Kind.TIMETABLE_WITHDRAWN,
        title="Exam timetable withdrawn",
        body=(
            "The published timetable has been taken down for changes. "
            "You will be notified when it is published again."
        ),
        link="/timetable",
    )
    return len(sent)


def unread_count(user) -> int:
    return Notification.objects.filter(recipient=user, read_at__isnull=True).count()

