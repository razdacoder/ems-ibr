"""Benchmark the greedy timetable generator against the CP-SAT one.

Reads courses, classes, halls and the saved generation constraints straight
from a pg_dump file (default ``ordo.sql``), so no database is needed. Both
generators get the same inputs and the same distribution fit check, and the
same scorer judges both.

    .venv/bin/python scripts/bench_timetable.py                 # real window
    .venv/bin/python scripts/bench_timetable.py --days 14 12 10 # tighter
    .venv/bin/python scripts/bench_timetable.py --seeds 10 --time-limit 60
"""

import argparse
import contextlib
import io
import json
import os
import random
import statistics
import sys
import time
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

import django  # noqa: E402

django.setup()

from ems import seating_rules  # noqa: E402
from ems.models import GenerationConstraints  # noqa: E402
from ems.seating_rules import RELAXED  # noqa: E402
from ems.timetable_cpsat import generate_cpsat  # noqa: E402
from ems.utils import (  # noqa: E402
    classify_courses,
    convert_hall_to_dict,
    course_rule,
    courses_short_of_halls,
    generate,
    get_total_seats,
    hall_effective_capacity,
    split_course,
)


# ---------------------------------------------------------------- dump data

def read_copy(dump: Path, table: str) -> list[dict]:
    rows, cols, inside = [], None, False
    with dump.open(encoding="utf-8") as fh:
        for line in fh:
            if not inside:
                if line.startswith(f"COPY public.{table} ("):
                    cols = [c.strip() for c in line.split("(", 1)[1].split(")")[0].split(",")]
                    inside = True
                continue
            if line.startswith("\\."):
                break
            values = line.rstrip("\n").split("\t")
            rows.append({c: (None if v == "\\N" else v) for c, v in zip(cols, values)})
    return rows


def load(dump: Path):
    faculties = {r["id"]: r["slug"] for r in read_copy(dump, "ems_faculty")}
    departments = {
        r["id"]: {"slug": r["slug"], "faculty": faculties.get(r["faculty_id"])}
        for r in read_copy(dump, "ems_department")
    }
    classes = {}
    for r in read_copy(dump, "ems_class"):
        dept = departments.get(r["department_id"], {})
        classes[r["id"]] = {
            "id": int(r["id"]),
            "name": r["name"],
            "size": int(r["size"] or 0),
            "department_slug": dept.get("slug"),
            "faculty_slug": dept.get("faculty"),
        }
    course_rows = {r["id"]: r for r in read_copy(dump, "ems_course")}
    members: dict = {}
    for r in read_copy(dump, "ems_class_courses"):
        if r["class_id"] in classes:
            members.setdefault(r["course_id"], []).append(r["class_id"])
    halls = [
        SimpleNamespace(
            id=int(r["id"]), name=r["name"], capacity=int(r["capacity"] or 0),
            rows=int(r["rows"]), columns=int(r["columns"]),
            layout=None, group="", seat_order="rows",
        )
        for r in read_copy(dump, "ems_hall")
    ]
    saved = read_copy(dump, "ems_generationconstraints")[0]
    constraints = GenerationConstraints(
        cbe_autosplit_threshold=int(saved["cbe_autosplit_threshold"]),
        cbe_fullday_threshold=int(saved["cbe_fullday_threshold"]),
        cbe_daily_cap_per_period=int(saved["cbe_daily_cap_per_period"]),
        pbe_hall_utilization=float(saved["pbe_hall_utilization"]),
        excluded_weekdays=json.loads(saved["excluded_weekdays"]),
        class_period_overrides=json.loads(saved["class_period_overrides"]),
        cbe_faculty_groups=json.loads(saved["cbe_faculty_groups"]),
        cbe_group_count=int(saved["cbe_group_count"]),
        seat_pattern=saved["seat_pattern"],
    )
    timetable_dates = sorted({r["date"] for r in read_copy(dump, "ems_timetable")})

    def fresh_courses():
        out = []
        for cid, row in course_rows.items():
            ids = members.get(cid)
            if ids:
                out.append({
                    "id": int(cid), "code": row["code"], "exam_type": row["exam_type"],
                    "classes": [dict(classes[k]) for k in ids],
                })
        return out

    return fresh_courses, halls, constraints, timetable_dates


# ------------------------------------------------------------------ scoring

