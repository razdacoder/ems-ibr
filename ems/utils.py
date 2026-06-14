import os
import random
import shutil
import zipfile

import pandas as pd  # type: ignore
from django.conf import settings
from django.db.models import Prefetch
from typing_extensions import Counter

from .models import (
    Class,
    Course,
    Department,
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
            "capacity": hall_effective_capacity(hall.rows, hall.columns, pattern),
        }
        for hall in Hall.objects.all()
    ]


# Get courses to memory location
def get_courses():
    """To get courses based on classes object.

    Each class also carries its department + faculty slugs so the CBE
    auto-split routine can bucket classes by faculty without re-querying.
    """
    courses = Course.objects.prefetch_related(
        Prefetch(
            "courses",
            queryset=Class.objects.select_related(
                "department__faculty"
            ).with_student_count(),
        )
    ).all()

    return [
        {
            "id": course.id,
            "code": course.code,
            "exam_type": course.exam_type,
            "classes": [
                {
                    "id": cls.id,
                    "name": cls.name,
                    # Live uploaded count, falling back to declared size.
                    "size": cls.effective_size,
                    "department_slug": cls.department.slug if cls.department else None,
                    "faculty_slug": (
                        cls.department.faculty.slug
                        if cls.department and cls.department.faculty
                        else None
                    ),
                }
                for cls in course.courses.all()
            ],
        }
        for course in courses
    ]


# Save timetable to DB
def save_to_timetable_db(schedules):
    """Save schedule into the timetable in DB"""
    timetables = []
    for schedule in schedules:
        for cls in schedule["course"]["classes"]:
            timetables.append(
                TimeTable(
                    course=Course.objects.get(id=schedule["course"]["id"]),
                    class_obj=Class.objects.get(id=cls["id"]),
                    date=schedule["date"],
                    period=schedule["period"],
                )
            )
    TimeTable.objects.bulk_create(timetables)


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


# Helper function to check if a class is scheduled on a given date
def is_class_scheduled(course, date, Schedules):
    for cls in course["classes"]:
        for schedule in Schedules:
            if schedule["date"] == date and cls in schedule["course"]["classes"]:
                return True
    return False


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
    """Check if a large CBE course can be scheduled (only checks class conflicts)"""
    if course["exam_type"] != "CBE":
        return False

    course_students = sum([cls["size"] for cls in course["classes"]])

    # Only courses above the full-day threshold need full day
    if course_students <= fullday_threshold:
        return False

    # Course must fit within autosplit cap (fullday_threshold AM + same PM)
    if course_students > autosplit_threshold:
        return False

    # Only check if any class in this course is already scheduled
    if is_class_scheduled(course, date, schedules):
        return False

    return True


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
            ):
                return True

    # Log why we can't continue
    print(f"[INFO] Cannot continue scheduling for {date} (AM). Remaining seats: {seat_remaining}")
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
                    reasons.append("cannot get full day (classes conflict)")
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

        if reasons:
            print(f"[SKIP] Course {course['code']} ({course['exam_type']}) skipped: {', '.join(reasons)}")

    return False


