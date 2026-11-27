import random

from django.db.models import Prefetch
from collections import Counter

from . import seating_rules
from .halls import course_limit, group_from_name, group_ranks, walk_key
from .seating_rules import (
    RELAXED,
    STRICT,
    even_half,
    even_seats,
    largest_quarter,
    relaxed_quarter_usage,
)
# Re-exported: hall_per_course_slice moved to seating_rules (spec 0002).
from .seating_rules import hall_per_course_slice  # noqa: F401
from .models import (
    Class,
    Course,
    Distribution,
    DistributionItem,
    Hall,
    SeatArrangement,
    TimeTable,
)

################################################################################################################################################################

# Get Halls to memory location


def get_halls(pattern: str = "checkerboard"):
    """All halls for timetable seat-budgeting.

    ``capacity`` here is the **allocation-reachable** seat count for the
    configured ``pattern`` (not the raw seat count). Keeping timetable,
    distribution, and allocation on the same capacity model is what prevents
    courses from being scheduled into a period they can't physically fit.
    """
    return [
        {
            "id": hall.id,
            "name": hall.name,
            "capacity": hall_effective_capacity(
                hall.rows, hall.columns, pattern, hall.capacity, mask=hall.layout
            ),
        }
        for hall in Hall.objects.open()
    ]


# Get courses to memory location
def get_courses():
    """To get courses based on classes object.

    Each class also carries its department + faculty slugs so the CBE
    auto-split routine can bucket classes by faculty without re-querying.

    Only active classes are planned, and ``size`` is the live student count
    (spec 0001). A course with no active class is left out.
    """
    courses = Course.objects.prefetch_related(
        Prefetch(
            "courses",
            queryset=Class.objects.active()
            .select_related("department__faculty")
            .with_student_count(),
        )
    ).all()

    result = []
    for course in courses:
        classes = [
            {
                "id": cls.id,
                "name": cls.name,
                "size": cls.student_count,
                "department_slug": cls.department.slug if cls.department else None,
                "faculty_slug": (
                    cls.department.faculty.slug
                    if cls.department and cls.department.faculty
                    else None
                ),
            }
            for cls in course.courses.all()
        ]
        if classes:
            result.append(
                {
                    "id": course.id,
                    "code": course.code,
                    "exam_type": course.exam_type,
                    "classes": classes,
                }
            )
    return result


# Save timetable to DB
def save_to_timetable_db(schedules):
    """Save schedule into the timetable in DB"""
    timetables = []
    for schedule in schedules:
        for cls in schedule["course"]["classes"]:
            timetables.append(
                TimeTable(
                    course_id=schedule["course"]["id"],
                    class_obj_id=cls["id"],
                    date=schedule["date"],
                    period=schedule["period"],
                    seating_rule=course_rule(schedule["course"]),
                )
            )
    TimeTable.objects.bulk_create(timetables)


def reset_allocation():
    """Clear seat allocations only."""
    SeatArrangement.objects.all().delete()


def reset_distribution():
    """Clear distribution. Allocation depends on it, so clear that too."""
    reset_allocation()
    Distribution.objects.all().delete()
    DistributionItem.objects.all().delete()


def reset_timetable():
    """Clear the timetable and everything planned from it. Deleting a
    timetable row only cascades to its DistributionItems: the Distribution
    rows and the SeatArrangements must go explicitly, or a new timetable
    inherits empty distributions and the old seating."""
    reset_distribution()
    TimeTable.objects.all().delete()


def slot_is_distributed(date, period):
    """True if distribution planned at least one class into a hall for the
    slot. A Distribution row with no items (its timetable rows were
    deleted) is a leftover, not a plan."""
    return DistributionItem.objects.filter(
        distribution__date=str(date), distribution__period=period
    ).exists()


def clear_slot_allocation(date, period):
    """Clear one slot's seat allocation."""
    SeatArrangement.objects.filter(date=str(date), period=period).delete()


def clear_slot_distribution(date, period):
    """Clear one slot's distribution, its allocation (planned from it) and
    the ``planned_students`` it recorded, so the slot reads as never
    distributed."""
    from django.db.models import Q

    clear_slot_allocation(date, period)
    DistributionItem.objects.filter(
        Q(distribution__date=str(date), distribution__period=period)
        | Q(schedule__date=str(date), schedule__period=period)
    ).delete()
    Distribution.objects.filter(date=str(date), period=period).delete()
    TimeTable.objects.filter(date=str(date), period=period).update(
        planned_students=None
    )


def classify_courses(courses, strict_limit, relaxed_limit):
    """Give every course its seating rule once, before the AM/PM split
    (spec 0002). Returns ``(kept, refused_oversized)``.

    A paper course's student count is the sum of its active classes' live
    counts (``get_courses``). CBE is always strict and never classified. A
    paper course too big even for the relaxed rule is left out and reported.
    """
    kept, refused = [], []
    for course in courses:
        if course["exam_type"] != "PBE":
            course["seating_rule"] = STRICT
            kept.append(course)
            continue
        students = sum(cls["size"] for cls in course["classes"])
        rule = seating_rules.classify(students, strict_limit, relaxed_limit)
        if rule == seating_rules.REFUSED:
            refused.append(
                {
                    "code": course["code"],
                    "students": students,
                    "strict_limit": strict_limit,
                    "relaxed_limit": relaxed_limit,
                }
            )
            continue
        course["seating_rule"] = rule
        kept.append(course)
    return kept, refused


# Split courses into AM and PM periods.
# `class_period_overrides` maps class NAME → "AM"/"PM" (case-insensitive),
# so a single "Level 100": "AM" applies across every department.
# Names absent from the map default to AM. CBE always goes AM.
def split_course(courses, class_period_overrides=None):
    overrides = {
        (k or "").strip().lower(): (v or "").upper()
        for k, v in (class_period_overrides or {}).items()
    }
    AM_courses, PM_courses = [], []
    for course in courses:
        if course["exam_type"] != "PBE":
            AM_courses.append(course)
            continue
        period = "AM"
        for cls in course["classes"]:
            key = (cls.get("name") or "").strip().lower()
            mapped = overrides.get(key)
            if mapped == "PM":
                period = "PM"
                break
        if period == "PM":
            PM_courses.append(course)
        else:
            AM_courses.append(course)
    return (AM_courses, PM_courses)


# Automatically split large CBE courses into N sections by faculty
def auto_split_large_cbe_courses(
    courses,
    autosplit_threshold=9000,
    group_count=2,
    faculty_groups=None,
):
    """
    Split each CBE course exceeding `autosplit_threshold` students into
    `group_count` sections, bucketing each class by its faculty's configured
    group number (1..group_count).

    `faculty_groups` is a mapping `{faculty_slug: group_int}`. Generation
    validation guarantees every faculty present in the system has an entry;
    here we still skip empty buckets so we never emit a section with zero
    classes.
    """
    if group_count < 2:
        group_count = 2
    mapping = {(k or "").strip(): int(v) for k, v in (faculty_groups or {}).items()}
    new_courses = []
    split_count = 0

    for course in courses:
        if course["exam_type"] != "CBE":
            new_courses.append(course)
            continue

        total_students = sum(cls["size"] for cls in course["classes"])
        if not (
            total_students > autosplit_threshold and len(course["classes"]) >= 2
        ):
            new_courses.append(course)
            continue

        # Bucket classes into the configured number of groups.
        buckets: dict[int, list] = {g: [] for g in range(1, group_count + 1)}
        for cls in course["classes"]:
            slug = (cls.get("faculty_slug") or "").strip()
            group = mapping.get(slug)
            if not group:
                # Generation gate should have caught this — fall back safely.
                group = group_count
            group = max(1, min(group_count, group))
            buckets[group].append(cls)

        emitted = 0
        for g in range(1, group_count + 1):
            members = buckets[g]
            if not members:
                continue
            group_total = sum(c["size"] for c in members)
            new_courses.append(
                {
                    "id": course["id"],
                    "code": f"{course['code']}-G{g}",
                    "exam_type": course["exam_type"],
                    "classes": members,
                    "original_code": course["code"],
                    "is_split": True,
                    "group": g,
                }
            )
            emitted += 1
            print(
                f"[AUTO-SPLIT] {course['code']} → G{g}: "
                f"{len(members)} classes, {group_total} students"
            )

        if emitted == 0:
            # Shouldn't happen, but degrade gracefully.
            new_courses.append(course)
        else:
            split_count += 1

    if split_count > 0:
        print(
            f"[INFO] Auto-split {split_count} large CBE course(s) "
            f"into up to {split_count * group_count} sections\n"
        )

    return new_courses


def refuse_oversized_cbe(courses, autosplit_threshold):
    """Set aside CBE courses (or auto-split sections) still above
    ``autosplit_threshold``: a full day seats at most that many, so
    ``generate`` could never place them. Returns ``(kept, refused)``."""
    kept, refused = [], []
    for course in courses:
        students = sum(cls["size"] for cls in course["classes"])
        if course["exam_type"] == "CBE" and students > autosplit_threshold:
            refused.append(
                {"code": course["code"], "students": students, "limit": autosplit_threshold}
            )
        else:
            kept.append(course)
    return kept, refused


def cbe_sections(
    courses,
    *,
    autosplit_threshold=9000,
    group_count=2,
    faculty_groups=None,
):
    """The CBE papers ``generate`` schedules from ``courses`` (``get_courses``
    shape): auto-split, then oversized ones set aside. ``(kept, refused)``."""
    return refuse_oversized_cbe(
        auto_split_large_cbe_courses(
            [c for c in courses if c["exam_type"] == "CBE"],
            autosplit_threshold=autosplit_threshold,
            group_count=group_count,
            faculty_groups=faculty_groups,
        ),
        autosplit_threshold,
    )