def score(schedules, all_courses, dates, seats, constraints, fit_check):
    """Same yardstick for both generators."""
    size = lambda c: sum(k["size"] for k in c["classes"])  # noqa: E731
    day_index = {d: i for i, d in enumerate(dates)}
    planned = {}
    for s in schedules:
        planned.setdefault(s["course"]["code"], s)
    total = len(all_courses)
    total_students = sum(size(c) for c in all_courses)
    sched_students = sum(size(s["course"]) for s in planned.values())

    # Hard-rule check.
    violations = 0
    class_days: dict = {}
    for s in planned.values():
        for k in s["course"]["classes"]:
            class_days.setdefault(k["id"], []).append(day_index[s["date"]])
    for days in class_days.values():
        violations += len(days) - len(set(days))
    slot_seats: dict = {}
    slot_relaxed: dict = {}
    for s in schedules:
        if s["course"]["exam_type"] == "PBE":
            key = (s["date"], s["period"])
            slot_seats[key] = slot_seats.get(key, 0) + size(s["course"])
            if course_rule(s["course"]) == RELAXED:
                slot_relaxed[key] = slot_relaxed.get(key, 0) + 1
    violations += sum(1 for v in slot_seats.values() if v > seats)
    violations += sum(1 for v in slot_relaxed.values() if v > 1)

    # Distribution fit check per slot.
    slot_courses: dict = {}
    for s in schedules:
        if s["course"]["exam_type"] == "PBE":
            slot_courses.setdefault((s["date"], s["period"]), []).append(s["course"])
    misfits = sum(len(fit_check(cs)) for cs in slot_courses.values())

    # Spread, per class.
    b2b = gap1 = 0
    classes_with_b2b = 0
    min_gaps = []
    for days in class_days.values():
        days = sorted(set(days))
        diffs = [b - a for a, b in zip(days, days[1:])]
        n = sum(1 for g in diffs if g == 1)
        b2b += n
        gap1 += sum(1 for g in diffs if g == 2)
        classes_with_b2b += n > 0
        if diffs:
            min_gaps.append(min(diffs))
    used_days = {day_index[s["date"]] for s in schedules}
    return {
        "courses_scheduled": len(planned),
        "courses_total": total,
        "courses_unscheduled": total - len(planned),
        "students_unscheduled": total_students - sched_students,
        "hard_violations": violations,
        "fit_misfits": misfits,
        "back_to_back": b2b,
        "one_day_gaps": gap1,
        "classes_with_back_to_back": classes_with_b2b,
        "avg_min_gap_days": round(statistics.mean(min_gaps), 2) if min_gaps else 0,
        "days_used": len(used_days),
    }


# ------------------------------------------------------------------ running

def make_dates(start, count, excluded):
    out, d = [], start
    while len(out) < count:
        if d.weekday() not in excluded:
            out.append(d)
        d += timedelta(days=1)
    return out


def prepare(fresh_courses, halls, constraints):
    courses = fresh_courses()
    sizes = [(h.rows, h.columns, h.layout) for h in halls]
    courses, refused = classify_courses(
        courses, seating_rules.strict_limit(sizes), seating_rules.relaxed_limit(sizes)
    )
    am, pm = split_course(courses, class_period_overrides=constraints.class_period_overrides)
    return am, pm, refused


