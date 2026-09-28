"""Pre-run checks for the timetable, distribution and allocation stages.

One module feeds the readiness endpoint, the generate views (409 before a job
is queued) and the tasks (a safety net when a job is reached anyway), so the
three can never disagree (spec 0001).

``slots`` is a list of ``(date, period)`` pairs, or ``None`` for every slot the
stage covers (the "generate all" case).
"""

from collections import defaultdict

from django.db.models import Q

from ems.models import Class, Distribution, TimeTable

STAGES = ("timetable", "distribution", "allocation")


class NotReady(Exception):
    """Raised by a task when its stage fails the readiness check."""

    def __init__(self, report: dict):
        self.report = report
        super().__init__(blocking_message(report))


def _slot_q(slots) -> Q:
    q = Q()
    for date, period in slots:
        q |= Q(date=str(date), period=period)
    return q


def _rows(slots):
    qs = TimeTable.objects.select_related("course", "class_obj__department")
    if slots is not None:
        if not slots:
            return qs.none()
        qs = qs.filter(_slot_q(slots))
    return qs.order_by("date", "period", "class_obj__department__name", "class_obj__name")


def _distributed_rows(slots):
    """Rows distribution plans seats for. CBE runs on computers, so
    distribution never processes those rows (``make_schedules``)."""
    return _rows(slots).filter(course__exam_type="PBE")


def timetable_slots() -> list:
    return [
        (str(d), p)
        for d, p in TimeTable.objects.values_list("date", "period")
        .distinct()
        .order_by("date", "period")
    ]


def distribution_slots() -> list:
    return [
        (str(d), p)
        for d, p in Distribution.objects.values_list("date", "period")
        .distinct()
        .order_by("date", "period")
    ]


def empty_classes(stage: str, slots=None) -> list:
    """Active classes the stage would plan for that have no students.

    ``timetable``: every active class linked to a course (no slot yet).
    ``distribution``: active classes timetabled in ``slots`` (all if None).
    """
    if stage == "timetable":
        classes = Class.objects.active().filter(courses__isnull=False).distinct()
        courses_by_class = defaultdict(set)
        for cid, code in classes.values_list("id", "courses__code"):
            courses_by_class[cid].add(code)
    else:
        courses_by_class = defaultdict(set)
        for row in _rows(slots).filter(class_obj__is_active=True):
            courses_by_class[row.class_obj_id].add(row.course.code)
        classes = Class.objects.filter(pk__in=courses_by_class.keys())

    empty = (
        classes.select_related("department")
        .with_student_count()
        .filter(_student_count=0)
        .order_by("department__name", "name")
    )
    return [
        {
            "class_id": cls.id,
            "label": cls.full_label,
            "department": cls.department.name,
            "courses": sorted(courses_by_class[cls.id]),
        }
        for cls in empty
    ]


def stale_rows(slots=None) -> list:
    """Active rows whose ``planned_students`` is NULL or differs from the
    class's live student count. ``slots=None`` = every distributed slot."""
    if slots is None:
        slots = distribution_slots()
    rows = list(_distributed_rows(slots).filter(class_obj__is_active=True))
    counts = Class.objects.filter(
        pk__in={r.class_obj_id for r in rows}
    ).student_count_map()
    return [
        {
            "date": str(r.date),
            "period": r.period,
            "class_id": r.class_obj_id,
            "label": r.class_obj.full_label,
            "course": r.course.code,
            "planned": r.planned_students,
            "current": counts.get(r.class_obj_id, 0),
        }
        for r in rows
        if r.planned_students != counts.get(r.class_obj_id, 0)
    ]


def skipped_inactive(slots=None) -> list:
    """Rows distribution skips because their class is switched off."""
    return [
        {
            "date": str(r.date),
            "period": r.period,
            "class_id": r.class_obj_id,
            "label": r.class_obj.full_label,
            "course": r.course.code,
        }
        for r in _distributed_rows(slots).filter(class_obj__is_active=False)
    ]


def check(stage: str, slots=None) -> dict:
    """Full readiness report for ``stage``. ``ready`` is false when any class
    is empty or any row is stale; ``skipped_inactive`` alone never blocks."""
    if stage not in STAGES:
        raise ValueError(f"Unknown stage '{stage}'.")
    report = {
        "stage": stage,
        "empty_classes": [],
        "stale": [],
        "skipped_inactive": [],
    }
    if stage in ("timetable", "distribution"):
        report["empty_classes"] = empty_classes(stage, slots)
    if stage == "distribution":
        report["skipped_inactive"] = skipped_inactive(slots)
    if stage == "allocation":
        report["stale"] = stale_rows(slots)
    report["ready"] = not report["empty_classes"] and not report["stale"]
    return report


def _sample(items, limit=10) -> str:
    text = "; ".join(items[:limit])
    if len(items) > limit:
        text += f"; and {len(items) - limit} more"
    return text


def blocking_message(report: dict) -> str:
    """One readable sentence for a 409 ``detail`` or a failed job."""
    parts = []
    if report["empty_classes"]:
        labels = [c["label"] for c in report["empty_classes"]]
        parts.append(
            "These active classes have no students uploaded: "
            f"{_sample(labels)}. Upload their student lists, or mark a class "
            "inactive if it is not sitting this session."
        )
    if report["stale"]:
        items = [
            f"{s['date']} {s['period']} {s['label']} ({s['course']}): planned "
            f"{'none' if s['planned'] is None else s['planned']}, now {s['current']}"
            for s in report["stale"]
        ]
        slots = sorted({f"{s['date']} {s['period']}" for s in report["stale"]})
        parts.append(
            "Student lists changed after distribution: "
            f"{_sample(items)}. Regenerate the distribution for "
            f"{_sample(slots)} before allocating."
        )
    parts.append(
        f"See the readiness check (GET /api/readiness/?stage={report['stage']})."
    )
    return " ".join(parts)


def failed_result(report: dict) -> dict:
    """``result_data`` for a job the safety net stopped."""
    return {
        "error": blocking_message(report),
        "error_type": "NotReady",
        "empty_classes": report["empty_classes"],
        "stale": report["stale"],
    }
