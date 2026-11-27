"""How fast can CP-SAT go without losing quality? Runtime vs result for a few
solver settings, on the real data in ordo.sql.

    .venv/bin/python -u scripts/bench_cpsat_speed.py              # 14 days
    .venv/bin/python -u scripts/bench_cpsat_speed.py --days 12

"cold" runs start knowing nothing; "warm" runs get the alpha the cold run
learned, as a school's second generation would if alpha were stored.
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import bench_timetable as b  # noqa: E402  (sets up Django)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump", default=str(b.ROOT / "ordo.sql"))
    ap.add_argument("--days", type=int, default=14)
    ap.add_argument("--spread", type=float, nargs="*", default=[120, 60, 30, 15],
                    help="phase 2 time limits to try on warm runs")
    ap.add_argument("--out")
    args = ap.parse_args()

    fresh, halls, cons, real = b.load(Path(args.dump))
    dates = b.make_dates(date.fromisoformat(real[0]), args.days,
                         set(cons.excluded_weekdays or []))
    hall_dicts = [
        {"id": h.id, "name": h.name, "capacity": b.hall_effective_capacity(
            h.rows, h.columns, cons.seat_pattern, h.capacity, mask=h.layout)}
        for h in halls
    ]

    def fit_check(period_courses):
        halls_now = b.convert_hall_to_dict(
            halls, safety_factor=float(cons.pbe_hall_utilization),
            pattern=cons.seat_pattern, course_limits=cons.hall_course_limits,
        )
        return b.courses_short_of_halls(
            period_courses, halls_now, group_order=cons.hall_group_order,
            small_course_threshold=cons.small_course_threshold,
        )

    def cpsat(label, **kw):
        r = b.run("cpsat", b.generate_cpsat, fresh, halls, hall_dicts, cons,
                  dates, fit_check, time_limit=30, **kw)
        r["label"] = label
        t = r["timings"]
        print(f"{label:28} {r['seconds']:7.1f}s  unsched={r['courses_unscheduled']:<3} "
              f"b2b={r['back_to_back']:<5} gaps1={r['one_day_gaps']:<4} "
              f"rounds={r['fit_rounds']} alpha={r['alpha']} status={r['status']}  "
              f"[greedy {t['greedy']}s, p1 {t['phase1']}s, p2 {t['phase2']}s, "
              f"fit {t['fit_check']}s / {r['fit_checks_run']} checks]", flush=True)
        return r

    print(f"=== {args.days} days ({dates[0]} .. {dates[-1]}) ===", flush=True)
    rows = [cpsat("cold, spread 60s", spread_time_limit=60)]
    alpha = rows[0]["alpha"]
    for limit in args.spread:
        rows.append(cpsat(f"warm a={alpha}, spread {limit:g}s",
                          spread_time_limit=limit, initial_alpha=alpha))
    if args.out:
        Path(args.out).write_text(json.dumps(rows, indent=2, default=str))


if __name__ == "__main__":
    main()