def run(name, fn, fresh_courses, halls, hall_dicts, constraints, dates, fit_check, **extra):
    am, pm, _refused = prepare(fresh_courses, halls, constraints)
    all_courses = am + pm
    kwargs = dict(
        autosplit_threshold=constraints.cbe_autosplit_threshold,
        fullday_threshold=constraints.cbe_fullday_threshold,
        daily_cap=constraints.cbe_daily_cap_per_period,
        pbe_utilization=float(constraints.pbe_hall_utilization),
        cbe_group_count=constraints.cbe_group_count,
        cbe_faculty_groups=constraints.cbe_faculty_groups or {},
        save=False, fit_check=fit_check, **extra,
    )
    t0 = time.perf_counter()
    with contextlib.redirect_stdout(io.StringIO()):
        summary = fn(dates, am, pm, hall_dicts, **kwargs)
    seconds = time.perf_counter() - t0
    seats = get_total_seats(hall_dicts, utilization=kwargs["pbe_utilization"])
    # Score against the CBE sections actually planned (after auto-split).
    planned_codes = {s["course"]["code"] for s in summary["schedules"]}
    universe = [s["course"] for s in summary["schedules"]]
    seen = set(planned_codes)
    for c in all_courses:
        if c["code"] not in seen and not any(
            code.startswith(c["code"] + "-G") for code in planned_codes
        ):
            universe.append(c)
            seen.add(c["code"])
    uniq = {c["code"]: c for c in universe}
    result = score(summary["schedules"], list(uniq.values()), dates, seats, constraints, fit_check)
    result["seconds"] = round(seconds, 2)
    result["status"] = summary.get("solver_status", "-")
    result["alpha"] = summary.get("alpha")
    result["fit_rounds"] = summary.get("fit_rounds")
    result["spread_bound"] = summary.get("spread_bound")
    result["timings"] = summary.get("timings")
    result["fit_checks_run"] = summary.get("fit_checks_run")
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump", default=str(ROOT / "ordo.sql"))
    ap.add_argument("--days", type=int, nargs="*", help="exam-day counts to test")
    ap.add_argument("--seeds", type=int, default=10, help="greedy runs per scenario")
    ap.add_argument("--time-limit", type=float, default=30.0, help="CP-SAT phase 1 seconds")
    ap.add_argument("--spread-time", type=float, default=120.0, help="CP-SAT phase 2 seconds")
    ap.add_argument("--out", help="write results JSON here")
    args = ap.parse_args()

    fresh_courses, halls, constraints, real_dates = load(Path(args.dump))
    excluded = set(constraints.excluded_weekdays or [])
    start = date.fromisoformat(real_dates[0])
    real_window = []
    d = start
    while d <= date.fromisoformat(real_dates[-1]):
        if d.weekday() not in excluded:
            real_window.append(d)
        d += timedelta(days=1)
    day_counts = args.days or [len(real_window)]

    hall_dicts = [
        {"id": h.id, "name": h.name, "capacity": hall_effective_capacity(
            h.rows, h.columns, constraints.seat_pattern, h.capacity, mask=h.layout)}
        for h in halls
    ]

    def fit_check(period_courses):
        halls_now = convert_hall_to_dict(
            halls, safety_factor=float(constraints.pbe_hall_utilization),
            pattern=constraints.seat_pattern,
            course_limits=constraints.hall_course_limits,
        )
        return courses_short_of_halls(
            period_courses, halls_now, group_order=constraints.hall_group_order,
            small_course_threshold=constraints.small_course_threshold,
        )

    am, pm, refused = prepare(fresh_courses, halls, constraints)
    per_class: dict = {}
    for c in am + pm:
        for k in c["classes"]:
            per_class[k["id"]] = per_class.get(k["id"], 0) + 1
    print(f"Data: {len(am) + len(pm)} courses ({len(am)} AM, {len(pm)} PM), "
          f"{len(halls)} halls, {len(per_class)} classes, refused oversized: {len(refused)}")
    print(f"Busiest class sits {max(per_class.values())} exams "
          f"-> no plan can fit everything in fewer days.\n")

    results = {}
    for n in day_counts:
        dates = make_dates(start, n, excluded)
        print(f"=== {n} exam days ({dates[0]} .. {dates[-1]}) ===")
        floor = sum(max(0, k - (n + 1) // 2) for k in per_class.values())
        print(f"  Floor: at least {floor} back-to-back days are unavoidable "
              f"(a class with k exams in {n} days needs k - ceil({n}/2) of them)")
        greedy_runs = []
        for seed in range(args.seeds):
            random.seed(seed)
            greedy_runs.append(run("greedy", generate, fresh_courses, halls,
                                   hall_dicts, constraints, dates, fit_check))
            print(f"  greedy seed {seed}: {greedy_runs[-1]['courses_unscheduled']} unscheduled, "
                  f"{greedy_runs[-1]['back_to_back']} back-to-back, {greedy_runs[-1]['seconds']}s")
        cpsat = run("cpsat", generate_cpsat, fresh_courses, halls, hall_dicts,
                    constraints, dates, fit_check, time_limit=args.time_limit,
                    spread_time_limit=args.spread_time)
        print(f"  cp-sat: {cpsat['courses_unscheduled']} unscheduled, "
              f"{cpsat['back_to_back']} back-to-back, {cpsat['seconds']}s, {cpsat['status']}, "
              f"alpha={cpsat['alpha']}, fit rounds={cpsat['fit_rounds']}, "
              f"proven penalty bound={cpsat['spread_bound']}")
        results[n] = {"greedy": greedy_runs, "cpsat": cpsat}
        print_table(greedy_runs, cpsat)
    if args.out:
        Path(args.out).write_text(json.dumps(results, indent=2, default=str))
        print(f"Results written to {args.out}")


def print_table(greedy_runs, cpsat):
    keys = [
        ("courses_unscheduled", "Courses unscheduled", "low"),
        ("students_unscheduled", "Students unscheduled", "low"),
        ("hard_violations", "Hard-rule violations", "low"),
        ("fit_misfits", "Slots failing fit check", "low"),
        ("back_to_back", "Back-to-back exam days", "low"),
        ("classes_with_back_to_back", "Classes with a back-to-back", "low"),
        ("one_day_gaps", "One-day gaps", "low"),
        ("avg_min_gap_days", "Avg tightest gap (days)", "high"),
        ("days_used", "Days used", "-"),
        ("seconds", "Runtime (s)", "low"),
    ]
    print(f"\n  {'Metric':30} {'Greedy mean':>12} {'best':>8} {'worst':>8} {'CP-SAT':>9}")
    for key, label, better in keys:
        vals = [r[key] for r in greedy_runs]
        best = min(vals) if better != "high" else max(vals)
        worst = max(vals) if better != "high" else min(vals)
        print(f"  {label:30} {statistics.mean(vals):12.2f} {best:8} {worst:8} {cpsat[key]:9}")
    print()


if __name__ == "__main__":
    main()