def cbe_min_days(cbe, *, fullday_threshold=4500, daily_cap=4500):
    """Fewest exam days the CBE papers ``cbe`` (from ``cbe_sections``) need,
    by the rules ``generate`` schedules them under: a paper above
    ``fullday_threshold`` takes a day of its own, and the smaller ones share
    the rest at ``daily_cap`` students a day. A lower bound: it ignores
    which classes clash."""
    full_days = small_students = 0
    for course in cbe:
        students = sum(cls["size"] for cls in course["classes"])
        if students > fullday_threshold:
            full_days += 1
        else:
            small_students += students
    small_days = -(-small_students // daily_cap) if daily_cap else 0
    return full_days + small_days


# Helper function to check if a class is scheduled on a given date
def _class_key(cls):
    # Hashable stand-in for a class dict: equal keys exactly when the dicts
    # compare equal, which is what the list membership test used.
    return tuple(sorted(cls.items()))


def scheduled_class_keys(date, Schedules):
    """Keys of every class already sitting an exam on ``date``."""
    return {
        _class_key(cls)
        for s in Schedules
        if s["date"] == date
        for cls in s["course"]["classes"]
    }


def is_class_scheduled(course, date, Schedules, scheduled=None):
    """True if any of ``course``'s classes already sits an exam on ``date``.

    ``scheduled`` is ``scheduled_class_keys(date, Schedules)``, for callers
    testing many courses against the same schedule. Without it every test
    rescanned the whole session's schedules, which dominated timetable
    generation time.
    """
    if scheduled is None:
        scheduled = scheduled_class_keys(date, Schedules)
    return any(_class_key(cls) in scheduled for cls in course["classes"])


def course_rule(course):
    """The course's seating rule. CBE sections split off later carry none,
    and CBE is always strict."""
    return course.get("seating_rule", STRICT)


def relaxed_blocked(course, date, period, Schedules):
    """True if ``course`` is relaxed and another relaxed course is already
    booked for this date and period. At most one relaxed course per period
    keeps the other checkerboard half free for strict courses."""
    if course_rule(course) != RELAXED:
        return False
    return any(
        s["date"] == date
        and s["period"] == period
        and course_rule(s["course"]) == RELAXED
        for s in Schedules
    )


# Helper function to get total available seats per period
def get_total_seats(Halls, utilization=0.9):
    # Floor per hall to match distribution's per-hall rounding, so the
    # timetable budget never overshoots what distribution can actually absorb.
    return sum(int(Hall["capacity"] * float(utilization)) for Hall in Halls)


# Get total CBE students scheduled for a given date
def get_cbe_student_count(schedules, date):
    """Calculate total number of students in CBE courses scheduled for a given date"""
    total_students = 0
    schedules_date = filter(lambda schedule: schedule["date"] == date, schedules)
    for schedule in schedules_date:
        if schedule["course"]["exam_type"] == "CBE":
            # Sum all class sizes for this CBE course
            total_students += sum([cls["size"] for cls in schedule["course"]["classes"]])
    return total_students


# Check if any CBE course is scheduled on a specific date
def has_cbe_on_date(schedules, date):
    """Check if any CBE course is already scheduled on this date"""
    for schedule in schedules:
        if schedule["date"] == date and schedule["course"]["exam_type"] == "CBE":
            return True
    return False


# Check if entire day is available for a full-day CBE course
def can_schedule_full_day_cbe(
    schedules,
    date,
    course,
    fullday_threshold=4500,
    autosplit_threshold=9000,
):
    """True if a large CBE course can take ``date`` as a full day: none of
    its classes sits an exam that day, and no other CBE does either. A full
    day course fills the CBE centre's capacity in both periods, so two on one
    day (or one beside smaller CBE papers) would overrun it."""
    if course["exam_type"] != "CBE":
        return False

    course_students = sum([cls["size"] for cls in course["classes"]])

    # Only courses above the full-day threshold need full day
    if course_students <= fullday_threshold:
        return False

    # Course must fit within autosplit cap (fullday_threshold AM + same PM)
    if course_students > autosplit_threshold:
        return False

    if is_class_scheduled(course, date, schedules):
        return False

    return not has_cbe_on_date(schedules, date)


# Check if a CBE course can be scheduled within the daily student limit
def can_schedule_cbe(schedules, date, course, max_students=4500):
    """Check if scheduling a CBE course would exceed the daily student limit"""
    # Only check for CBE courses
    if course["exam_type"] != "CBE":
        return True

    # Calculate students in the candidate course
    course_students = sum([cls["size"] for cls in course["classes"]])

    # Get current CBE student count for this date
    current_cbe_students = get_cbe_student_count(schedules, date)

    # Check if adding this course would exceed the limit
    return (current_cbe_students + course_students) <= max_students


# Helper function to check if timetable can still be scheduled based on the number of seats remaining
def can_continue(
    date,
    period,
    seat_remaining,
    courses,
    Schedules,
    fullday_threshold=4500,
    autosplit_threshold=9000,
    daily_cap=4500,
):
    for course in courses:
        # For CBE courses, check if within daily student limit (no seat constraint)
        if course["exam_type"] == "CBE":
            course_students = sum([cls["size"] for cls in course["classes"]])

            # Large CBE courses (> fullday_threshold) need full day
            if course_students > fullday_threshold:
                if can_schedule_full_day_cbe(
                    Schedules, date, course,
                    fullday_threshold=fullday_threshold,
                    autosplit_threshold=autosplit_threshold,
                ):
                    return True
            # Small CBE courses check student limit
            else:
                if (
                    not is_class_scheduled(course, date, Schedules)
                    and can_schedule_cbe(
                        Schedules, date, course, max_students=daily_cap
                    )
                ):
                    return True
        # For PBE courses, check seat availability
        else:
            Seat_Required = sum([Class["size"] for Class in course["classes"]])
            if (
                seat_remaining >= Seat_Required
                and not is_class_scheduled(course, date, Schedules)
                and not relaxed_blocked(course, date, period, Schedules)
            ):
                return True

    # Log why we can't continue
    print(f"[INFO] Cannot continue scheduling for {date} ({period}). Remaining seats: {seat_remaining}")
    current_cbe_count = get_cbe_student_count(Schedules, date)
    print(f"[INFO] Current CBE students for {date}: {current_cbe_count}/{daily_cap}")

    for course in courses:
        reasons = []
        if course["exam_type"] == "CBE":
            course_students = sum([cls["size"] for cls in course["classes"]])

            if course_students > fullday_threshold:
                # Large CBE course logic
                if is_class_scheduled(course, date, Schedules):
                    reasons.append("classes already scheduled")
                elif not can_schedule_full_day_cbe(
                    Schedules, date, course,
                    fullday_threshold=fullday_threshold,
                    autosplit_threshold=autosplit_threshold,
                ):
                    reasons.append("cannot get a full day (another CBE sits that day)")
            else:
                # Small CBE course logic
                if is_class_scheduled(course, date, Schedules):
                    reasons.append("class already scheduled")
                if not can_schedule_cbe(
                    Schedules, date, course, max_students=daily_cap
                ):
                    reasons.append(
                        f"would exceed daily CBE limit (current: {current_cbe_count}, "
                        f"course needs: {course_students}, max: {daily_cap})"
                    )
        else:
            Seat_Required = sum([Class["size"] for Class in course["classes"]])
            if seat_remaining < Seat_Required:
                reasons.append(f"insufficient seats ({seat_remaining} < {Seat_Required})")
            if is_class_scheduled(course, date, Schedules):
                reasons.append("class already scheduled")
            if relaxed_blocked(course, date, period, Schedules):
                reasons.append("another relaxed course already sits this period")

        if reasons:
            print(f"[SKIP] Course {course['code']} ({course['exam_type']}) skipped: {', '.join(reasons)}")

    return False


def can_continue_PM(date, period, seat_remaining, courses, Schedules):
    for course in courses:
        Seat_Required = sum([Class["size"] for Class in course["classes"]])
        if (
            seat_remaining >= Seat_Required
            and not is_class_scheduled(course, date, Schedules)
            and not relaxed_blocked(course, date, period, Schedules)
        ):
            return True
    
    # Log why we can't continue
    print(f"[INFO] Cannot continue scheduling for {date} (PM). Remaining seats: {seat_remaining}")
    for course in courses:
        Seat_Required = sum([Class["size"] for Class in course["classes"]])
        reasons = []
        if seat_remaining < Seat_Required:
            reasons.append(f"insufficient seats ({seat_remaining} < {Seat_Required})")
        if is_class_scheduled(course, date, Schedules):
            reasons.append("class already scheduled")
        if relaxed_blocked(course, date, period, Schedules):
            reasons.append("another relaxed course already sits this period")
        
        if reasons:
            print(f"[SKIP] Course {course['code']} skipped: {', '.join(reasons)}")
    
    return False


def filter_courses(
    date,
    period,
    seat_remaining,
    courses,
    schedules,
    fullday_threshold=4500,
    autosplit_threshold=9000,
    daily_cap=4500,
):
    eligible_courses = []
    scheduled = scheduled_class_keys(date, schedules)
    for course in courses:
        # CBE courses don't require seats
        if course["exam_type"] == "CBE":
            course_students = sum([cls["size"] for cls in course["classes"]])

            # Large CBE courses (> fullday_threshold) need full day
            if course_students > fullday_threshold:
                if can_schedule_full_day_cbe(
                    schedules, date, course,
                    fullday_threshold=fullday_threshold,
                    autosplit_threshold=autosplit_threshold,
                ):
                    eligible_courses.append(course)
            # Small CBE courses check student limit
            else:
                if not is_class_scheduled(course, date, schedules, scheduled) and can_schedule_cbe(
                    schedules, date, course, max_students=daily_cap
                ):
                    eligible_courses.append(course)
        # PBE courses require seat availability
        else:
            seat_required = sum(cls["size"] for cls in course["classes"])
            if (
                seat_remaining >= seat_required
                and not is_class_scheduled(course, date, schedules, scheduled)
                and not relaxed_blocked(course, date, period, schedules)
            ):
                eligible_courses.append(course)
    return eligible_courses


# Get the next valid course to schedule
def get_next_course(
    date,
    period,
    seat_remaining,
    courses,
    Schedules,
    fullday_threshold=4500,
    autosplit_threshold=9000,
    daily_cap=4500,
):
    # Prioritize large CBE courses FIRST - they need full days
    large_cbe_courses = [
        c
        for c in courses
        if c["exam_type"] == "CBE"
        and sum([cls["size"] for cls in c["classes"]]) > fullday_threshold
        and can_schedule_full_day_cbe(
            Schedules, date, c,
            fullday_threshold=fullday_threshold,
            autosplit_threshold=autosplit_threshold,
        )
    ]
    if large_cbe_courses:
        return random.choice(large_cbe_courses)

    # Then small CBE courses (≤ fullday_threshold)
    small_cbe_courses = [
        c
        for c in courses
        if c["exam_type"] == "CBE"
        and sum([cls["size"] for cls in c["classes"]]) <= fullday_threshold
        and not is_class_scheduled(c, date, Schedules)
        and can_schedule_cbe(Schedules, date, c, max_students=daily_cap)
    ]
    if small_cbe_courses:
        return random.choice(small_cbe_courses)

    # Then handle PBE courses with seat constraints
    courses_to_select = filter_courses(
        date, period, seat_remaining, courses, Schedules,
        fullday_threshold=fullday_threshold,
        autosplit_threshold=autosplit_threshold,
        daily_cap=daily_cap,
    )
    if courses_to_select:
        return random.choice(courses_to_select)
    return None


def _give_back_misfits(date, period, schedules, pool, fit_check):
    """Run ``fit_check`` on the paper courses booked for one period and move
    any that would not get hall space for every student back to ``pool``,
    for a later date. Repeats until the rest fit: removing a course frees
    room, but the packer may then place the others differently. Returns how
    many courses went back."""
    if fit_check is None:
        return 0
    moved = 0
    while True:
        booked = [
            s for s in schedules
            if s["date"] == date and s["period"] == period
            and s["course"]["exam_type"] != "CBE"
        ]
        misfits = fit_check([s["course"] for s in booked])
        if not misfits:
            return moved
        ids = {id(c) for c in misfits}
        for s in booked:
            if id(s["course"]) in ids:
                schedules.remove(s)
                pool.append(s["course"])
                moved += 1
                print(
                    f"[FIT] {s['course']['code']} ({period}) moved off {date}: "
                    "distribution could not seat all its students"
                )


# Function to generate the timetable and save it to the DB
def generate(
    dates,
    courses_AM,
    courses_PM,
    Halls,
    *,
    autosplit_threshold=9000,
    fullday_threshold=4500,
    daily_cap=4500,
    pbe_utilization=0.9,
    cbe_group_count=2,
    cbe_faculty_groups=None,
    save=True,
    on_date_planned=None,
    fit_check=None,
):
    """Plan the timetable for ``dates`` and return a summary.

    ``save=False`` leaves the database alone and returns the plan as
    ``summary["schedules"]``, for a caller that must replace the old
    timetable and save the new one in a single transaction.

    ``on_date_planned(done, total)`` is called after each date is planned,
    for progress reporting.

    ``fit_check(courses)`` returns the paper courses of one period that
    distribution could not seat in full (:func:`courses_short_of_halls`).
    They go back to the pool for a later date, so no planned slot leaves a
    class without a hall.
    """
    # Initialize schedules list
    Schedules = []
    # Paper courses a fit check sent back to the pool for a later date.
    rebooked = 0

    # Auto-split large CBE courses into N faculty-keyed sections
    courses_AM = auto_split_large_cbe_courses(
        courses_AM,
        autosplit_threshold=autosplit_threshold,
        group_count=cbe_group_count,
        faculty_groups=cbe_faculty_groups,
    )
    courses_PM = auto_split_large_cbe_courses(
        courses_PM,
        autosplit_threshold=autosplit_threshold,
        group_count=cbe_group_count,
        faculty_groups=cbe_faculty_groups,
    )
    # A CBE paper still too big for a full day after the split can never be
    # placed: report it as refused instead of skipping it date after date.
    courses_AM, refused_cbe = refuse_oversized_cbe(courses_AM, autosplit_threshold)
    courses_PM, refused_cbe_pm = refuse_oversized_cbe(courses_PM, autosplit_threshold)
    refused_cbe += refused_cbe_pm

    # Track initial course counts
    initial_am_count = len(courses_AM)
    initial_pm_count = len(courses_PM)

    print(f"\n{'='*60}")
    print(f"[START] Timetable generation for {len(dates)} dates")
    print(f"[INFO] Total AM courses: {initial_am_count}, Total PM courses: {initial_pm_count}")
    print(f"[INFO] Total hall capacity per period: {get_total_seats(Halls, utilization=pbe_utilization)} seats")
    print(f"{'='*60}\n")

    # Loop through the dates
    for date_index, Date in enumerate(dates, start=1):
        print(f"\n[DATE] Processing: {Date}")
        print(f"[INFO] Remaining courses - AM: {len(courses_AM)}, PM: {len(courses_PM)}")

        Total_Seats_AM = get_total_seats(Halls, utilization=pbe_utilization)
        Total_Seats_PM = get_total_seats(Halls, utilization=pbe_utilization)

        print(f"[INFO] Available seats - AM: {Total_Seats_AM}, PM: {Total_Seats_PM}")

        AM_scheduling = True
        am_scheduled_count = 0
        # While there are still seats available and courses to add
        while AM_scheduling:
            if not can_continue(
                Date, "AM", Total_Seats_AM, courses_AM, Schedules,
                fullday_threshold=fullday_threshold,
                autosplit_threshold=autosplit_threshold,
                daily_cap=daily_cap,
            ):
                AM_scheduling = False
                print(f"[INFO] Stopped AM scheduling for {Date}. Courses scheduled: {am_scheduled_count}")
                break

            Course = get_next_course(
                Date, "AM", Total_Seats_AM, courses_AM, Schedules,
                fullday_threshold=fullday_threshold,
                autosplit_threshold=autosplit_threshold,
                daily_cap=daily_cap,
            )
            if Course is None:
                print(f"[WARN] No valid course found for AM on {Date}")
                AM_scheduling = False
                break

            if Course["exam_type"] == "CBE":
                course_students = sum([cls["size"] for cls in Course["classes"]])

                # Check if course needs full day (> fullday_threshold)
                if course_students > fullday_threshold:
                    if can_schedule_full_day_cbe(
                        Schedules, Date, Course,
                        fullday_threshold=fullday_threshold,
                        autosplit_threshold=autosplit_threshold,
                    ):
                        # Schedule for both AM and PM periods
                        Schedule_AM = {"course": Course, "date": Date, "period": "AM"}
                        Schedule_PM = {"course": Course, "date": Date, "period": "PM"}
                        Schedules.append(Schedule_AM)
                        Schedules.append(Schedule_PM)
                        
                        # Show section info if it's a split course
                        section_info = f" (Section {Course['code'].split('-')[-1]})" if Course.get("is_split") else ""
                        print(f"[OK] Scheduled {Course['code']}{section_info} (FULL DAY - CBE) - {course_students} students (AM + PM)")
                        courses_AM.remove(Course)
                        am_scheduled_count += 1
                    else:
                        # Don't remove - let it try again on next date
                        print(f"[DEFER] {Course['code']} (CBE) - Deferring to next date (classes already scheduled today)")
                
                # Regular scheduling for courses ≤ fullday_threshold
                elif can_schedule_cbe(Schedules, Date, Course, max_students=daily_cap):
                    Schedule = {"course": Course, "date": Date, "period": "AM"}
                    Schedules.append(Schedule)
                    current_cbe_total = get_cbe_student_count(Schedules, Date)
                    print(f"[OK] Scheduled {Course['code']} (AM - CBE) - {course_students} students, {current_cbe_total} total CBE today")
                    courses_AM.remove(Course)
                    am_scheduled_count += 1
                else:
                    # Don't remove small CBE courses either - let them try on next date
                    current_cbe_total = get_cbe_student_count(Schedules, Date)
                    print(f"[DEFER] {Course['code']} (AM - CBE) - Deferring to next date ({current_cbe_total} CBE students already today)")
            else:
                Seat_Required = sum([Class["size"] for Class in Course["classes"]])
                if Total_Seats_AM >= Seat_Required and not is_class_scheduled(
                    Course, Date, Schedules
                ):
                    Schedule = {"course": Course, "date": Date, "period": "AM"}
                    Schedules.append(Schedule)
                    rule_info = " [RELAXED SEATING]" if course_rule(Course) == RELAXED else ""
                    print(f"[OK] Scheduled {Course['code']} (AM){rule_info} - {Seat_Required} seats, {Total_Seats_AM - Seat_Required} remaining")
                    Total_Seats_AM -= Seat_Required
                    courses_AM.remove(Course)
                    am_scheduled_count += 1
                    if Total_Seats_AM == 0:
                        AM_scheduling = False
                        print(f"[INFO] AM period full for {Date}")
                    if (
                        len(filter_courses(
                            Date, "AM", Total_Seats_AM, courses_AM, Schedules,
                            fullday_threshold=fullday_threshold,
                            autosplit_threshold=autosplit_threshold,
                            daily_cap=daily_cap,
                        )) == 0
                    ):
                        AM_scheduling = False
                else:
                    print(f"[SKIP] {Course['code']} (AM) - needs {Seat_Required} seats, only {Total_Seats_AM} available")
                    courses_AM.remove(Course)

        rebooked += _give_back_misfits(Date, "AM", Schedules, courses_AM, fit_check)

        #  Schedule PM Courses
        PM_scheduling = True
        pm_scheduled_count = 0
        while PM_scheduling:
            if not can_continue_PM(Date, "PM", Total_Seats_PM, courses_PM, Schedules):
                PM_scheduling = False
                print(f"[INFO] Stopped PM scheduling for {Date}. Courses scheduled: {pm_scheduled_count}")
                break
            else:
                Course = get_next_course(
                    Date, "PM", Total_Seats_PM, courses_PM, Schedules,
                    fullday_threshold=fullday_threshold,
                    autosplit_threshold=autosplit_threshold,
                    daily_cap=daily_cap,
                )
                if Course is None:
                    print(f"[WARN] No valid course found for PM on {Date}")
                    PM_scheduling = False
                    break
                
                Seat_Required = sum([Class["size"] for Class in Course["classes"]])
                if Total_Seats_PM >= Seat_Required and not is_class_scheduled(
                    Course, Date, Schedules
                ):
                    Schedule = {"course": Course, "date": Date, "period": "PM"}
                    Schedules.append(Schedule)
                    rule_info = " [RELAXED SEATING]" if course_rule(Course) == RELAXED else ""
                    print(f"[OK] Scheduled {Course['code']} (PM){rule_info} - {Seat_Required} seats, {Total_Seats_PM - Seat_Required} remaining")
                    Total_Seats_PM -= Seat_Required
                    courses_PM.remove(Course)
                    pm_scheduled_count += 1
                    if Total_Seats_PM == 0:
                        PM_scheduling = False
                        print(f"[INFO] PM period full for {Date}")
                    if (
                        len(filter_courses(
                            Date, "PM", Total_Seats_PM, courses_PM, Schedules,
                            fullday_threshold=fullday_threshold,
                            autosplit_threshold=autosplit_threshold,
                            daily_cap=daily_cap,
                        )) == 0
                    ):
                        PM_scheduling = False
                else:
                    print(f"[SKIP] {Course['code']} (PM) - needs {Seat_Required} seats, only {Total_Seats_PM} available")
                    courses_PM.remove(Course)
        
        rebooked += _give_back_misfits(Date, "PM", Schedules, courses_PM, fit_check)

        # Log CBE summary for this date
        daily_cbe_count = get_cbe_student_count(Schedules, Date)
        if daily_cbe_count > 0:
            print(f"[CBE SUMMARY] {Date}: {daily_cbe_count} CBE students scheduled")

        if on_date_planned:
            on_date_planned(date_index, len(dates))
    
    # Final summary
    print(f"\n{'='*60}")
    print("[COMPLETE] TIMETABLE GENERATION SUMMARY")
    print(f"{'='*60}")
    
    scheduled_am = initial_am_count - len(courses_AM)
    scheduled_pm = initial_pm_count - len(courses_PM)
    
    print(f"[SUMMARY] AM: {scheduled_am}/{initial_am_count} scheduled, {len(courses_AM)} skipped")
    print(f"[SUMMARY] PM: {scheduled_pm}/{initial_pm_count} scheduled, {len(courses_PM)} skipped")
    print(f"[SUMMARY] Total scheduled: {len(Schedules)} timetable entries")
    
    if courses_AM:
        print(f"\n[SKIPPED] AM courses ({len(courses_AM)}):")
        for course in courses_AM:
            print(f"  - {course['code']}")
    
    if courses_PM:
        print(f"\n[SKIPPED] PM courses ({len(courses_PM)}):")
        for course in courses_PM:
            print(f"  - {course['code']}")
    
    print(f"\n{'='*60}\n")
    
    if save:
        save_to_timetable_db(Schedules)

    summary = {
        'total_scheduled': len(Schedules),
        'am_scheduled': scheduled_am,
        'pm_scheduled': scheduled_pm,
        'am_skipped': len(courses_AM),
        'pm_skipped': len(courses_PM),
        'skipped_am_codes': [c['code'] for c in courses_AM],
        'skipped_pm_codes': [c['code'] for c in courses_PM],
        'relaxed_courses': [
            {
                'code': s['course']['code'],
                'date': str(s['date']),
                'period': s['period'],
                'students': sum(cls['size'] for cls in s['course']['classes']),
            }
            for s in Schedules
            if course_rule(s['course']) == RELAXED
        ],
    }
    summary['refused_cbe'] = refused_cbe
    summary['rebooked_after_fit_check'] = rebooked
    if not save:
        summary['schedules'] = Schedules
    return summary


################################################################################################################################################################


def get_total_no_seats(halls):
    sum = 0
    for hall in halls:
        sum += hall.capacity

    return sum


def get_total_no_seats_needed(timetables):
    """Seats a set of timetable rows needs: the live student count of each
    active row's class. Inactive classes need none."""
    rows = [t for t in timetables if t.class_obj.is_active]
    size_map = slot_student_counts(rows)
    return sum(size_map.get(t.class_obj_id, 0) for t in rows)


def slot_student_counts(timetables) -> dict:
    """``{class id: student count}`` for the classes in ``timetables``, in one
    query. Distribution reads the counts once and uses the same numbers to
    plan and to record ``planned_students``."""
    return Class.objects.filter(
        pk__in={t.class_obj_id for t in timetables}
    ).student_count_map()


def planned_rows(timetables):
    """Rows distribution plans seats for: paper exams whose class is active.
    CBE runs on computers; inactive classes are not sitting."""
    return [
        t
        for t in timetables
        if t.course.exam_type != "CBE" and t.class_obj.is_active
    ]


def record_planned_students(timetables, size_map, result) -> list:
    """Write ``TimeTable.planned_students`` for every planned row, and return
    ``unplaced_by_class``: rows given halls for fewer students than planned.

    ``size_map`` must be the map distribution planned with, so the recorded
    number is exactly the one it used, whether or not everyone found a hall.
    """
    rows = planned_rows(timetables)
    for row in rows:
        row.planned_students = size_map.get(row.class_obj_id, 0)
    TimeTable.objects.bulk_update(rows, ["planned_students"], batch_size=500)

    given = Counter()
    for hall in result:
        for item in hall["classes"]:
            given[item["id"]] += item["student_range"]
    return [
        {
            "timetable_id": row.id,
            "class_id": row.class_obj_id,
            "label": row.class_obj.full_label,
            "course": row.course.code,
            "planned": row.planned_students,
            "assigned": given[row.id],
        }
        for row in rows
        if row.planned_students > given[row.id]
    ]


# Allocation runs the checkerboard pattern under 8-dir adjacency. That means:
#   - The pattern itself uses cells where (r + c) % 2 == 0 → about half the grid.
#   - For a single course, two students one step diagonally apart (e.g. (0,0)
#     and (1,1)) are both even-parity and 8-dir adjacent, so they conflict.
#     Safely packing one course needs every-other-row × every-other-col →
#     about a quarter of the grid.
# Distribution must respect both bounds, otherwise the allocator overflows
# into the unplaced bucket.

def hall_effective_capacity(
    rows: int,
    cols: int,
    pattern: str = "checkerboard",
    capacity: int = 0,
    mask=None,
) -> int:
    """Total seats the allocator can fill in this hall under ``pattern``.

    * ``checkerboard``: only even-parity seats → ceil(rows*cols / 2) for a
      full rectangle.
    * ``sequential``  : every seat → rows * cols for a full rectangle.

    ``mask`` is the hall's seat layout (``None`` = full rectangle); only
    real seats count. ``capacity`` is the hall's stated capacity. The grid
    can hold more cells than the hall is rated for (AH 4 & 5: 14x15 = 210
    cells, capacity 204), so a positive ``capacity`` is a hard ceiling on
    the result.
    """
    if rows <= 0 or cols <= 0:
        return 0
    if pattern == "sequential":
        seats = seating_rules.hall_layout(
            rows, cols, seating_rules.mask_key(mask)
        ).seat_count
    else:
        seats = even_half(rows, cols, mask)  # checkerboard
    if capacity and capacity > 0:
        seats = min(seats, capacity)
    return seats


def current_constraints():
    """The saved ``GenerationConstraints``, or unsaved defaults."""
    from .models import GenerationConstraints

    return GenerationConstraints.objects.first() or GenerationConstraints()


def hall_fill_cap(hall, constraints=None) -> int:
    """Most students ``hall`` may hold in one slot: its seats for the seat
    pattern times ``pbe_hall_utilization``. A hard rule: distribution never
    plans past it, and allocation, reconcile and manual assignment never
    seat past it."""
    constraints = constraints or current_constraints()
    seats = hall_effective_capacity(
        hall.rows, hall.columns, constraints.seat_pattern, hall.capacity,
        mask=hall.layout,
    )
    return int(seats * float(constraints.pbe_hall_utilization))


def in_walk_order(halls, constraints=None, key=lambda hall: hall):
    """``halls`` (or items whose ``key`` is a ``Hall``) in the order
    distribution fills them: group by group in ``hall_group_order``, biggest
    hall first inside a group (see halls.py)."""
    constraints = constraints or current_constraints()
    items = list(halls)

    def seats(hall):
        return hall_effective_capacity(
            hall.rows, hall.columns, constraints.seat_pattern, hall.capacity,
            mask=hall.layout,
        )

    def group(hall):
        return hall.group or group_from_name(hall.name)

    ranks = group_ranks(
        ((group(key(i)), seats(key(i))) for i in items), constraints.hall_group_order
    )
    return sorted(
        items,
        key=lambda i: walk_key(ranks, group(key(i)), seats(key(i)), key(i).name),
    )


def convert_hall_to_dict(
    halls,
    safety_factor: float = 0.90,
    pattern: str = "checkerboard",
    course_limits=None,
):
    """Hall list for distribution.

    ``safety_factor`` defaults to 0.9 and is expected to match
    ``GenerationConstraints.pbe_hall_utilization``, the hard cap on how full
    a hall may get. ``pattern`` matches ``GenerationConstraints.seat_pattern``.
    Together they keep timetable, distribution, and allocation on one
    capacity model. ``course_limits`` is
    ``GenerationConstraints.hall_course_limits``; ``None`` sets no limit.
    """
    halls_dict = []
    for hall in halls:
        mask = seating_rules.mask_key(hall.layout)
        effective = hall_effective_capacity(
            hall.rows, hall.columns, pattern, hall.capacity, mask=mask
        )
        halls_dict.append(
            {
                "id": hall.id,
                "name": hall.name,
                "rows": hall.rows,
                "columns": hall.columns,
                # Seat mask, or None for a full rectangle. Every quarter
                # count below is taken over real seats only.
                "layout": mask,
                # Seat numbering: which even seats the relaxed course takes.
                "seat_order": hall.seat_order,
                # Pattern-aware seat budget; replaces raw hall.capacity for
                # distribution. Headroom keeps the allocator's randomized
                # passes from running out of free seats.
                "capacity": int(effective * safety_factor),
                # The biggest quarter: a course may fill it whole.
                # _max_seatable_bite checks each bite against the quarters
                # actually left, so no unseatable mix gets through.
                "per_course_slice": largest_quarter(hall.rows, hall.columns, mask),
                # Cap for the slot's relaxed course, if any (spec 0002).
                "even_half": even_half(hall.rows, hall.columns, mask),
                # Walk order and course limit (see halls.py). The limit is
                # by the hall's seats for the pattern, before the fill cap.
                "group": hall.group or group_from_name(hall.name),
                "seats": effective,
                "course_limit": (
                    course_limit(effective, course_limits)
                    if course_limits is not None
                    else None
                ),
                "classes": [],
            }
        )
    return halls_dict


def relaxed_course_code(timetables):
    """Code of the one relaxed course among a slot's ``timetables`` rows, or
    ``None``. Timetable generation books at most one per period (spec 0002),
    so more than one means the timetable is broken: refuse rather than seat
    two courses on the same checkerboard half."""
    codes = {t.course.code for t in timetables if t.seating_rule == RELAXED}
    if len(codes) > 1:
        raise ValueError(
            f"More than one relaxed course in one slot ({', '.join(sorted(codes))}). "
            "Regenerate the timetable."
        )
    return next(iter(codes), None)


def courses_short_of_halls(courses, halls, group_order=None, small_course_threshold=0):
    """Paper ``courses`` (``get_courses`` shape) that distribution could not
    give hall space for every student, if they all sat one slot in
    ``halls`` (from :func:`convert_hall_to_dict`, used up by this call).

    Timetable generation calls this after planning each period. Counting
    seats is not enough: course limits, the one-quarter-per-course rule and
    keeping classes in blocks stop the packer from filling halls to the
    last seat, so a period booked to its seat total can leave classes
    without a hall. Runs the real packer on stand-in rows, never saved.
    """
    from types import SimpleNamespace

    rows, owner, size_map = [], {}, {}
    for index, course in enumerate(courses):
        if course["exam_type"] == "CBE":
            continue
        for cls in course["classes"]:
            row = SimpleNamespace(
                id=-(len(rows) + 1),
                course=SimpleNamespace(code=course["code"], exam_type=course["exam_type"]),
                class_obj=SimpleNamespace(name=cls["name"], is_active=True),
                class_obj_id=cls["id"],
                seating_rule=course_rule(course),
            )
            rows.append(row)
            owner[row.id] = index
            size_map[cls["id"]] = cls["size"]
    if not rows:
        return []
    result = distribute_classes_to_halls(
        rows, halls, size_map=size_map, relaxed_course=relaxed_course_code(rows),
        group_order=group_order, small_course_threshold=small_course_threshold,
    )
    given = Counter()
    for hall in result:
        for item in hall["classes"]:
            given[item["id"]] += item["student_range"]
    short = sorted({
        owner[row.id] for row in rows if given[row.id] < size_map[row.class_obj_id]
    })
    return [courses[i] for i in short]


def slot_relaxed_course_id(date, period):
    """Id of the slot's relaxed course, or ``None``, in one query. Reconcile,
    manual assignment and the attendance exports read the rule through this
    once per call, never per student."""
    ids = set(
        TimeTable.objects.filter(
            date=date, period=period, seating_rule=RELAXED
        ).values_list("course_id", flat=True)
    )
    if len(ids) > 1:
        raise ValueError(
            f"More than one relaxed course on {date} {period}. Regenerate the timetable."
        )
    return next(iter(ids), None)


def make_schedules(timetables, size_map=None):
    """One entry per planned row, sized by the class's live student count.
    ``size_map`` (from :func:`slot_student_counts`) lets the caller record
    the same numbers it planned with."""
    rows = planned_rows(timetables)
    if size_map is None:
        size_map = slot_student_counts(rows)
    # A fixed order (the packer then sorts by size): the timetable's fit
    # check and the real distribution must plan a slot the same way, which
    # a random shuffle broke for classes of equal size.
    rows = sorted(rows, key=lambda t: (t.course.code, t.class_obj_id))
    return [
        {
            "id": timetable.id,
            "class": timetable.class_obj.name,
            "course": timetable.course.code,
            "size": size_map.get(timetable.class_obj_id, 0),
        }
        for timetable in rows
    ]


def _quarters_can_seat(
    rows, cols, bites, relaxed_course=None, mask=None, seat_order="rows"
):
    """True if the allocator's pass 0 would seat every ``bites`` entry in a
    ``rows`` x ``cols`` hall with seat layout ``mask`` (``None`` = full).

    ``bites`` is ``[(course_code, count), ...]``. This replays pass 0
    exactly. ``relaxed_course`` (the slot's relaxed course code, or ``None``)
    is placed first, whatever its size, on the first ``count`` seats of
    ``even_seats``. Then ``try_quarter_placement`` runs on what is left:
    strict courses largest first (course code breaks ties), each into
    whichever ``(r%2, c%2)`` quarter has the most free cells, and a course
    must fit one quarter whole. The two must stay in step: anything this
    accepts is seated by pass 0 with no leftovers, so nothing reaches the
    adjacency fallback passes or the cross hall reconcile.
    """
    # A copy: the layout is cached and shared.
    free = dict(
        seating_rules.hall_layout(rows, cols, seating_rules.mask_key(mask)).quarters
    )
    strict_bites = []
    for course, count in bites:
        if course != relaxed_course:
            strict_bites.append((course, count))
            continue
        if count > even_half(rows, cols, mask):
            return False
        in_q00, in_q11 = relaxed_quarter_usage(rows, cols, count, mask, seat_order)
        free[(0, 0)] -= in_q00
        free[(1, 1)] -= in_q11
    for _course, count in sorted(strict_bites, key=lambda b: (-b[1], b[0])):
        best = max(free, key=free.get)
        if count > free[best]:
            return False
        free[best] -= count
    return True


def _max_seatable_bite(hall, course_code, limit, relaxed_course=None):
    """Largest bite (at most ``limit``) of ``course_code`` this hall can still
    seat without leaving anyone unplaced. Only ever returns a verified size.

    Counts of the same course are summed, because the allocator seats a
    course as one group (one quarter, or the even seats for the relaxed
    course) whichever classes it came from."""
    existing = {}
    for c in hall["classes"]:
        existing[c["course"]] = existing.get(c["course"], 0) + c["student_range"]
    lo, hi = 0, limit
    while lo < hi:
        mid = (lo + hi + 1) // 2
        bites = dict(existing)
        bites[course_code] = bites.get(course_code, 0) + mid
        if _quarters_can_seat(
            hall["rows"],
            hall["columns"],
            list(bites.items()),
            relaxed_course,
            mask=hall.get("layout"),
            seat_order=hall.get("seat_order", "rows"),
        ):
            lo = mid
        else:
            hi = mid - 1
    return lo


def course_cap(hall, course_code, relaxed_course=None):
    """Most students of one course this hall can take: its checkerboard half
    for the slot's relaxed course, its quarter slice for any other."""
    if relaxed_course is not None and course_code == relaxed_course:
        return hall.get("even_half", 0)
    return hall.get("per_course_slice", 0)


def _fold_small_hall(hall, hosts, relaxed_course=None):
    """Move every course in ``hall`` into ``hosts`` so ``hall`` need not
    open. All or nothing: if one course finds no host, nothing moves.

    Each course moves whole into one host that can seat it (see
    :func:`_max_seatable_bite`). A host may go one course over its
    ``course_limit``, never more. Hosts that already hold the course come
    first, then hosts still under their limit, then the halls nearest the
    end of the walk, so the small course sits by its neighbours."""
    snapshot = [(h, h["capacity"], [dict(c) for c in h["classes"]]) for h in hosts]
    walk_pos = {id(h): i for i, h in enumerate(hosts)}
    for code in sorted({c["course"] for c in hall["classes"]}):
        pieces = [c for c in hall["classes"] if c["course"] == code]
        count = sum(p["student_range"] for p in pieces)

        def rank(host):
            in_host = {c["course"] for c in host["classes"]}
            limit = host.get("course_limit")
            return (
                code not in in_host,
                limit is not None and len(in_host) >= limit,
                -walk_pos[id(host)],
            )

        for host in sorted(hosts, key=rank):
            in_host = {c["course"] for c in host["classes"]}
            limit = host.get("course_limit")
            if code not in in_host and limit is not None and len(in_host) > limit:
                continue
            if count > host["capacity"]:
                continue
            if _max_seatable_bite(host, code, count, relaxed_course) < count:
                continue
            for piece in pieces:
                same = next(
                    (c for c in host["classes"] if c["id"] == piece["id"]), None
                )
                if same:
                    same["student_range"] += piece["student_range"]
                else:
                    host["classes"].append(dict(piece))
            host["capacity"] -= count
            break
        else:
            for host, capacity, classes in snapshot:
                host["capacity"], host["classes"] = capacity, classes
            return False
    hall["capacity"] += sum(c["student_range"] for c in hall["classes"])
    hall["classes"] = []
    return True


def distribute_classes_to_halls(
    timetables,
    halls,
    size_map=None,
    relaxed_course=None,
    group_order=None,
    small_course_threshold=0,
):
    """Pack timetable rows into halls one hall at a time, in walk order,
    filling each hall as full as it can be seated before the next opens.

    Each hall carries two budgets (set by :func:`convert_hall_to_dict`):
      * ``capacity``         — total students the hall can take for the
                               configured pattern, with safety headroom.
      * ``per_course_slice`` — most students of one strict course: its
                               biggest quarter (the ``even_half`` for the
                               slot's relaxed course, see :func:`course_cap`).

    **Walk order, each hall filled before the next.** Halls are visited
    group by group in ``group_order`` (``GenerationConstraints.
    hall_group_order``), biggest hall first inside a group (see
    :mod:`ems.halls`). A hall keeps taking seatable bites, round after round,
    until no course can add a single student it could seat, never past its
    ``capacity`` (the hard fill cap). Only then does the next hall open. So
    every hall but the last one used is filled to the most the seating rule
    and its course limit allow. The old two pass packer sent tails to
    whichever hall had the *least* room, which filled small halls while big
    ones sat at 60-80%.

    **Courses stay together.** In each hall the courses already started in
    an earlier hall go first, in the order they started, so a course runs
    on through consecutive halls of the walk until it is done and spills
    only into the neighbouring group. New courses then fill what is left,
    largest first.

    **Course limit.** A hall never holds more different courses than its
    ``course_limit`` (from ``GenerationConstraints.hall_course_limits``;
    ``None`` = no limit).

    **The ceiling is the seating rule, not the packer.** Under the strict
    rule one course takes at most one of a hall's four quarters, so a slot
    with only three strict courses can fill no hall past about 75%, however
    the halls are ordered. Courses are tried largest first, the order the
    allocator seats them in, so the quarters fill the way they will be sat.

    **Classes stay together.** Each bite of a course first finishes a class
    an earlier hall started, then takes whole classes that fit, and splits
    at most one more, which runs on into the next hall used. So a split
    class keeps its matric block in consecutive halls.

    **Seatable bites only.** Every bite is capped by
    :func:`_max_seatable_bite`, so a hall is never handed a mix of courses
    the allocator cannot fit into its adjacency safe quarters.

    **Relaxed course.** ``relaxed_course`` is the slot's relaxed course code
    (spec 0002), or ``None``. Its cap per hall is the hall's ``even_half``,
    and the seatability model places it first on the even parity seats.

    **Small courses don't open a hall.** Courses run largest first, so the
    smallest come last, when the halls with room are often already at their
    course limit, and a fresh hall opens for a handful of students. A hall
    holding only courses of at most ``small_course_threshold`` students
    (``GenerationConstraints.small_course_threshold``; 0 = off) is folded
    into the halls already used, each of which may go one course over its
    limit for it (see :func:`_fold_small_hall`).
    """
    class_schedules = make_schedules(timetables=timetables, size_map=size_map)
    # Stable-sort by size desc so a course hands out its biggest classes
    # first; make_schedules' fixed order breaks ties.
    class_schedules.sort(key=lambda s: s["size"], reverse=True)
    ranks = group_ranks(
        ((h.get("group", ""), h.get("seats", h.get("capacity", 0))) for h in halls),
        group_order,
    )
    halls.sort(
        key=lambda h: walk_key(
            ranks, h.get("group", ""), h.get("seats", h.get("capacity", 0)), h["name"]
        )
    )

    classes_by_course: dict[str, list] = {}
    for schedule in class_schedules:
        classes_by_course.setdefault(schedule["course"], []).append(schedule)

    def left(course_code):
        return sum(s["size"] for s in classes_by_course[course_code])

    course_totals = {code: left(code) for code in classes_by_course}

    def place(hall, schedule, take):
        existing = next(
            (c for c in hall["classes"] if c["id"] == schedule["id"]), None
        )
        if existing:
            existing["student_range"] += take
        else:
            hall["classes"].append(
                {
                    "id": schedule["id"],
                    "class": schedule["class"],
                    "course": schedule["course"],
                    "student_range": take,
                }
            )
        hall["capacity"] -= take
        schedule["size"] -= take

    started = set()  # ids of classes already split into an earlier hall

    def give(hall, course_code, count):
        """``count`` students of ``course_code``, splitting as few of its
        classes as possible: first the rest of a class an earlier hall
        started, then whole classes that fit (biggest first), and only then
        the start of one more class, which runs on into the next hall."""
        waiting = [s for s in classes_by_course[course_code] if s["size"]]
        order = [s for s in waiting if s["id"] in started]
        order += [s for s in waiting if s["id"] not in started]
        for schedule in order:
            if count == 0:
                return
            if schedule["id"] in started or schedule["size"] <= count:
                take = min(count, schedule["size"])
                place(hall, schedule, take)
                count -= take
        for schedule in order:
            if count == 0:
                return
            if schedule["size"]:
                take = min(count, schedule["size"])
                place(hall, schedule, take)
                started.add(schedule["id"])
                count -= take

    # Courses in the order they were first placed; they carry on first.
    course_started: dict[str, int] = {}

    def course_order():
        started = sorted(
            (c for c in course_started if left(c)), key=course_started.get
        )
        # Largest remaining first; the course code breaks ties so a re-run
        # hands out the same bites.
        fresh = sorted(
            (c for c in classes_by_course if c not in course_started and left(c)),
            key=lambda code: (-left(code), code),
        )
        return started + fresh

    for hall in halls:
        limit_courses = hall.get("course_limit")
        progress = True
        while progress and hall["capacity"] > 0:
            progress = False
            for course_code in course_order():
                if hall["capacity"] <= 0:
                    break
                in_hall = {c["course"] for c in hall["classes"]}
                if (
                    limit_courses is not None
                    and course_code not in in_hall
                    and len(in_hall) >= limit_courses
                ):
                    continue
                remaining = left(course_code)
                limit = min(
                    remaining,
                    hall["capacity"],
                    course_cap(hall, course_code, relaxed_course),
                )
                take = _max_seatable_bite(hall, course_code, limit, relaxed_course)
                if take > 0:
                    give(hall, course_code, take)
                    course_started.setdefault(course_code, len(course_started))
                    progress = True

    used = [hall for hall in halls if hall["classes"]]
    if small_course_threshold:
        def small_only(hall):
            return all(
                course_totals[c["course"]] <= small_course_threshold
                for c in hall["classes"]
            )

        hosts = [hall for hall in used if not small_only(hall)]
        for hall in reversed([hall for hall in used if small_only(hall)]):
            if not _fold_small_hall(hall, hosts, relaxed_course):
                hosts.append(hall)
    return [hall for hall in used if hall["classes"]]


def save_to_db(res, date, period):
    # One transaction (single commit) instead of a commit per statement, and
    # no per-row SELECTs: use *_id FKs and bulk_create the items. On a remote
    # Postgres this collapses thousands of serialized round-trips down to a
    # handful per hall — the previous N+1 was what blew past Celery's hard
    # time limit on the bulk task.
    from django.db import transaction

    with transaction.atomic():
        # Three statements for the whole slot rather than three per hall:
        # bulk_create returns primary keys on Postgres and SQLite, so the
        # M2M rows can be linked up without re-reading anything.
        distributions = Distribution.objects.bulk_create(
            [Distribution(hall_id=item["id"], date=date, period=period) for item in res]
        )
        dist_items = []
        owners = []
        for distribution, item in zip(distributions, res):
            for cls in item["classes"]:
                dist_items.append(
                    DistributionItem(
                        schedule_id=cls["id"],
                        no_of_students=cls["student_range"],
                    )
                )
                owners.append(distribution)
        DistributionItem.objects.bulk_create(dist_items)
        Through = Distribution.items.through
        Through.objects.bulk_create(
            [
                Through(distribution_id=owner.id, distributionitem_id=dist_item.id)
                for owner, dist_item in zip(owners, dist_items)
            ]
        )


##########################################################################################
################# Seat Allocation ########################################################
##########################################################################################


_ADJACENCY_DIRECTIONS = {
    "8-dir": [
        (-1, -1), (-1, 0), (-1, 1),
        (0, -1),           (0, 1),
        (1, -1),  (1, 0),  (1, 1),
    ],
    "4-dir": [(-1, 0), (1, 0), (0, -1), (0, 1)],
    "off": [],
}


def allocate_students_to_seats(
    students,
    rows,
    cols,
    *,
    adjacency_mode="8-dir",
    success_threshold_pct=60,
    pattern_order=None,
    relaxed_courses=(),
    mask=None,
    seat_order="rows",
):
    """Deterministic seat allocation with a multi-pass approach.

    **Placement is strictly matric-number ordered.** Within every course the
    lowest matric number takes the lowest-numbered legal seat, so walking a
    hall row by row reads matric numbers in ascending order and an
    invigilator can track a class as one contiguous run. No pass shuffles
    students or cells, and re-running the same slot reproduces the same map.

    Students of a course still never sit within ``adjacency_mode`` reach of
    each other — ordering decides *which* legal seat a student gets, never
    whether the adjacency rule is relaxed.

    `adjacency_mode` controls which neighbouring cells block same-course placement.

    ``relaxed_courses`` holds the codes of courses in this hall seated under
    the relaxed rule (spec 0002; at most one per hall). Pass 0 seats such a
    course first on the even parity seats in seat number order, and for it
    only side, front and back neighbours block, in every pass.

    ``mask`` is the hall's seat layout (``None`` = every cell is a seat).
    Every pass picks only from real seats, and seat numbers count real
    seats only. ``seat_order`` is how the hall numbers them; every pass
    walks seats in that order, so matric numbers follow the numbering.
    """
    if not students:  # Check if students list is empty
        return {}, students, 0  # Return all students as unplaced with 0% placement

    layout = seating_rules.hall_layout(
        rows, cols, seating_rules.mask_key(mask), seat_order
    )
    hall_seats = layout.seats  # seat-number order

    if pattern_order is None:
        pattern_order = ["checkerboard", "diagonal", "sequential"]
    directions = _ADJACENCY_DIRECTIONS.get(adjacency_mode, _ADJACENCY_DIRECTIONS["8-dir"])
    relaxed_courses = set(relaxed_courses or ())
    # The relaxed rule narrows the configured one; with adjacency off there
    # is nothing to relax.
    relaxed_directions = seating_rules.neighbours(RELAXED) if directions else []

    # Initialize seat grid and student tracking
    seats = [[None for _ in range(cols)] for _ in range(rows)]
    student_positions = {student["name"]: None for student in students}

    # Group students by course for better placement strategies
    course_groups = {}
    for student in students:
        course = student["course"]
        if course not in course_groups:
            course_groups[course] = []
        course_groups[course].append(student)

    # Sort every course group by matric number once, here — every pass below
    # consumes these lists in order, so this single sort is what makes seat
    # numbers ascend with matric numbers. Plain string ordering, matching the
    # `order_by('matric_no')` the task uses to pick which students land in
    # this hall (see generate_allocation_task); the two must agree or a
    # hall's block would be selected by one order and seated by another.
    for course_students in course_groups.values():
        course_students.sort(key=lambda s: s["name"])

    # O(1) name -> student lookup. is_valid_position is called once per
    # candidate cell per unplaced student (see try_ordered_placement), so a
    # linear `next(... for s in students ...)` scan here turns placement into
    # O(n^2)-per-attempt and is the reason large halls could take many
    # minutes (previously a full task timeout) instead of seconds.
    student_by_name = {student["name"]: student for student in students}

    def is_valid_position(student_name, row, col):
        """Adjacency check honoring the configured mode."""
        if not directions:  # adjacency_mode == "off"
            return True
        course = student_by_name[student_name]["course"]
        blocked = relaxed_directions if course in relaxed_courses else directions
        for dr, dc in blocked:
            r, c = row + dr, col + dc
            if 0 <= r < rows and 0 <= c < cols and seats[r][c]:
                adjacent_student = student_by_name[seats[r][c]]
                if adjacent_student["course"] == course:
                    return False
        return True

    def try_pattern_placement(course_students, pattern="checkerboard"):
        """Place students on a pattern's cells, lowest matric to lowest seat.

        ``course_students`` arrives matric-sorted and each ``positions`` list
        is built row-major, so the first legal cell found for each student is
        also the lowest-numbered one still free.
        """
        placed = 0

        if pattern == "checkerboard":
            # Try checkerboard pattern (every other seat)
            positions = [
                (r, c)
                for r, c in hall_seats
                if (r + c) % 2 == 0 and not seats[r][c]
            ]
        elif pattern == "diagonal":
            # Try diagonal pattern
            positions = [
                (r, c)
                for r, c in hall_seats
                if r % 2 == c % 2 and not seats[r][c]
            ]
        else:
            # Sequential pattern
            positions = [(r, c) for r, c in hall_seats if not seats[r][c]]

        for student in course_students:
            if student_positions[student["name"]] is not None:
                continue  # Already placed

            for row, col in positions:
                if not seats[row][col] and is_valid_position(student["name"], row, col):
                    seats[row][col] = student["name"]
                    student_positions[student["name"]] = (row, col)
                    positions.remove((row, col))
                    placed += 1
                    break

        return placed

    def try_ordered_placement(remaining_students):
        """Seat leftovers by scanning every free cell in seat-number order.

        Replaces the old random dart-throwing passes (100/300/500 blind
        `randint` attempts per student). Two reasons: darts broke matric
        ordering by scattering the tail across the grid, and they could fail
        to seat a student even when a legal cell existed — a full scan finds
        one whenever there is one, so this both preserves ordering and beats
        the old placement rate. `remaining_students` is matric-sorted.
        """
        placed = 0
        free_cells = [(r, c) for r, c in hall_seats if not seats[r][c]]

        for student in remaining_students:
            if student_positions[student["name"]] is not None:
                continue  # Already placed

            for idx, (row, col) in enumerate(free_cells):
                if not seats[row][col] and is_valid_position(student["name"], row, col):
                    seats[row][col] = student["name"]
                    student_positions[student["name"]] = (row, col)
                    free_cells.pop(idx)
                    placed += 1
                    break

        return placed

    def try_relaxed_placement():
        """Seat each relaxed course first, lowest matric to the lowest even
        parity seat (``even_seats``). Even parity seats never share an edge,
        so this is always legal under the relaxed rule. The distribution
        model (``_quarters_can_seat``) replays exactly this."""
        if not directions:
            return 0
        placed_here = 0
        for course_code in sorted(relaxed_courses & course_groups.keys()):
            cells = [
                (r, c)
                for r, c in even_seats(rows, cols, mask, seat_order)
                if not seats[r][c]
            ]
            for student, (row, col) in zip(course_groups[course_code], cells):
                seats[row][col] = student["name"]
                student_positions[student["name"]] = (row, col)
                placed_here += 1
        return placed_here

    def try_quarter_placement():
        """Deterministic 'quarter' placement — the only layout that's
        provably safe under 8-dir same-course adjacency.

        The grid is partitioned into four ``(r%2, c%2)`` quarters. Any two
        cells in the same quarter are at least two apart in row or column,
        so they're never 8-dir adjacent — meaning *any* set of same-course
        students placed in one quarter is automatically conflict-free. A
        single course must stay in one quarter (different quarters touch);
        different courses can share a quarter freely.

        Courses are placed largest-first into the most-empty quarter. With
        distribution capping each course at ``ceil(r/2)*ceil(c/2)`` × safety,
        every course fits its chosen quarter in full.
        """
        if not directions:
            return 0
        quarter_cells = {
            (ro, co): [
                (r, c)
                for r, c in hall_seats
                if r % 2 == ro and c % 2 == co and not seats[r][c]
            ]
            for ro in (0, 1)
            for co in (0, 1)
        }
        # Largest course first; course code breaks ties so two courses of
        # equal size always claim quarters in the same order across runs.
        courses_sorted = sorted(
            (
                (code, group)
                for code, group in course_groups.items()
                if code not in relaxed_courses
            ),
            key=lambda kv: (
                -sum(1 for s in kv[1] if student_positions[s["name"]] is None),
                kv[0],
            ),
        )
        placed_here = 0
        for _course_code, course_students in courses_sorted:
            remaining = [
                s for s in course_students if student_positions[s["name"]] is None
            ]
            if not remaining:
                continue
            # Pick the quarter with the most room.
            best_key = max(quarter_cells, key=lambda k: len(quarter_cells[k]))
            cells = quarter_cells[best_key]
            for student in remaining:
                if not cells:
                    break  # this course's tail will fall through to later passes
                row, col = cells.pop(0)
                seats[row][col] = student["name"]
                student_positions[student["name"]] = (row, col)
                placed_here += 1
        return placed_here

    # Multi-pass allocation strategy with configurable adjacency
    total_placed = 0

    # Pass 0: Deterministic quarter placement — guarantees no same-course
    # 8-dir adjacency for everything it seats, achieving the theoretical max
    # without burning attempts on random dead-ends.
    # The relaxed course goes first, on the even parity seats; strict
    # courses then take quarters of what is left.
    total_placed += try_relaxed_placement()
    total_placed += try_quarter_placement()

    # Pass 1: Pattern-based placement per course in admin-configured order.
    # course_students stays matric-sorted — no shuffle — so anything pass 0
    # left over is still seated in ascending matric order.
    for course, course_students in course_groups.items():
        for pattern in pattern_order:
            remaining = [
                s for s in course_students if student_positions[s["name"]] is None
            ]
            if not remaining:
                break
            placed = try_pattern_placement(remaining, pattern)
            total_placed += placed
            if placed > 0:
                break  # If pattern worked, move to next course

    # Pass 2: Ordered sweep of whatever the pattern passes could not seat.
    # One exhaustive scan replaces the old three escalating random passes —
    # it can only fail when no legal cell exists at all, so a fourth pass
    # would have nothing left to find. Re-sorted by matric because students
    # here come from `students` (hall build order), not a course group.
    remaining_students = sorted(
        (s for s in students if student_positions[s["name"]] is None),
        key=lambda s: (s["course"], s["name"]),
    )
    if remaining_students:
        total_placed += try_ordered_placement(remaining_students)

    # NOTE: Removed relaxed and force placement passes to maintain strict adjacency constraints
    # Students that cannot be placed while maintaining constraints will remain unplaced

    # Convert positions to sequential seat numbers
    index_to_seat = layout.seat_number

    seat_positions = {}
    unplaced_students = []

    for student, position in student_positions.items():
        if position is None:
            unplaced_students.append(student)
        else:
            row, col = position
            if row is not None and col is not None:
                seat_positions[student] = index_to_seat(row, col)
            else:
                unplaced_students.append(student)

    # Calculate placement statistics
    placed_count = len(seat_positions)
    total_students = len(students)
    percentage_placed = (
        (placed_count / total_students) * 100 if total_students > 0 else 0
    )

    # Print debug information
    print(f"Total students: {total_students}")
    print(f"Placed students count: {placed_count}")
    print(f"Unplaced students: {len(unplaced_students)}")
    print(f"Percentage placed: {percentage_placed:.2f}%")

    # Honour admin-configured success threshold (returns partial either way)
    if percentage_placed >= success_threshold_pct:
        return seat_positions, unplaced_students, percentage_placed
    else:
        # Even if below threshold, return partial results instead of empty
        return seat_positions, unplaced_students, percentage_placed


def build_seat_arrangements(
    students,
    rows,
    cols,
    date,
    period,
    hall,
    course_map,
    *,
    adjacency_mode="8-dir",
    success_threshold_pct=60,
    pattern_order=None,
    relaxed_courses=(),
    mask=None,
    seat_order="rows",
):
    """Seat one hall and return its unsaved ``SeatArrangement`` rows.

    Returns ``(arrangements, placed_count, unplaced_count)``. Unplaced
    students get a row with ``seat_number=None`` for ``reconcile_unplaced``
    to pick up. Nothing is written here: the caller saves every hall of the
    slot in one ``bulk_create``, which on a remote database is far cheaper
    than several inserts per hall. ``course_map`` maps course code to
    ``Course``; students' ``student_id`` must be real ids, since the
    allocation task reads them from the database moments before.
    """
    seat_positions, unplaced_students, percentage_placed = allocate_students_to_seats(
        students, rows, cols,
        adjacency_mode=adjacency_mode,
        success_threshold_pct=success_threshold_pct,
        pattern_order=pattern_order,
        relaxed_courses=relaxed_courses,
        mask=mask,
        seat_order=seat_order,
    )
    # First student wins on a repeated matric number, as the linear scan
    # this lookup replaced did.
    by_name = {}
    for s in students:
        by_name.setdefault(s["name"], s)

    def row(student_name, seat):
        student = by_name[student_name]
        return SeatArrangement(
            date=date,
            period=period,
            student_id=student.get("student_id"),
            seat_number=seat,
            hall=hall,
            course=course_map.get(student["course"]),
            cls_id=student["cls_id"],
        )

    # Course by course, matric ordered within each, placed rows first.
    placed_rows = sorted(
        seat_positions.items(),
        key=lambda kv: (by_name[kv[0]]["course"], kv[0]),
    )
    unplaced_rows = sorted(
        unplaced_students, key=lambda name: (by_name[name]["course"], name)
    )
    arrangements = [row(name, seat) for name, seat in placed_rows]
    arrangements += [row(name, None) for name in unplaced_rows]
    return arrangements, len(placed_rows), len(unplaced_rows)


def is_valid_position(
    seat_number, course_code, seat_map, rows, cols, rule=STRICT, mask=None,
    seat_order="rows",
):
    """
    Check if a seat position is valid for manual assignment based on adjacency constraints.

    Args:
        seat_number (int): The seat number to check (1-based)
        course_code: The course of the student to be placed (a code or an
            id, matching the values of ``seat_map``)
        seat_map (dict): Dictionary mapping seat numbers to courses
        rows (int): Number of rows in the hall
        cols (int): Number of columns in the hall
        rule (str): The course's seating rule for the slot (spec 0002):
            8-dir for strict, 4-dir for relaxed
        mask: The hall's seat layout (``None`` = every cell is a seat)
        seat_order: How the hall numbers its seats

    Returns:
        bool: True if the position is valid, False otherwise (including a
        seat number the hall does not have)
    """
    layout = seating_rules.hall_layout(
        rows, cols, seating_rules.mask_key(mask), seat_order
    )
    cell = layout.cell(seat_number)
    if cell is None:
        return False
    row, col = cell

    for dr, dc in seating_rules.neighbours(rule):
        adj_row, adj_col = row + dr, col + dc

        # Only real seats can hold a neighbour
        if layout.is_seat(adj_row, adj_col):
            adj_seat_number = layout.seat_number(adj_row, adj_col)

            # Check if there's a student in the adjacent seat with the same course
            if adj_seat_number in seat_map and seat_map[adj_seat_number] == course_code:
                return False

    return True


def reconcile_unplaced(date, period):
    """Cross-hall reconciliation: seat any students left unplaced in one
    hall into another hall (same date/period) that still has empty cells
    *and* room for that course's quarter.

    Runs after every hall has been allocated independently. Walks every
    ``SeatArrangement`` row with ``seat_number=NULL`` and, course-by-course,
    finds a destination hall whose empty parity quarter can absorb the
    student without breaking the course's seating rule: 8-dir for strict
    courses, 4-dir for the slot's relaxed course (spec 0002).

    A destination never goes past its fill cap (:func:`hall_fill_cap`) or
    takes a new course past its course limit, and halls in (or nearest to)
    the groups the course already sits in are tried first.

    Returns the number of students reseated.
    """
    from .models import SeatArrangement, Hall

    unplaced_qs = (
        SeatArrangement.objects.filter(
            date=date, period=period, seat_number__isnull=True
        )
        .select_related("course", "cls", "hall", "student")
        # Matric order within each course, so overflow students keep landing
        # in their destination hall in the same ascending run they would have
        # had at home. NULL student FKs (placeholder rows) sort last.
        .order_by("course_id", "student__matric_no")
    )
    if not unplaced_qs.exists():
        return 0

    constraints = current_constraints()
    # Closed halls take no overflow either.
    halls = in_walk_order(Hall.objects.open(), constraints)
    # Group rank of every hall, for "nearest group" (see halls.py).
    ranks = group_ranks(
        ((h.group or group_from_name(h.name), 0) for h in halls),
        constraints.hall_group_order,
    )
    rank_of_hall = {h.id: ranks[h.group or group_from_name(h.name)] for h in halls}
    # The slot's rule, looked up once: only its relaxed course is 4-dir.
    relaxed_course_id = slot_relaxed_course_id(date, period)
    strict_offsets = seating_rules.neighbours(STRICT)
    relaxed_offsets = seating_rules.neighbours(RELAXED)

    # Every seated row of the slot in one query, grouped by hall, instead of
    # a query per hall.
    seated_by_hall: dict[int, list[tuple[int, int]]] = {}
    for hall_id, seat_number, course_id in SeatArrangement.objects.filter(
        date=date, period=period, seat_number__isnull=False
    ).values_list("hall_id", "seat_number", "course_id"):
        seated_by_hall.setdefault(hall_id, []).append((seat_number, course_id))

    # Build per-hall occupancy maps once.
    hall_state: dict[int, dict] = {}
    for hall in halls:
        r, c = hall.rows, hall.columns
        layout = seating_rules.layout_of(hall)
        grid = [[None] * c for _ in range(r)]
        for seat_number, course_id in seated_by_hall.get(hall.id, ()):
            cell = layout.cell(seat_number)
            if cell is not None:
                grid[cell[0]][cell[1]] = course_id
        # Free seats grouped by parity quarter.
        quarters: dict[tuple[int, int], list[tuple[int, int]]] = {
            (ro, co): [] for ro in (0, 1) for co in (0, 1)
        }
        for row, col in layout.seats:
            if grid[row][col] is None:
                quarters[(row % 2, col % 2)].append((row, col))
        # Per-quarter occupancy of course_ids so we don't seat a student in
        # a quarter that already has same-course students stuck there.
        quarter_courses: dict[tuple[int, int], set[int]] = {
            (ro, co): set() for ro in (0, 1) for co in (0, 1)
        }
        for row, col in layout.seats:
            cid = grid[row][col]
            if cid is not None:
                quarter_courses[(row % 2, col % 2)].add(cid)
        seated = seated_by_hall.get(hall.id, ())
        hall_state[hall.id] = {
            "rows": r,
            "cols": c,
            # Seats left under the hard fill cap, and the course limit.
            "room": hall_fill_cap(hall, constraints) - len(seated),
            "courses": {course_id for _seat, course_id in seated},
            "course_limit": course_limit(
                hall_effective_capacity(
                    hall.rows, hall.columns, constraints.seat_pattern,
                    hall.capacity, mask=hall.layout,
                ),
                constraints.hall_course_limits,
            ),
            "layout": layout,
            "grid": grid,
            "quarters": quarters,
            "quarter_courses": quarter_courses,
        }

    def cell_is_legal(state, row, col, course_id):
        """True if course_id at (row, col) keeps its rule's separation.

        Checks the actual grid, not just which courses a quarter hosts. The
        quarter-set test this replaced only asked "is this course already in
        *this* quarter" — but a cell in quarter (0,0) touches cells in all
        three other quarters, so that test seated students right next to a
        same-course neighbour living one quarter over.
        """
        grid = state["grid"]
        offsets = (
            relaxed_offsets if course_id == relaxed_course_id else strict_offsets
        )
        for dr, dc in offsets:
            rr, cc = row + dr, col + dc
            if 0 <= rr < state["rows"] and 0 <= cc < state["cols"]:
                if grid[rr][cc] == course_id:
                    return False
        return True

    reseated = 0
    reseat_writes = []
    # Hall each (class, course) overflow last went to. Trying it first keeps
    # a class's overflow together as one block. Ranking by free cells alone
    # changed the winner after every student, so a class was dealt out a few
    # students per hall across many halls.
    last_target: dict[tuple, int] = {}
    # Group ranks each course already sits in.
    course_ranks: dict[int, set[int]] = {}
    for hall_id, state in hall_state.items():
        for course_id in state["courses"]:
            course_ranks.setdefault(course_id, set()).add(rank_of_hall[hall_id])

    def distance(hall_id, course_id):
        """How many groups away ``hall_id`` is from the course's halls."""
        here = course_ranks.get(course_id)
        rank = rank_of_hall[hall_id]
        return min(abs(rank - r) for r in here) if here else 0

    for sa in unplaced_qs:
        target_id = None
        target_pos = None
        group = (sa.cls_id, sa.course_id)
        # The hall this class's overflow last went to first, then the halls
        # nearest the course's groups, then the emptiest. Within a hall, a
        # quarter that already has this course (extending an existing
        # same-course quarter is always safe) or any quarter the course
        # hasn't entered.
        sorted_halls = sorted(
            (
                kv for kv in hall_state.items()
                if kv[1]["room"] > 0
                and (
                    sa.course_id in kv[1]["courses"]
                    or len(kv[1]["courses"]) < kv[1]["course_limit"]
                )
            ),
            key=lambda kv: (
                kv[0] != last_target.get(group),
                distance(kv[0], sa.course_id),
                -sum(len(v) for v in kv[1]["quarters"].values()),
            ),
        )
        for hall_id, state in sorted_halls:
            quarters = state["quarters"]
            qcourses = state["quarter_courses"]
            # Quarters already hosting this course are tried first: cells
            # within one parity quarter are mutually non-adjacent, so they are
            # the likeliest to yield a legal cell. This is only an ordering
            # heuristic now — every candidate cell is adjacency-checked below,
            # including in `preferred`, so a quarter the course has not
            # entered is no longer assumed safe.
            preferred = [
                key for key, courses in qcourses.items()
                if sa.course_id in courses and quarters[key]
            ]
            fallback = [
                key for key, courses in qcourses.items()
                if sa.course_id not in courses and quarters[key]
            ]
            for key in preferred + fallback:
                cells = quarters[key]
                # Cells are row-major, so scanning front-to-back and taking
                # the first *legal* one keeps reseated students in ascending
                # seat order to match their ascending matric order, without
                # the blind pop(0) that put them next to existing neighbours.
                for idx, (row, col) in enumerate(cells):
                    if cell_is_legal(state, row, col, sa.course_id):
                        cells.pop(idx)
                        state["grid"][row][col] = sa.course_id
                        qcourses[key].add(sa.course_id)
                        target_id = hall_id
                        target_pos = (row, col)
                        break
                if target_id is not None:
                    break
            if target_id is not None:
                break
        if target_id is None:
            continue  # genuinely no room anywhere
        last_target[group] = target_id
        state = hall_state[target_id]
        state["room"] -= 1
        state["courses"].add(sa.course_id)
        course_ranks.setdefault(sa.course_id, set()).add(rank_of_hall[target_id])
        # Persist the move.
        row, col = target_pos
        sa.hall_id = target_id
        sa.seat_number = hall_state[target_id]["layout"].seat_number(row, col)
        reseat_writes.append(sa)
        reseated += 1

    # One bulk UPDATE instead of a commit per reseated student.
    if reseat_writes:
        SeatArrangement.objects.bulk_update(
            reseat_writes, ["hall_id", "seat_number"]
        )

    return reseated
