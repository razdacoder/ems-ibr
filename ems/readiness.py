"""Pre-run checks for the timetable, distribution and allocation stages.

One module feeds the readiness endpoint, the generate views (409 before a job
is queued) and the tasks (a safety net when a job is reached anyway), so the
three can never disagree (spec 0001).

``slots`` is a list of ``(date, period)`` pairs, or ``None`` for every slot the
stage covers (the "generate all" case).
"""

from collections import defaultdict

from django.db.models import Q

from ems import seating_rules
from ems.models import Class, Distribution, Hall, TimeTable

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


def outdated_rules(slots=None) -> list:
    """Paper courses in ``slots`` whose stored ``seating_rule`` no longer
    matches ``classify`` with today's student counts and halls (spec 0002).

    For example a strict course that has since grown past ``strict_limit``:
    distributing it under the old rule would leave students without a seat.
    The student count is the course's active classes, as at generation.
    """
    stored = defaultdict(set)
    codes = {}
    for date, period, course_id, code, rule in _distributed_rows(slots).values_list(
        "date", "period", "course_id", "course__code", "seating_rule"
    ):
        stored[(str(date), period, course_id)].add(rule)
        codes[course_id] = code
    if not stored:
        return []

    classes_by_course = defaultdict(set)
    for cid, course_id in Class.objects.active().filter(
        courses__in=codes.keys()
    ).values_list("id", "courses"):
        if course_id in codes:
            classes_by_course[course_id].add(cid)
    counts = Class.objects.filter(
        pk__in={cid for ids in classes_by_course.values() for cid in ids}
    ).student_count_map()
    students = {
        course_id: sum(counts.get(cid, 0) for cid in classes_by_course[course_id])
        for course_id in codes
    }

    halls = list(Hall.objects.open().values_list("rows", "columns", "layout"))
    strict = seating_rules.strict_limit(halls)
    relaxed = seating_rules.relaxed_limit(halls)

    outdated = []
    for (date, period, course_id), rules in sorted(
        stored.items(), key=lambda kv: (kv[0][0], kv[0][1], codes[kv[0][2]])
    ):
        current = seating_rules.classify(students[course_id], strict, relaxed)
        stored_rule = next(iter(rules)) if len(rules) == 1 else "mixed"
        if stored_rule != current:
            outdated.append(
                {
                    "date": date,
                    "period": period,
                    "course": codes[course_id],
                    "stored_rule": stored_rule,
                    "current_rule": current,
                    "students": students[course_id],
                }
            )
    return outdated


def closed_halls(slots=None) -> list:
    """Halls a slot's distribution planned into that are now closed.
    Allocation would seat students there, so the slot needs distributing
    again. ``slots=None`` = every distributed slot."""
    if slots is None:
        slots = distribution_slots()
    if not slots:
        return []
    return [
        {"date": str(date), "period": period, "hall_id": hall_id, "hall": name}
        for date, period, hall_id, name in Distribution.objects.filter(
            _slot_q(slots), hall__is_open=False
        )
        .values_list("date", "period", "hall_id", "hall__name")
        .distinct()
        .order_by("date", "period", "hall__name")
    ]


def check(stage: str, slots=None) -> dict:
    """Full readiness report for ``stage``. ``ready`` is false when any class
    is empty, any row is stale, (distribution) any course's seating rule is
    out of date, or (allocation) the distribution uses a closed hall;
    ``skipped_inactive`` alone never blocks."""
    if stage not in STAGES:
        raise ValueError(f"Unknown stage '{stage}'.")
    report = {
        "stage": stage,
        "empty_classes": [],
        "stale": [],
        "skipped_inactive": [],
        "outdated_rules": [],
        "closed_halls": [],
    }
    if stage in ("timetable", "distribution"):
        report["empty_classes"] = empty_classes(stage, slots)
    if stage == "distribution":
        report["skipped_inactive"] = skipped_inactive(slots)
        report["outdated_rules"] = outdated_rules(slots)
    if stage == "allocation":
        report["stale"] = stale_rows(slots)
        report["closed_halls"] = closed_halls(slots)
    report["ready"] = (
        not report["empty_classes"]
        and not report["stale"]
        and not report["outdated_rules"]
        and not report["closed_halls"]
    )
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
    if report.get("outdated_rules"):
        codes = sorted({o["course"] for o in report["outdated_rules"]})
        parts.append(
            f"Timetable seating rule outdated for {_sample(codes)}, "
            "regenerate the timetable."
        )
    if report.get("closed_halls"):
        names = sorted({h["hall"] for h in report["closed_halls"]})
        slots = sorted({f"{h['date']} {h['period']}" for h in report["closed_halls"]})
        parts.append(
            f"Distribution uses closed halls: {_sample(names)}. Regenerate the "
            f"distribution for {_sample(slots)}, or open the halls again."
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
        "outdated_rules": report.get("outdated_rules", []),
        "closed_halls": report.get("closed_halls", []),
    }
