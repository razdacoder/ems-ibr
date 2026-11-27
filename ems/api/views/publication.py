"""Timetable publication: separate from generation, so the committee can
check a generated timetable before department officers see it, and choose
who is told when it goes out (see ``ems.publication``)."""

from django.db import transaction
from django.db.models import Count, Q
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ems import publication
from ems.api.exceptions import Conflict
from ems.api.permissions import IsSuperAdmin
from ems.models import SystemSettings, TimeTable
from ems.notifications import (
    notify_timetable_published,
    notify_timetable_withdrawn,
    timetable_departments,
)
from tenancy.permissions import requires_feature


def _id_list(data, key):
    """``data[key]`` as a list of ints, or None when absent."""
    raw = data.get(key)
    if raw is None:
        return None
    if not isinstance(raw, list):
        raise ValidationError({key: "Expected a list of ids."})
    try:
        return [int(v) for v in raw]
    except (TypeError, ValueError) as exc:
        raise ValidationError({key: "Expected a list of ids."}) from exc


def _notify_flag(data) -> bool:
    value = data.get("notify", True)
    if isinstance(value, str):
        return value.lower() in ("1", "true", "yes")
    return bool(value)


def _status(request) -> dict:
    row = SystemSettings.objects.select_related("timetable_published_by").first()
    published_at = row.timetable_published_at if row else None
    by = row.timetable_published_by if row else None
    body = {
        "generated": TimeTable.objects.exists(),
        "published": published_at is not None,
        "published_at": published_at,
        "published_by": by.email if by else None,
    }
    if request.user.is_super_admin:
        # The publish dialog's recipient picker: each department in the
        # timetable with how many active users it would reach.
        body["departments"] = [
            {
                "id": d.id,
                "name": d.name,
                "slug": d.slug,
                "papers": d.papers,
                "first_date": str(d.first_date),
                "last_date": str(d.last_date),
                "users": d.users,
            }
            for d in timetable_departments().annotate(
                users=Count("user", filter=Q(user__is_active=True), distinct=True)
            )
        ]
    return body


class TimetablePublicationView(APIView):
    """GET /api/timetable/publication/: draft or published, and (super
    admins) the departments a publish would notify."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(_status(request))


class PublishTimetableView(APIView):
    """POST /api/timetable/publish/

    Body (all optional): ``department_ids`` (default: every department in
    the timetable; ``[]`` = none), ``user_ids`` (extra individual users),
    ``notify`` (default true). Publishing again re-sends to the chosen
    recipients, for example a department added since.
    """

    permission_classes = [IsSuperAdmin, requires_feature("publication")]

    def post(self, request):
        department_ids = _id_list(request.data, "department_ids")
        user_ids = _id_list(request.data, "user_ids")
        if not TimeTable.objects.exists():
            raise ValidationError(
                {"detail": "No timetable to publish. Generate the timetable first."}
            )
        with transaction.atomic():
            already = publication.is_published()
            publication.publish(request.user)
            notified = {"departments": 0, "users": 0}
            if _notify_flag(request.data):
                notified = notify_timetable_published(
                    department_ids=department_ids,
                    user_ids=user_ids,
                    sender=request.user,
                )
        return Response(
            {**_status(request), "already_published": already, "notified": notified}
        )


class UnpublishTimetableView(APIView):
    """POST /api/timetable/unpublish/: back to draft. Department officers
    stop seeing it; those told it was published are told it was withdrawn
    unless ``notify`` is false."""

    permission_classes = [IsSuperAdmin, requires_feature("publication")]

    def post(self, request):
        with transaction.atomic():
            published_at = publication.unpublish()
            if published_at is None:
                raise Conflict("The timetable is not published.")
            notified = 0
            if _notify_flag(request.data):
                notified = notify_timetable_withdrawn(
                    published_at=published_at, sender=request.user
                )
        return Response({**_status(request), "notified": {"users": notified}})