def can_continue_PM(date, seat_remaining, courses, Schedules):
    for course in courses:
        Seat_Required = sum([Class["size"] for Class in course["classes"]])
        if seat_remaining >= Seat_Required and not is_class_scheduled(
            course, date, Schedules
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
        
        if reasons:
            print(f"[SKIP] Course {course['code']} skipped: {', '.join(reasons)}")
    
    return False


def filter_courses(
    date,
    seat_remaining,
    courses,
    schedules,
    fullday_threshold=4500,
    autosplit_threshold=9000,
    daily_cap=4500,
):
    eligible_courses = []
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
                if not is_class_scheduled(course, date, schedules) and can_schedule_cbe(
                    schedules, date, course, max_students=daily_cap
                ):
                    eligible_courses.append(course)
        # PBE courses require seat availability
        else:
            seat_required = sum(cls["size"] for cls in course["classes"])
            if seat_remaining >= seat_required and not is_class_scheduled(
                course, date, schedules
            ):
                eligible_courses.append(course)
    return eligible_courses


# Get the next valid course to schedule
def get_next_course(
    date,
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
        date, seat_remaining, courses, Schedules,
        fullday_threshold=fullday_threshold,
        autosplit_threshold=autosplit_threshold,
        daily_cap=daily_cap,
    )
    if courses_to_select:
        return random.choice(courses_to_select)
    return None


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
):
    # Initialize schedules list
    Schedules = []

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

    # Track initial course counts
    initial_am_count = len(courses_AM)
    initial_pm_count = len(courses_PM)

    print(f"\n{'='*60}")
    print(f"[START] Timetable generation for {len(dates)} dates")
    print(f"[INFO] Total AM courses: {initial_am_count}, Total PM courses: {initial_pm_count}")
    print(f"[INFO] Total hall capacity per period: {get_total_seats(Halls, utilization=pbe_utilization)} seats")
    print(f"{'='*60}\n")

    # Loop through the dates
    for Date in dates:
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
                Date, Total_Seats_AM, courses_AM, Schedules,
                fullday_threshold=fullday_threshold,
                autosplit_threshold=autosplit_threshold,
                daily_cap=daily_cap,
            ):
                AM_scheduling = False
                print(f"[INFO] Stopped AM scheduling for {Date}. Courses scheduled: {am_scheduled_count}")
                break

            Course = get_next_course(
                Date, Total_Seats_AM, courses_AM, Schedules,
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
                    print(f"[OK] Scheduled {Course['code']} (AM) - {Seat_Required} seats, {Total_Seats_AM - Seat_Required} remaining")
                    Total_Seats_AM -= Seat_Required
                    courses_AM.remove(Course)
                    am_scheduled_count += 1
                    if Total_Seats_AM == 0:
                        AM_scheduling = False
                        print(f"[INFO] AM period full for {Date}")
                    if (
                        len(filter_courses(
                            Date, Total_Seats_AM, courses_AM, Schedules,
                            fullday_threshold=fullday_threshold,
                            autosplit_threshold=autosplit_threshold,
                            daily_cap=daily_cap,
                        )) == 0
                    ):
                        AM_scheduling = False
                else:
                    print(f"[SKIP] {Course['code']} (AM) - needs {Seat_Required} seats, only {Total_Seats_AM} available")
                    courses_AM.remove(Course)

        #  Schedule PM Courses
        PM_scheduling = True
        pm_scheduled_count = 0
        while PM_scheduling:
            if not can_continue_PM(Date, Total_Seats_PM, courses_PM, Schedules):
                PM_scheduling = False
                print(f"[INFO] Stopped PM scheduling for {Date}. Courses scheduled: {pm_scheduled_count}")
                break
            else:
                Course = get_next_course(
                    Date, Total_Seats_PM, courses_PM, Schedules,
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
                    print(f"[OK] Scheduled {Course['code']} (PM) - {Seat_Required} seats, {Total_Seats_PM - Seat_Required} remaining")
                    Total_Seats_PM -= Seat_Required
                    courses_PM.remove(Course)
                    pm_scheduled_count += 1
                    if Total_Seats_PM == 0:
                        PM_scheduling = False
                        print(f"[INFO] PM period full for {Date}")
                    if (
                        len(filter_courses(
                            Date, Total_Seats_PM, courses_PM, Schedules,
                            fullday_threshold=fullday_threshold,
                            autosplit_threshold=autosplit_threshold,
                            daily_cap=daily_cap,
                        )) == 0
                    ):
                        PM_scheduling = False
                else:
                    print(f"[SKIP] {Course['code']} (PM) - needs {Seat_Required} seats, only {Total_Seats_PM} available")
                    courses_PM.remove(Course)
        
        # Log CBE summary for this date
        daily_cbe_count = get_cbe_student_count(Schedules, Date)
        if daily_cbe_count > 0:
            print(f"[CBE SUMMARY] {Date}: {daily_cbe_count} CBE students scheduled")
    
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
    
    # Bulk upload schedules to timetable Db
    save_to_timetable_db(Schedules)
    
    # Return summary for task result
    return {
        'total_scheduled': len(Schedules),
        'am_scheduled': scheduled_am,
        'pm_scheduled': scheduled_pm,
        'am_skipped': len(courses_AM),
        'pm_skipped': len(courses_PM),
        'skipped_am_codes': [c['code'] for c in courses_AM],
        'skipped_pm_codes': [c['code'] for c in courses_PM],
    }


################################################################################################################################################################


def get_total_no_seats(halls):
    sum = 0
    for hall in halls:
        sum += hall.capacity

    return sum


def get_total_no_seats_needed(timetables):
    # Effective size = live uploaded student count, falling back to the
    # declared class size. Built once to avoid a per-row query.
    size_map = Class.objects.effective_size_map()
    sum = 0
    for timetable in timetables:
        sum += size_map.get(timetable.class_obj_id, timetable.class_obj.size)
    return sum


# Allocation runs the checkerboard pattern under 8-dir adjacency. That means:
#   - The pattern itself uses cells where (r + c) % 2 == 0 → about half the grid.
#   - For a single course, two students one step diagonally apart (e.g. (0,0)
#     and (1,1)) are both even-parity and 8-dir adjacent, so they conflict.
#     Safely packing one course needs every-other-row × every-other-col →
#     about a quarter of the grid.
# Distribution must respect both bounds, otherwise the allocator overflows
# into the unplaced bucket.

def hall_effective_capacity(rows: int, cols: int, pattern: str = "checkerboard") -> int:
    """Total seats the allocator can fill in this hall under ``pattern``.

    * ``checkerboard``: only even-parity cells → ceil(rows*cols / 2).
    * ``sequential``  : all cells → rows * cols.
    """
    if rows <= 0 or cols <= 0:
        return 0
    if pattern == "sequential":
        return rows * cols
    return (rows * cols + 1) // 2  # checkerboard


def hall_per_course_slice(rows: int, cols: int, pattern: str = "checkerboard") -> int:
    """Largest course that's guaranteed to fit any quarter of the hall.

    Each course is confined to one ``(r%2, c%2)`` parity quarter so all its
    students stay pairwise non-8-dir-adjacent. When ``rows`` or ``cols`` is
    odd the four quarters have unequal sizes (e.g. a 15×20 hall has two
    80-cell and two 70-cell quarters). To guarantee zero adjacency-overflow
    we cap at the *smallest* quarter — ``floor(r/2) × floor(c/2)`` — rather
    than the largest. Pattern is irrelevant; same-course adjacency binds.
    """
    del pattern
    if rows <= 0 or cols <= 0:
        return 0
    return max(1, rows // 2) * max(1, cols // 2)


def convert_hall_to_dict(
    halls,
    safety_factor: float = 0.90,
    pattern: str = "checkerboard",
):
    """Hall list for distribution.

    ``safety_factor`` defaults to 0.9 and is expected to match
    ``GenerationConstraints.pbe_hall_utilization``. ``pattern`` matches
    ``GenerationConstraints.seat_pattern``. Together they keep timetable,
    distribution, and allocation on one capacity model.
    """
    halls_dict = []
    for hall in halls:
        effective = hall_effective_capacity(hall.rows, hall.columns, pattern)
        halls_dict.append(
            {
                "id": hall.id,
                "name": hall.name,
                "rows": hall.rows,
                "columns": hall.columns,
                # Pattern-aware seat budget; replaces raw hall.capacity for
                # distribution. Headroom keeps the allocator's randomized
                # passes from running out of free seats.
                "capacity": int(effective * safety_factor),
                # Slice equals the smallest quarter, so the deterministic
                # quarter placer always finds room — no headroom multiplier
                # needed.
                "per_course_slice": hall_per_course_slice(
                    hall.rows, hall.columns, pattern
                ),
                "classes": [],
            }
        )
    return halls_dict


def make_schedules(timetables):
    # Effective size = live uploaded student count, falling back to the
    # declared class size. Built once to avoid a per-row query.
    size_map = Class.objects.effective_size_map()
    tt = []
    for timetable in timetables:
        if timetable.course.exam_type == "CBE":
            continue
        tt.append(
            {
                "id": timetable.id,
                "class": timetable.class_obj.name,
                "course": timetable.course.code,
                "size": size_map.get(
                    timetable.class_obj_id, timetable.class_obj.size
                ),
            }
        )
    random.shuffle(tt)
    return tt


def is_course_in_hall(hall, course_code):
    if len(hall["classes"]) == 0:
        return False
    for cls in hall["classes"]:
        if cls["course"] == course_code:
            return True
    return False


def distribute_classes_to_halls(timetables, halls, remainder_threshold=5):
    """Pack timetable rows into halls under allocation-aware caps.

    Each hall carries two budgets (set by :func:`convert_hall_to_dict`):
      * ``capacity``           — total students the hall can absorb under
                                  checkerboard + 8-dir adjacency, with safety
                                  headroom (≈ 0.45 × rows × cols).
      * ``per_course_slice``    — max students of any one course in the hall
                                  (≈ rows × cols / 4).

    Largest schedules go first so they aren't fragmented across many halls.
    Halls are visited largest-capacity first for the same reason.
    """
    class_schedules = make_schedules(timetables=timetables)
    # make_schedules already random-shuffles. Stable-sort by size desc to
    # place big courses first while keeping intra-size randomness.
    class_schedules.sort(key=lambda s: s["size"], reverse=True)
    halls.sort(key=lambda h: h.get("capacity", 0), reverse=True)

    for hall in halls:
        slice_cap = hall.get("per_course_slice", 0)
        for schedule in class_schedules:
            if schedule["size"] == 0:
                continue
            if is_course_in_hall(hall, schedule["course"]):
                # Keep slices of the same course in different halls — this is
                # what lets the allocator spread same-course adjacency risk.
                continue
            seats_remaining = hall["capacity"]
            if seats_remaining <= 0:
                break

            take = min(schedule["size"], seats_remaining, slice_cap)
            if take <= 0:
                continue
            # Sweep up a tiny tail rather than spilling it to another hall —
            # but only if it still fits within both budgets.
            tail = schedule["size"] - take
            if 0 < tail < remainder_threshold and tail <= seats_remaining - take:
                take += tail

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

    return [hall for hall in halls if hall["classes"]]


def save_to_db(res, date, period):

    for item in res:
        hall = Hall.objects.get(id=item["id"])
        distribution = Distribution.objects.create(hall=hall, date=date, period=period)
        for cls in item["classes"]:
            schedule = TimeTable.objects.get(id=cls["id"])
            dist_item = DistributionItem.objects.create(
                schedule=schedule, no_of_students=cls["student_range"]
            )
            distribution.items.add(dist_item)
            distribution.save()
        distribution.save()


###################################
##### BULK UPLOAD FUNCTION ########
###################################


def handle_uploaded_file(file, upload_type):
    """Process uploaded ZIP file entirely in memory without creating temporary files"""
    print("File Uploaded Successful")

    # Read the uploaded file into memory
    file_content = b""
    for chunk in file.chunks():
        file_content += chunk

    # Process ZIP file in memory
    import io

    with zipfile.ZipFile(io.BytesIO(file_content), "r") as zip_ref:
        if upload_type == "courses":
            return process_class_course_files_memory(zip_ref)
        elif upload_type == "classes":
            return process_department_class_file_memory(zip_ref)
        elif upload_type == "students":
            return process_student_files_memory(zip_ref)

    return None


def process_class_course_files_memory(zip_ref):
    """Process class course files from ZIP in memory"""
    import io

    # Look for 'class course' folder in ZIP
    class_course_files = [
        f
        for f in zip_ref.namelist()
        if f.startswith("class course/") and f.endswith(".csv")
    ]

    if not class_course_files:
        raise ValueError(
            "No 'class course' folder with CSV files found in the ZIP file."
        )

    for file_path in class_course_files:
        # Extract department and class name from path: 'class course/department/class.csv'
        path_parts = file_path.split("/")
        if len(path_parts) >= 3:
            department_name = path_parts[1]
            class_file = path_parts[2]
            class_name, ext = os.path.splitext(class_file)

            if ext == ".csv":
                try:
                    class_obj = Class.objects.get(
                        name=class_name, department__slug=department_name
                    )

                    # Read CSV content from ZIP
                    csv_content = zip_ref.read(file_path)
                    csv_io = io.StringIO(csv_content.decode("utf-8"))
                    process_class_course_csv_memory(csv_io, class_obj)

                except Class.DoesNotExist:
                    print(
                        f"Class {class_name} in department {department_name} does not exist in the database."
                    )


def process_class_course_files(extracted_dir):
    class_course_path = os.path.join(extracted_dir, "class course")
    if os.path.isdir(class_course_path):
        for department_name in os.listdir(class_course_path):
            department_path = os.path.join(class_course_path, department_name)
            if os.path.isdir(department_path):
                for class_file in os.listdir(department_path):
                    class_name, ext = os.path.splitext(class_file)
                    if ext == ".csv":
                        class_path = os.path.join(department_path, class_file)
                        try:
                            class_obj = Class.objects.get(
                                name=class_name, department__slug=department_name
                            )
                            process_class_course_csv(class_path, class_obj)
                        except Class.DoesNotExist:
                            print(
                                f"Class {class_name} in department {department_name} does not exist in the database."
                            )


def process_department_class_file_memory(zip_ref):
    """Process department class files from ZIP in memory"""
    import io

    # Look for 'classes' folder in ZIP
    dept_class_files = [
        f
        for f in zip_ref.namelist()
        if f.startswith("classes/") and f.endswith("classes.csv")
    ]

    if not dept_class_files:
        raise ValueError(
            "No 'classes' folder with classes.csv files found in the ZIP file."
        )

    for file_path in dept_class_files:
        # Extract department name from path: 'classes/department/classes.csv'
        path_parts = file_path.split("/")
        if len(path_parts) >= 3:
            department_name = path_parts[1]

            try:
                department = Department.objects.get(slug=department_name)

                # Read CSV content from ZIP
                csv_content = zip_ref.read(file_path)
                csv_io = io.StringIO(csv_content.decode("utf-8"))
                process_department_class_csv_memory(csv_io, department)

            except Department.DoesNotExist:
                print(f"Department {department_name} does not exist in the database.")


def process_department_class_file(extracted_dir):
    department_class_path = os.path.join(extracted_dir, "classes")
    if os.path.isdir(department_class_path):
        for department_name in os.listdir(department_class_path):
            department_path = os.path.join(department_class_path, department_name)
            if os.path.isdir(department_path):
                class_file_path = os.path.join(department_path, "classes.csv")
                if os.path.isfile(class_file_path):
                    try:
                        department = Department.objects.get(slug=department_name)
                        process_department_class_csv(class_file_path, department)
                    except Department.DoesNotExist:
                        print(
                            f"Department {department_name} does not exist in the database."
                        )


def validate_and_restructure_course_code(course_code, course_title):
    """
    Validates and restructures a course code into the format: ABC 123
    Handles optional suffixes like "(ELECTIVE)" and multiple codes like "URP 213/URP 211"
    Returns the first valid course code when multiple are provided.
    
    Args:
        course_code (str): The course code to validate and restructure
        
    Returns:
        str: The restructured course code in format "ABC 123"
        
    Raises:
        ValueError: If the course code is invalid
    """
    import re
    
    # Remove extra whitespace and convert to uppercase
    cleaned = str(course_code).strip().upper()
    
    # Remove anything in parentheses (like "(ELECTIVE)")
    cleaned = re.sub(r'\s*\([^)]*\)', '', cleaned)
    
    # Handle multiple course codes separated by slash - take the first one
    if '/' in cleaned:
        cleaned = cleaned.split('/')[0].strip()
    
    # Remove all remaining spaces to parse the components
    no_spaces = cleaned.replace(" ", "")
    
    # Check if it matches the pattern: 3 letters followed by 3 digits
    pattern = r'^([A-Z]{3})(\d{3})$'
    match = re.match(pattern, no_spaces)
    
    if not match:
        raise ValueError(
            f"Invalid course code: '{course_code}'. '{course_title}'"
            "Expected format: 3 letters followed by 3 digits (e.g., GNS 101)"
        )
    
    # Extract components and format
    department = match.group(1)
    course_number = match.group(2)
    
    return f"{department} {course_number}"

def process_class_course_csv_memory(csv_io, class_obj):
    """Process class course CSV from memory with bulk operations"""
    from django.db import transaction

    # Read CSV content into pandas DataFrame
    csv_io.seek(0)
    df = pd.read_csv(csv_io)

    # Validate and restructure all course codes with error handling
    validated_codes = []
    invalid_rows = []
    
    for idx, row in df.iterrows():
        try:
            validated_codes.append(validate_and_restructure_course_code(row["COURSE CODE"], row["COURSE TITLE"]))
        except ValueError as e:
            validated_codes.append(None)  # Placeholder for invalid codes
            invalid_rows.append(idx)
    
    # Assign validated codes back to DataFrame
    df["COURSE CODE"] = validated_codes
    
    # Remove rows with invalid course codes
    if invalid_rows:
        df = df.drop(invalid_rows)
        # Optionally log or raise warning about skipped rows
        print(f"Warning: Skipped {len(invalid_rows)} rows with invalid course codes")
    
    # Remove any remaining None values and duplicates
    df = df.dropna(subset=["COURSE CODE"])
    df = df.drop_duplicates(subset=["COURSE CODE"])

    # Extract unique course codes
    course_codes = df["COURSE CODE"].tolist()

    # Get existing courses in a single query
    existing_courses = Course.objects.filter(code__in=course_codes)
    existing_codes = set(existing_courses.values_list("code", flat=True))

    # Prepare new courses to create
    new_courses = []
    for _, row in df.iterrows():
        code = row["COURSE CODE"]
        if code not in existing_codes:
            new_courses.append(
                Course(name=row["COURSE TITLE"], code=code, exam_type=row["EXAM TYPE"])
            )

    # Bulk create new courses
    if new_courses:
        Course.objects.bulk_create(new_courses, ignore_conflicts=True)

    # Get all courses (existing + newly created) in one query
    all_courses = Course.objects.filter(code__in=course_codes)

    # Bulk add to many-to-many relationship
    with transaction.atomic():
        class_obj.courses.add(*all_courses)

def process_class_course_csv(file_path, class_obj):
    file = pd.read_csv(file_path).to_dict()
    for key in file["COURSE CODE"]:
        code = file["COURSE CODE"][key]
        name = file["COURSE TITLE"][key]
        exam_type = file["EXAM TYPE"][key]
        course, created = Course.objects.get_or_create(
            name=name.strip(), code=code.strip(), exam_type=exam_type.strip()
        )
        class_obj.courses.add(course)


def process_department_class_csv_memory(csv_io, department):
    """Process department class CSV from memory"""
    import pandas as pd

    # Read CSV content into pandas DataFrame
    csv_io.seek(0)  # Reset to beginning
    df = pd.read_csv(csv_io)
    file_dict = df.to_dict()

    clasess = []

    for key in file_dict["Name"]:
        cls = Class(
            name=file_dict["Name"][key].strip(),
            department=department,
            size=file_dict["Size"][key],
        )
        clasess.append(cls)
    Class.objects.bulk_create(clasess)


def process_department_class_csv(class_file_path, department):
    file = pd.read_csv(class_file_path).to_dict()
    for key in file["Name"]:
        Class.objects.update_or_create(
            name=file["Name"][key], department=department, size=file["Size"][key]
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
    max_attempts=10000,
    *,
    adjacency_mode="8-dir",
    attempts_pass2=100,
    attempts_pass3=300,
    attempts_pass4=500,
    success_threshold_pct=60,
    pattern_order=None,
):
    """
    Optimized seat allocation with multi-pass approach.
    `adjacency_mode` controls which neighbouring cells block same-course placement.
    """
    if not students:  # Check if students list is empty
        return {}, students, 0  # Return all students as unplaced with 0% placement

    if pattern_order is None:
        pattern_order = ["checkerboard", "diagonal", "sequential"]
    directions = _ADJACENCY_DIRECTIONS.get(adjacency_mode, _ADJACENCY_DIRECTIONS["8-dir"])

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

    def is_valid_position(student_name, row, col):
        """Adjacency check honoring the configured mode."""
        if not directions:  # adjacency_mode == "off"
            return True
        course = next(
            student["course"] for student in students if student["name"] == student_name
        )
        for dr, dc in directions:
            r, c = row + dr, col + dc
            if 0 <= r < rows and 0 <= c < cols and seats[r][c]:
                adjacent_student = next(
                    student for student in students if student["name"] == seats[r][c]
                )
                if adjacent_student["course"] == course:
                    return False
        return True

    def try_pattern_placement(course_students, pattern="checkerboard"):
        """Try to place students using specific patterns"""
        placed = 0

        if pattern == "checkerboard":
            # Try checkerboard pattern (every other seat)
            positions = [
                (r, c)
                for r in range(rows)
                for c in range(cols)
                if (r + c) % 2 == 0 and not seats[r][c]
            ]
        elif pattern == "diagonal":
            # Try diagonal pattern
            positions = [
                (r, c)
                for r in range(rows)
                for c in range(cols)
                if r % 2 == c % 2 and not seats[r][c]
            ]
        else:
            # Sequential pattern
            positions = [
                (r, c) for r in range(rows) for c in range(cols) if not seats[r][c]
            ]

        random.shuffle(positions)

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

    def try_random_placement(remaining_students, attempts_per_student=100):
        """Try random placement with STRICT adjacency constraints"""
        placed = 0

        for student in remaining_students:
            if student_positions[student["name"]] is not None:
                continue  # Already placed

            for _ in range(attempts_per_student):
                row, col = random.randint(0, rows - 1), random.randint(0, cols - 1)
                if not seats[row][col] and is_valid_position(student["name"], row, col):
                    seats[row][col] = student["name"]
                    student_positions[student["name"]] = (row, col)
                    placed += 1
                    break

        return placed

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
                for r in range(rows)
                for c in range(cols)
                if r % 2 == ro and c % 2 == co and not seats[r][c]
            ]
            for ro in (0, 1)
            for co in (0, 1)
        }
        courses_sorted = sorted(
            course_groups.items(),
            key=lambda kv: -sum(
                1 for s in kv[1] if student_positions[s["name"]] is None
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
    total_placed += try_quarter_placement()

    # Pass 1: Pattern-based placement per course in admin-configured order
    for course, course_students in course_groups.items():
        random.shuffle(course_students)  # Randomize within course

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

    # Pass 2: Random placement with constraint-respecting placement
    remaining_students = [s for s in students if student_positions[s["name"]] is None]
    if remaining_students:
        placed = try_random_placement(remaining_students, attempts_pass2)
        total_placed += placed

    # Pass 3: More attempts
    remaining_students = [s for s in students if student_positions[s["name"]] is None]
    if remaining_students:
        placed = try_random_placement(remaining_students, attempts_pass3)
        total_placed += placed

    # Pass 4: Final attempt with the highest budget
    remaining_students = [s for s in students if student_positions[s["name"]] is None]
    if remaining_students:
        placed = try_random_placement(remaining_students, attempts_pass4)
        total_placed += placed

    # NOTE: Removed relaxed and force placement passes to maintain strict adjacency constraints
    # Students that cannot be placed while maintaining constraints will remain unplaced

    # Convert positions to sequential seat numbers
    def index_to_seat(row, col):
        return row * cols + col + 1

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


def print_seating_arrangement(
    students,
    rows,
    cols,
    date,
    period,
    hall_id,
    *,
    adjacency_mode="8-dir",
    attempts_pass2=100,
    attempts_pass3=300,
    attempts_pass4=500,
    success_threshold_pct=60,
    pattern_order=None,
):
    from .models import Student  # Import here to avoid circular imports

    result = allocate_students_to_seats(
        students, rows, cols,
        adjacency_mode=adjacency_mode,
        attempts_pass2=attempts_pass2,
        attempts_pass3=attempts_pass3,
        attempts_pass4=attempts_pass4,
        success_threshold_pct=success_threshold_pct,
        pattern_order=pattern_order,
    )
    if result is None:
        print("Error: allocate_students_to_seats returned None.")
        return

    seat_positions, unplaced_students, percentage_placed = result

    print(f"Percentage of students placed: {percentage_placed:.2f}%")

    if seat_positions:
        # Group students by course
        courses = sorted(set(student["course"] for student in students))
        course_groups = {course: [] for course in courses}
        for student_name, seat in seat_positions.items():
            student_data = next(s for s in students if s["name"] == student_name)
            course = student_data["course"]
            cls_id = student_data["cls_id"]
            student_id = student_data.get("student_id")
            course_groups[course].append((student_name, seat, cls_id, student_id))

        # Print sorted by course and create SeatArrangement objects
        print("\nSeating Arrangement:")
        for course in courses:
            print(f"\n{course}:")
            arrangements = []
            for student_name, seat, cls_id, student_id in sorted(
                course_groups[course], key=lambda x: x[0]
            ):
                # Get the actual Student instance if student_id exists
                student_instance = None
                if student_id:
                    try:
                        student_instance = Student.objects.get(id=student_id)
                    except Student.DoesNotExist:
                        student_instance = None

                arrangements.append(
                    SeatArrangement(
                        date=date,
                        period=period,
                        student=student_instance,  # Use actual Student instance
                        seat_number=seat,
                        hall=Hall.objects.get(id=hall_id),
                        course=Course.objects.filter(code=course).first(),
                        cls=Class.objects.get(id=cls_id),
                    )
                )
                print(f"{student_name}: {seat}")
            SeatArrangement.objects.bulk_create(arrangements)

    # Group and sort unplaced students by course
    unplaced_by_course = {}
    for student_name in unplaced_students:
        student_data = next(s for s in students if s["name"] == student_name)
        course = student_data["course"]
        cls_id = student_data["cls_id"]
        student_id = student_data.get("student_id")
        if course not in unplaced_by_course:
            unplaced_by_course[course] = []
        unplaced_by_course[course].append((student_name, cls_id, student_id))

    # Print unplaced students sorted by course and create SeatArrangement objects
    if unplaced_students:
        print("\nUnplaced Students:")
        for course in sorted(unplaced_by_course.keys()):
            print(f"\n{course}:")
            arrangements = []
            for student_name, cls_id, student_id in sorted(unplaced_by_course[course]):
                # Get the actual Student instance if student_id exists
                student_instance = None
                if student_id:
                    try:
                        student_instance = Student.objects.get(id=student_id)
                    except Student.DoesNotExist:
                        student_instance = None

                arrangements.append(
                    SeatArrangement(
                        date=date,
                        period=period,
                        student=student_instance,  # Use actual Student instance
                        hall=Hall.objects.get(id=hall_id),
                        course=Course.objects.filter(code=course).first(),
                        cls=Class.objects.get(id=cls_id),
                    )
                )
                print(student_name)
            SeatArrangement.objects.bulk_create(arrangements)


def generate_seat_allocation(rows: int, cols: int, students):
    random.seed(0)
    # Ensure the total number of students does not exceed rows * cols
    if len(students) > rows * cols:
        print(
            f"Error: Too many students for the given hall capacity of {rows * cols} seats."
        )
    else:
        # Print the seating arrangement
        print_seating_arrangement(students, rows, cols)


def is_valid_position(seat_number, course_code, seat_map, rows, cols):
    """
    Check if a seat position is valid for manual assignment based on adjacency constraints.

    Args:
        seat_number (int): The seat number to check (1-based)
        course_code (str): The course code of the student to be placed
        seat_map (dict): Dictionary mapping seat numbers to course codes
        rows (int): Number of rows in the hall
        cols (int): Number of columns in the hall

    Returns:
        bool: True if the position is valid, False otherwise
    """
    # Convert seat number to row, col (0-based)
    seat_index = seat_number - 1
    row = seat_index // cols
    col = seat_index % cols

    # Define adjacency directions (8-directional)
    directions = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]

    for dr, dc in directions:
        adj_row, adj_col = row + dr, col + dc

        # Check if adjacent position is within bounds
        if 0 <= adj_row < rows and 0 <= adj_col < cols:
            # Convert back to seat number
            adj_seat_number = adj_row * cols + adj_col + 1

            # Check if there's a student in the adjacent seat with the same course
            if adj_seat_number in seat_map and seat_map[adj_seat_number] == course_code:
                return False

    return True


def get_student_number(dep_slug, cls, num):
    student_number = ""
    if cls.name.startswith("N"):
        student_number += "N/"
    elif cls.name.startswith("P"):
        student_number += "PN/"
    else:
        student_number += "H/"
    student_number += f"{dep_slug}/{num:04}"
    return student_number


###################################
##### STUDENT BULK UPLOAD ########
###################################


def process_student_files_memory(zip_ref):
    """Process student files from ZIP in memory with comprehensive validation"""
    import io
    import re

    from django.db import transaction

    from .models import Class, Student

    # Look for 'students/department/class.csv' files in ZIP
    student_files = [
        f
        for f in zip_ref.namelist()
        if f.startswith("students/") and f.endswith(".csv")
    ]

    if not student_files:
        raise ValueError(
            "No 'students' folder with CSV files found in the ZIP file.\nPlease ensure your ZIP contains a 'students' folder with department subfolders containing CSV files named after class names."
        )

    # Pre-validation phase
    validation_results = []
    valid_files = []

    for file_path in student_files:
        # Extract department slug and class filename from path: 'students/department-slug/ClassName.csv'
        path_parts = file_path.split("/")
        if len(path_parts) < 3:
            continue  # Skip files not inside a department subfolder
        department_slug = path_parts[1]
        csv_filename = path_parts[2]
        try:
            # Read CSV content from ZIP, trying multiple encodings
            csv_content = zip_ref.read(file_path)
            csv_io = None
            for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
                try:
                    csv_io = io.StringIO(csv_content.decode(encoding))
                    break
                except (UnicodeDecodeError, LookupError):
                    continue
            if csv_io is None:
                raise ValueError("Unable to decode CSV file with any supported encoding (utf-8, cp1252, latin-1)")

            validation_result = validate_student_csv_memory(csv_io, csv_filename, department_slug)
            validation_results.append(validation_result)
            if validation_result["is_valid"]:
                # Reset StringIO for processing
                csv_io.seek(0)
                valid_files.append((csv_io, validation_result))
        except Exception as e:
            validation_results.append(
                {
                    "file_name": csv_filename,
                    "department_slug": department_slug,
                    "is_valid": False,
                    "errors": [f"Failed to validate file: {str(e)}"],
                }
            )

    # Check if any files failed validation
    failed_validations = [r for r in validation_results if not r["is_valid"]]
    if failed_validations:
        error_messages = []
        for result in failed_validations:
            dept = result.get("department_slug", "unknown")
            error_messages.append(f"File '{result['file_name']}' (department: {dept}):")
            for error in result["errors"]:
                error_messages.append(f"  • {error}")

        raise ValueError(
            "Validation failed for one or more files:\n\n" + "\n".join(error_messages)
        )

    # Process all valid files in a single transaction
    try:
        with transaction.atomic():
            total_created = 0
            total_updated = 0

            for csv_io, validation_result in valid_files:
                class_obj = validation_result["class_obj"]
                try:
                    created, updated = process_validated_student_csv_memory(
                        csv_io, validation_result
                    )
                except ValueError as e:
                    raise ValueError(
                        f"Error in file '{validation_result['file_name']}' "
                        f"(class: {class_obj.name}, department: {class_obj.department.name}): {e}"
                    )
                total_created += created
                total_updated += updated

            return {
                "success": True,
                "message": f"Successfully processed {len(valid_files)} files. Created: {total_created}, Updated: {total_updated} students.",
                "files_processed": len(valid_files),
                "students_created": total_created,
                "students_updated": total_updated,
            }
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Failed to process student files: {str(e)}")
    """Process student files with comprehensive validation"""
    import re

    from django.db import transaction

    from .models import Class, Student

    students_dir = os.path.join(extracted_dir, "students")
    if not os.path.exists(students_dir):
        raise ValueError(
            "No 'students' folder found in the uploaded ZIP file.\nPlease ensure your ZIP contains a 'students' folder with department subfolders containing CSV files named after class names."
        )

    # Collect all CSV files inside department subfolders: students/department-slug/ClassName.csv
    department_dirs = [
        d for d in os.listdir(students_dir)
        if os.path.isdir(os.path.join(students_dir, d))
    ]
    if not department_dirs:
        raise ValueError(
            "No department subfolders found in the 'students' folder.\nPlease add department subfolders named after department slugs, each containing CSV files named after class names."
        )

    csv_file_entries = []  # list of (file_path, csv_filename, department_slug)
    for dept_slug in department_dirs:
        dept_path = os.path.join(students_dir, dept_slug)
        for csv_file in os.listdir(dept_path):
            if csv_file.endswith(".csv"):
                csv_file_entries.append((os.path.join(dept_path, csv_file), csv_file, dept_slug))

    if not csv_file_entries:
        raise ValueError(
            "No CSV files found in any department subfolder.\nPlease add CSV files named after your class names (e.g., 'ND1 Computer Science.csv')."
        )

    # Pre-validation phase
    validation_results = []
    valid_files = []

    for file_path, csv_file, dept_slug in csv_file_entries:
        try:
            validation_result = validate_student_csv(file_path, dept_slug)
            validation_results.append(validation_result)
            if validation_result["is_valid"]:
                valid_files.append((file_path, validation_result))
        except Exception as e:
            validation_results.append(
                {
                    "file_name": csv_file,
                    "department_slug": dept_slug,
                    "is_valid": False,
                    "errors": [f"Failed to validate file: {str(e)}"],
                }
            )

    # Check if any files failed validation
    failed_validations = [r for r in validation_results if not r["is_valid"]]
    if failed_validations:
        error_messages = []
        for result in failed_validations:
            dept = result.get("department_slug", "unknown")
            error_messages.append(f"File '{result['file_name']}' (department: {dept}):")
            for error in result["errors"]:
                error_messages.append(f"  • {error}")

        raise ValueError(
            "Validation failed for one or more files:\n\n" + "\n".join(error_messages)
        )

    # Process all valid files in a single transaction
    try:
        with transaction.atomic():
            total_created = 0
            total_updated = 0

            for file_path, validation_result in valid_files:
                class_obj = validation_result["class_obj"]
                try:
                    created, updated = process_validated_student_csv(
                        file_path, validation_result
                    )
                except ValueError as e:
                    raise ValueError(
                        f"Error in file '{validation_result['file_name']}' "
                        f"(class: {class_obj.name}, department: {class_obj.department.name}): {e}"
                    )
                total_created += created
                total_updated += updated

            return {
                "success": True,
                "message": f"Successfully processed {len(valid_files)} files. Created: {total_created}, Updated: {total_updated} students.",
                "files_processed": len(valid_files),
                "students_created": total_created,
                "students_updated": total_updated,
            }
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Failed to process student files: {str(e)}")


def validate_student_csv_memory(csv_io, file_name, department_slug):
    """Validate a student CSV file from memory without making database changes"""
    import re

    from .models import Class, Student

    errors = []

    # Extract class name from filename (remove .csv extension)
    class_name = file_name.replace(".csv", "")

    # Check if class exists within the given department
    try:
        class_obj = Class.objects.get(name=class_name, department__slug=department_slug)
    except Class.DoesNotExist:
        return {
            "file_name": file_name,
            "department_slug": department_slug,
            "is_valid": False,
            "errors": [
                f"Class '{class_name}' not found in department '{department_slug}'. Please ensure the CSV filename matches an existing class name and is placed in the correct department subfolder."
            ],
        }

    # Try to read CSV from memory
    try:
        csv_io.seek(0)  # Reset to beginning
        df = pd.read_csv(
            csv_io,
            dtype={
                "MATRIC NUMBER": "string",
                "FIRSTNAME": "string",
                "LASTNAME": "string",
                "EMAIL": "string",
                "PHONE NUMBER": "string",
            },
            engine="c",
        )
        df = df.astype(str).apply(lambda x: x.str.strip())
    except Exception as e:
        return {
            "file_name": file_name,
            "department_slug": department_slug,
            "is_valid": False,
            "errors": [f"Cannot read CSV file: {str(e)}"],
        }

    # Check if file is empty
    if len(df) == 0:
        errors.append("CSV file is empty")

    # Check required columns
    required_columns = [
        "MATRIC NUMBER",
        "FIRSTNAME",
        "LASTNAME",
        "EMAIL",
        "PHONE NUMBER",
    ]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        errors.append(f"Missing required columns: {', '.join(missing_columns)}")

    if errors:  # Return early if basic structure is invalid
        return {
            "file_name": file_name,
            "department_slug": department_slug,
            "is_valid": False,
            "errors": errors,
            "class_obj": class_obj,
        }

    # Silently drop rows with empty required fields (EMAIL is optional - auto-generated if missing)
    required_non_email = [col for col in required_columns if col != "EMAIL"]
    for col in required_non_email:
        df = df[~(df[col].isna() | df[col].str.strip().isin(["", "nan", "None"]))]

    # Silently deduplicate matric numbers (keep first occurrence)
    df = df.drop_duplicates(subset=["MATRIC NUMBER"], keep="first")

    # Check for existing students in this class
    matric_numbers = df["MATRIC NUMBER"].tolist()
    existing_in_class = Student.objects.filter(
        matric_no__in=matric_numbers, level=class_obj
    ).values_list("matric_no", flat=True)

    if existing_in_class:
        errors.append(
            f"Students already exist in class '{class_name}': {', '.join(list(existing_in_class)[:5])}{'...' if len(existing_in_class) > 5 else ''}"
        )

    # Check for existing matric numbers in database
    existing_matrics = (
        Student.objects.filter(matric_no__in=matric_numbers)
        .exclude(level=class_obj)
        .values_list("matric_no", flat=True)
    )

    if existing_matrics:
        errors.append(
            f"Matric numbers already exist in other classes: {', '.join(list(existing_matrics)[:5])}{'...' if len(existing_matrics) > 5 else ''}"
        )

    return {
        "file_name": file_name,
        "department_slug": department_slug,
        "is_valid": len(errors) == 0,
        "errors": errors,
        "class_obj": class_obj,
        "student_data": df if len(errors) == 0 else None,
        "student_count": len(df),
    }


def validate_student_csv(file_path, department_slug):
    """Validate a student CSV file without making database changes"""
    import re

    from .models import Class, Student

    file_name = os.path.basename(file_path)
    errors = []

    # Extract class name from filename (remove .csv extension)
    class_name = file_name.replace(".csv", "")

    # Check if class exists within the given department
    try:
        class_obj = Class.objects.get(name=class_name, department__slug=department_slug)
    except Class.DoesNotExist:
        return {
            "file_name": file_name,
            "department_slug": department_slug,
            "is_valid": False,
            "errors": [
                f"Class '{class_name}' not found in department '{department_slug}'. Please ensure the CSV filename matches an existing class name and is placed in the correct department subfolder."
            ],
        }

    # Try to read CSV with multiple encoding fallbacks
    df = None
    last_error = None
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            df = pd.read_csv(
                file_path,
                encoding=encoding,
                dtype={
                    "MATRIC NUMBER": "string",
                    "FIRSTNAME": "string",
                    "LASTNAME": "string",
                    "EMAIL": "string",
                    "PHONE NUMBER": "string",
                },
                engine="c",
            )
            df = df.astype(str).apply(lambda x: x.str.strip())
            break
        except UnicodeDecodeError as e:
            last_error = e
            continue
        except Exception as e:
            return {
                "file_name": file_name,
                "department_slug": department_slug,
                "is_valid": False,
                "errors": [f"Cannot read CSV file: {str(e)}"],
            }
    if df is None:
        return {
            "file_name": file_name,
            "department_slug": department_slug,
            "is_valid": False,
            "errors": [f"Cannot read CSV file: {str(last_error)}"],
        }

    # Check if file is empty
    if len(df) == 0:
        errors.append("CSV file is empty")

    # Check required columns
    required_columns = [
        "MATRIC NUMBER",
        "FIRSTNAME",
        "LASTNAME",
        "EMAIL",
        "PHONE NUMBER",
    ]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        errors.append(f"Missing required columns: {', '.join(missing_columns)}")

    if errors:  # Return early if basic structure is invalid
        return {
            "file_name": file_name,
            "is_valid": False,
            "errors": errors,
            "class_obj": class_obj,
        }

    # Silently drop rows with empty required fields (EMAIL is optional - auto-generated if missing)
    required_non_email = [col for col in required_columns if col != "EMAIL"]
    for col in required_non_email:
        df = df[~(df[col].isna() | df[col].str.strip().isin(["", "nan", "None"]))]

    # Silently deduplicate matric numbers (keep first occurrence)
    df = df.drop_duplicates(subset=["MATRIC NUMBER"], keep="first")

    # Check for existing students in this class
    matric_numbers = df["MATRIC NUMBER"].tolist()
    existing_in_class = Student.objects.filter(
        matric_no__in=matric_numbers, level=class_obj
    ).values_list("matric_no", flat=True)

    if existing_in_class:
        errors.append(
            f"Students already exist in class '{class_name}': {', '.join(list(existing_in_class)[:5])}{'...' if len(existing_in_class) > 5 else ''}"
        )

    # Check for existing matric numbers in database
    existing_matrics = (
        Student.objects.filter(matric_no__in=matric_numbers)
        .exclude(level=class_obj)
        .values_list("matric_no", flat=True)
    )

    if existing_matrics:
        errors.append(
            f"Matric numbers already exist in other classes: {', '.join(list(existing_matrics)[:5])}{'...' if len(existing_matrics) > 5 else ''}"
        )

    return {
        "file_name": file_name,
        "is_valid": len(errors) == 0,
        "errors": errors,
        "class_obj": class_obj,
        "student_data": df if len(errors) == 0 else None,
        "student_count": len(df),
    }


def process_validated_student_csv_memory(csv_io, validation_result):
    """Process a validated student CSV file from memory"""
    from django.db import IntegrityError, transaction

    from .models import Student

    class_obj = validation_result["class_obj"]
    df = validation_result["student_data"]

    # Convert to records for processing
    student_records = df.to_dict("records")

    # Process in chunks for better memory management
    chunk_size = 250
    total_created = 0
    total_updated = 0

    for i in range(0, len(student_records), chunk_size):
        chunk = student_records[i : i + chunk_size]
        students_to_create = []

        for record in chunk:
            raw_email = str(record["EMAIL"]).strip().replace(" ", "").replace(",", "").lower()
            if not raw_email or raw_email in ["nan", "none", ""]:
                first = str(record["FIRSTNAME"]).strip().lower().replace(" ", "")
                last = str(record["LASTNAME"]).strip().lower().replace(" ", "")
                matric = str(record["MATRIC NUMBER"]).strip().replace("/", "").replace(" ", "")
                raw_email = f"{first}{last}{matric}@ems.com"
            students_to_create.append(
                Student(
                    matric_no=record["MATRIC NUMBER"],
                    first_name=record["FIRSTNAME"],
                    last_name=record["LASTNAME"],
                    email=raw_email,
                    phone=record["PHONE NUMBER"],
                    department=class_obj.department,
                    level=class_obj,
                )
            )

        # Bulk create students for this chunk
        if students_to_create:
            try:
                with transaction.atomic():
                    Student.objects.bulk_create(students_to_create, batch_size=250)
            except IntegrityError:
                matric_numbers = [s.matric_no for s in students_to_create]
                existing = (
                    Student.objects.filter(matric_no__in=matric_numbers)
                    .values("matric_no", "level__name", "department__name")
                )
                conflicts = ", ".join(
                    f"{r['matric_no']} (class: {r['level__name']}, dept: {r['department__name']})"
                    for r in existing
                )
                raise ValueError(
                    f"Duplicate matric number(s) found while uploading to class '{class_obj.name}' "
                    f"(department: {class_obj.department.name}): {conflicts}"
                )
            total_created += len(students_to_create)

    return total_created, total_updated


def process_validated_student_csv(file_path, validation_result):
    """Process a validated student CSV file"""
    from django.db import IntegrityError, transaction

    from .models import Student

    class_obj = validation_result["class_obj"]
    df = validation_result["student_data"]

    # Convert to records for processing
    student_records = df.to_dict("records")

    # Process in chunks for better memory management
    chunk_size = 250
    total_created = 0
    total_updated = 0

    for i in range(0, len(student_records), chunk_size):
        chunk = student_records[i : i + chunk_size]
        students_to_create = []

        for record in chunk:
            raw_email = str(record["EMAIL"]).strip().replace(" ", "").replace(",", "").lower()
            if not raw_email or raw_email in ["nan", "none", ""]:
                first = str(record["FIRSTNAME"]).strip().lower().replace(" ", "")
                last = str(record["LASTNAME"]).strip().lower().replace(" ", "")
                matric = str(record["MATRIC NUMBER"]).strip().replace("/", "").replace(" ", "")
                raw_email = f"{first}{last}{matric}@ems.com"
            students_to_create.append(
                Student(
                    matric_no=record["MATRIC NUMBER"],
                    first_name=record["FIRSTNAME"],
                    last_name=record["LASTNAME"],
                    email=raw_email,
                    phone=record["PHONE NUMBER"],
                    department=class_obj.department,
                    level=class_obj,
                )
            )

        # Bulk create students for this chunk
        if students_to_create:
            try:
                with transaction.atomic():
                    Student.objects.bulk_create(students_to_create, batch_size=250)
            except IntegrityError:
                matric_numbers = [s.matric_no for s in students_to_create]
                existing = (
                    Student.objects.filter(matric_no__in=matric_numbers)
                    .values("matric_no", "level__name", "department__name")
                )
                conflicts = ", ".join(
                    f"{r['matric_no']} (class: {r['level__name']}, dept: {r['department__name']})"
                    for r in existing
                )
                raise ValueError(
                    f"Duplicate matric number(s) found while uploading to class '{class_obj.name}' "
                    f"(department: {class_obj.department.name}): {conflicts}"
                )
            total_created += len(students_to_create)

    return total_created, total_updated


# Legacy function for backward compatibility
def process_student_csv(file_path, class_obj, department_slug):
    """Legacy function - use validate_student_csv and process_validated_student_csv instead"""
    validation_result = validate_student_csv(file_path, department_slug)
    if not validation_result["is_valid"]:
        raise ValueError(f"Validation failed: {'; '.join(validation_result['errors'])}")

    return process_validated_student_csv(file_path, validation_result)


def reconcile_unplaced(date, period):
    """Cross-hall reconciliation: seat any students left unplaced in one
    hall into another hall (same date/period) that still has empty cells
    *and* room for that course's quarter.

    Runs after every hall has been allocated independently. Walks every
    ``SeatArrangement`` row with ``seat_number=NULL`` and, course-by-course,
    finds a destination hall whose empty parity quarter can absorb the
    student without breaking 8-dir same-course adjacency.

    Returns the number of students reseated.
    """
    from .models import SeatArrangement, Hall

    unplaced_qs = (
        SeatArrangement.objects.filter(
            date=date, period=period, seat_number__isnull=True
        )
        .select_related("course", "cls", "hall")
        .order_by("course_id")
    )
    if not unplaced_qs.exists():
        return 0

    halls = list(Hall.objects.all())

    # Build per-hall occupancy maps once.
    hall_state: dict[int, dict] = {}
    for hall in halls:
        r, c = hall.rows, hall.columns
        grid = [[None] * c for _ in range(r)]
        existing = SeatArrangement.objects.filter(
            date=date, period=period, hall=hall, seat_number__isnull=False
        ).select_related("course")
        for sa in existing:
            seat = sa.seat_number - 1  # 1-based → 0-based
            row, col = divmod(seat, c)
            if 0 <= row < r and 0 <= col < c:
                grid[row][col] = sa.course_id
        # Free cells grouped by parity quarter.
        quarters: dict[tuple[int, int], list[tuple[int, int]]] = {
            (ro, co): [] for ro in (0, 1) for co in (0, 1)
        }
        for row in range(r):
            for col in range(c):
                if grid[row][col] is None:
                    quarters[(row % 2, col % 2)].append((row, col))
        # Per-quarter occupancy of course_ids so we don't seat a student in
        # a quarter that already has same-course students stuck there.
        quarter_courses: dict[tuple[int, int], set[int]] = {
            (ro, co): set() for ro in (0, 1) for co in (0, 1)
        }
        for row in range(r):
            for col in range(c):
                cid = grid[row][col]
                if cid is not None:
                    quarter_courses[(row % 2, col % 2)].add(cid)
        hall_state[hall.id] = {
            "rows": r,
            "cols": c,
            "grid": grid,
            "quarters": quarters,
            "quarter_courses": quarter_courses,
        }

    reseated = 0
    for sa in unplaced_qs:
        target_id = None
        target_pos = None
        target_quarter = None
        # Prefer halls with the most empty cells and a quarter that already
        # has this course (extending an existing same-course quarter is
        # always safe) or any quarter the course hasn't entered.
        sorted_halls = sorted(
            hall_state.items(),
            key=lambda kv: -sum(len(v) for v in kv[1]["quarters"].values()),
        )
        for hall_id, state in sorted_halls:
            quarters = state["quarters"]
            qcourses = state["quarter_courses"]
            # Try quarters that already host this course first — guaranteed
            # safe (cells inside one quarter are never 8-dir adjacent).
            preferred = [
                key for key, courses in qcourses.items()
                if sa.course_id in courses and quarters[key]
            ]
            fallback = [
                key for key, courses in qcourses.items()
                if sa.course_id not in courses and quarters[key]
            ]
            for key in preferred + fallback:
                row, col = quarters[key].pop()
                state["grid"][row][col] = sa.course_id
                qcourses[key].add(sa.course_id)
                target_id = hall_id
                target_pos = (row, col)
                target_quarter = key
                break
            if target_id is not None:
                break
        if target_id is None:
            continue  # genuinely no room anywhere
        del target_quarter  # only used while choosing
        # Persist the move.
        row, col = target_pos
        cols = hall_state[target_id]["cols"]
        sa.hall_id = target_id
        sa.seat_number = row * cols + col + 1
        sa.save(update_fields=["hall_id", "seat_number"])
        reseated += 1

    return reseated
