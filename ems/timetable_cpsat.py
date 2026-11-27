"""Exam timetabling with a constraint solver (Google OR-Tools CP-SAT).

An alternative to the randomized greedy :func:`ems.utils.generate`. It takes
the same inputs and returns the same summary shape, so a caller can switch
between the two. Nothing here changes how ``generate`` behaves.

The model
---------
One 0/1 variable ``x[course, day]`` says "this course sits on this day". The
period comes from the course's pool (AM or PM, decided by ``split_course``);
a full-day CBE paper takes both periods of its day.

Hard rules, the same ones the greedy enforces:
  * a course sits at most once;
  * a class sits at most one exam a day;
  * paper (PBE) students in one period fit the period's seat total;
  * at most one relaxed course per period;
  * a full-day CBE paper has its day to itself (no other CBE that day);
  * smaller CBE papers share a day up to ``daily_cap`` students;
  * every period passes ``fit_check`` (the real distribution packer). That
    check is not linear, so it runs after each solve: a period that fails it
    gets a cut forbidding that exact set of courses together, and the model
    is solved again.

Objective, in priority order:
  1. schedule as many courses as possible;
  2. then as many students as possible;
  3. then as few back-to-back days as possible for any class (exams on two
     dates next to each other in ``dates``), with a smaller penalty for a
     one-day gap.

Unlike the greedy, the solver can prove a plan is optimal, or that no plan
fits every course into the dates given.
"""

import time

from ortools.sat.python import cp_model

from .seating_rules import RELAXED
from .utils import (
    auto_split_large_cbe_courses,
    course_rule,
    get_total_seats,
    refuse_oversized_cbe,
    save_to_timetable_db,
)

# Objective weights. A scheduled course must outweigh every spread penalty
# put together, and a student must outweigh them too, so these are
# lexicographic in practice.
W_BACK_TO_BACK = 10
W_ONE_DAY_GAP = 1


def _size(course):
    return sum(cls["size"] for cls in course["classes"])


def generate_cpsat(
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
    time_limit=60.0,
    spread_time_limit=60.0,
    repair_time_limit=15.0,
    initial_alpha=0.0,
    max_fit_rounds=20,
    workers=8,
    seed=0,
    spread=True,
    warm_start=True,
    log=False,
):
    """Plan the timetable for ``dates`` with CP-SAT. Same arguments and
    summary as :func:`ems.utils.generate`, plus:

    ``time_limit``      seconds per phase 1 solve;
    ``spread_time_limit`` seconds for the first phase 2 solve;
    ``repair_time_limit`` seconds for each later phase 2 solve, after a fit
                        check failure (it starts from an almost-done plan);
    ``initial_alpha``   per-course seat overhead learned on an earlier run
                        (the summary's ``alpha``). Passing it back skips most
                        fit-check rounds;
    ``max_fit_rounds``  how many times to re-solve after ``fit_check`` cuts;
    ``workers``/``seed`` solver threads and random seed;
    ``spread``          add the back-to-back penalties (False = only fit);
    ``warm_start``      run the greedy first and start the solver from its
                        plan, so the result is never worse than the greedy's.

    It solves in two phases: first the most courses and students, then,
    holding that, the fewest back-to-back days (``time_limit`` each).

    The summary also carries ``solver_status`` ("OPTIMAL" when phase 1 was
    proven best and phase 2 too, "FALLBACK" when time ran out and the best
    plan already known was kept), ``fit_rounds``, ``alpha`` (the learned
    per-course seat overhead), ``spread_bound`` (a proven lower bound on the
    spread penalty), ``solve_seconds`` and ``timings`` (seconds per step).
    """
    started = time.perf_counter()
    timings = {"greedy": 0.0, "phase1": 0.0, "phase2": 0.0, "fit_check": 0.0}
    dates = list(dates)
    n_days = len(dates)

    # Same pre-processing as the greedy, so both plan the same papers.
    split = dict(
        autosplit_threshold=autosplit_threshold,
        group_count=cbe_group_count,
        faculty_groups=cbe_faculty_groups,
    )
    courses_AM = auto_split_large_cbe_courses(courses_AM, **split)
    courses_PM = auto_split_large_cbe_courses(courses_PM, **split)
    courses_AM, refused_cbe = refuse_oversized_cbe(courses_AM, autosplit_threshold)
    courses_PM, refused_pm = refuse_oversized_cbe(courses_PM, autosplit_threshold)
    refused_cbe += refused_pm

    items = [(c, "AM") for c in courses_AM] + [(c, "PM") for c in courses_PM]
    seats = get_total_seats(Halls, utilization=pbe_utilization)

    def kind(course):
        if course["exam_type"] != "CBE":
            return "PBE"
        return "CBE_FULL" if _size(course) > fullday_threshold else "CBE"

    pbe_slots = {
        period: [
            i for i, (c, p) in enumerate(items) if p == period and kind(c) == "PBE"
        ]
        for period in ("AM", "PM")
    }
    full = [i for i, (c, _p) in enumerate(items) if kind(c) == "CBE_FULL"]
    small = [i for i, (c, _p) in enumerate(items) if kind(c) == "CBE"]
    by_class: dict = {}
    for i, (course, _p) in enumerate(items):
        for cls in course["classes"]:
            by_class.setdefault(cls["id"], set()).add(i)
    total_students = sum(_size(c) for c, _p in items)

    # What the fit check has taught us. `alpha` is seats lost per course in
    # a period: the packer cannot fill halls to the last seat once course
    # limits and the one-quarter-per-course rule bite, so a period passes
    # roughly when students + alpha * courses <= seats. It starts at 0 and
    # rises just enough to rule out every period that failed, but never so
    # far that it rules out one that passed. `nogoods` are exact sets that
    # failed, for whatever alpha cannot separate.
    alpha = float(initial_alpha or 0.0)
    failed_shapes: list = []  # (students, courses) of periods that failed
    passed_shapes: list = []  # ... and that passed
    nogoods: list = []        # (day, [item indexes])

    def blank():
        return {(i, d): 0 for i in range(len(items)) for d in range(n_days)}

    # Warm start: the greedy's plan is a valid starting point (it already
    # passed the fit check), and the best plan known until CP-SAT beats it.
    hint = None
    if warm_start:
        import contextlib
        import io

        from .utils import generate

        index = {id(c): i for i, (c, _p) in enumerate(items)}
        t0 = time.perf_counter()
        with contextlib.redirect_stdout(io.StringIO()):
            greedy = generate(
                dates, list(courses_AM), list(courses_PM), Halls,
                autosplit_threshold=autosplit_threshold,
                fullday_threshold=fullday_threshold, daily_cap=daily_cap,
                pbe_utilization=pbe_utilization, cbe_group_count=cbe_group_count,
                cbe_faculty_groups=cbe_faculty_groups, save=False,
                fit_check=fit_check,
            )
        timings["greedy"] = time.perf_counter() - t0
        hint = blank()
        day_index = {d: n for n, d in enumerate(dates)}
        shapes: dict = {}
        for row in greedy["schedules"]:
            i = index.get(id(row["course"]))
            if i is None:
                continue
            hint[i, day_index[row["date"]]] = 1
            if kind(row["course"]) == "PBE":
                st, n = shapes.get((row["date"], row["period"]), (0, 0))
                shapes[row["date"], row["period"]] = (st + _size(row["course"]), n + 1)
        # Every greedy period passed the fit check: alpha must keep them legal.
        passed_shapes.extend(shapes.values())
        # An alpha from an earlier run must not rule out this greedy plan.
        alpha = min(
            [alpha] + [(seats - st) / n for st, n in shapes.values() if n]
        )

    def build():
        model = cp_model.CpModel()
        x = {
            (i, d): model.NewBoolVar(f"x_{i}_{d}")
            for i in range(len(items))
            for d in range(n_days)
        }
        scheduled = []
        for i in range(len(items)):
            s = model.NewBoolVar(f"s_{i}")
            model.Add(sum(x[i, d] for d in range(n_days)) == s)
            scheduled.append(s)
        # A class sits at most one exam a day.
        day_of = {}
        for k, members in by_class.items():
            for d in range(n_days):
                expr = sum(x[i, d] for i in members)
                model.Add(expr <= 1)
                day_of[k, d] = expr
        scale = 100  # alpha in hundredths, CP-SAT wants integers
        a = int(round(alpha * scale))
        for d in range(n_days):
            for period, pbe in pbe_slots.items():
                model.Add(
                    sum((scale * _size(items[i][0]) + a) * x[i, d] for i in pbe)
                    <= scale * seats
                )
                relaxed = [i for i in pbe if course_rule(items[i][0]) == RELAXED]
                if len(relaxed) > 1:
                    model.Add(sum(x[i, d] for i in relaxed) <= 1)
            full_today = sum(x[i, d] for i in full)
            model.Add(full_today <= 1)
            # A full-day paper leaves no room for any other CBE that day.
            model.Add(
                sum(_size(items[i][0]) * x[i, d] for i in small)
                <= daily_cap - daily_cap * full_today
            )
        for d, slot in nogoods:
            model.Add(sum(x[i, d] for i in slot) <= len(slot) - 1)
        primary = (total_students + 1) * sum(scheduled) + sum(
            _size(c) * scheduled[i] for i, (c, _p) in enumerate(items)
        )
        penalty = []
        if spread:
            for k in by_class:
                for d in range(n_days - 1):
                    b = model.NewBoolVar(f"b2b_{k}_{d}")
                    model.Add(b >= day_of[k, d] + day_of[k, d + 1] - 1)
                    penalty.append(W_BACK_TO_BACK * b)
                    if d + 2 < n_days:
                        g = model.NewBoolVar(f"gap_{k}_{d}")
                        model.Add(g >= day_of[k, d] + day_of[k, d + 2] - 1)
                        penalty.append(W_ONE_DAY_GAP * g)
        return model, x, primary, sum(penalty)

    fit_cache: dict = {}

    def cached_fit(slot):
        """fit_check for one period's items. The packer's answer depends
        only on which courses sit together, so repeats come from the cache."""
        key = frozenset(slot)
        if key not in fit_cache:
            t0 = time.perf_counter()
            fit_cache[key] = fit_check([items[i][0] for i in slot])
            timings["fit_check"] += time.perf_counter() - t0
        return fit_cache[key]

    def to_schedules(values):
        out = []
        for (i, d), on in values.items():
            if on:
                course, period = items[i]
                if kind(course) == "CBE_FULL":
                    out.append({"course": course, "date": dates[d], "period": "AM"})
                    out.append({"course": course, "date": dates[d], "period": "PM"})
                else:
                    out.append({"course": course, "date": dates[d], "period": period})
        return out

    def make_solver(limit):
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = float(limit)
        solver.parameters.num_search_workers = int(workers)
        solver.parameters.random_seed = int(seed)
        solver.parameters.log_search_progress = bool(log)
        return solver

    fit_rounds = 0
    status_name = "UNKNOWN"
    spread_bound = None
    best_known = hint  # last plan known to pass the fit check
    # Phase 2 only runs once a phase 1 plan has passed the fit check, so the
    # rounds that are still learning the fit rule stay cheap.
    polish = False
    polished = False  # a full phase 2 solve has run
    while True:
        # Phase 1: schedule as much as possible.
        model, x, primary, penalty = build()
        if hint:
            for key, value in hint.items():
                model.AddHint(x[key], value)
        model.Maximize(primary)
        solver = make_solver(time_limit)
        t0 = time.perf_counter()
        status = solver.Solve(model)
        timings["phase1"] += time.perf_counter() - t0
        status_name = solver.StatusName(status)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            if best_known is None:
                raise RuntimeError(f"CP-SAT found no plan (status {status_name})")
            # Out of time with nothing better: keep the best plan known.
            status_name = "FALLBACK"
            values = best_known
            schedules = to_schedules(values)
            break
        best_primary = int(solver.ObjectiveValue())
        values = {key: solver.Value(var) for key, var in x.items()}

        # Phase 2: keep that, and spread each class's exams out.
        if spread and polish:
            model.Add(primary >= best_primary)
            model.ClearHints()
            for key, value in values.items():
                model.AddHint(x[key], value)
            model.Minimize(penalty)
            # The first polish gets the full budget; a repair after a fit
            # failure starts from an almost-done plan and needs far less.
            solver = make_solver(repair_time_limit if polished else spread_time_limit)
            t0 = time.perf_counter()
            status = solver.Solve(model)
            timings["phase2"] += time.perf_counter() - t0
            polished = True
            if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                values = {key: solver.Value(var) for key, var in x.items()}
                spread_bound = int(solver.BestObjectiveBound())
                if status_name == "OPTIMAL" and status != cp_model.OPTIMAL:
                    status_name = "FEASIBLE"
        hint = values
        schedules = to_schedules(values)
        failed = []
        for d in range(n_days if fit_check else 0):
            for pbe in pbe_slots.values():
                slot = [i for i in pbe if values[i, d]]
                if not slot:
                    continue
                shape = (sum(_size(items[i][0]) for i in slot), len(slot))
                misfits = cached_fit(slot)
                if misfits:
                    failed.append((d, slot, misfits))
                    failed_shapes.append(shape)
                else:
                    passed_shapes.append(shape)
        if not failed:
            best_known = values
            if spread and not polish:
                polish = True
                continue
            break
        fit_rounds += 1
        if fit_rounds > max_fit_rounds:
            # Out of rounds. The last plan that passed the fit check is
            # complete; prefer it. Without one, drop the misfits, as the
            # greedy leaves them unplaced when no later date has room.
            if best_known is not None:
                status_name = "FALLBACK"
                schedules = to_schedules(best_known)
                break
            for d, _slot, misfits in failed:
                ids = {id(c) for c in misfits}
                schedules = [
                    s for s in schedules
                    if not (s["date"] == dates[d] and id(s["course"]) in ids)
                ]
            break
        # Learn: raise alpha to rule out the failed shapes, unless that
        # would also rule out a shape known to pass.
        ceiling = min(
            ((seats - st) / n for st, n in passed_shapes if n), default=float("inf")
        )
        needs = [
            (seats - st) / n + 0.01 for st, n in failed_shapes
            if n and (seats - st) / n + 0.01 <= ceiling
        ]
        if needs:
            alpha = max(alpha, max(needs))
        for d, slot, _m in failed:
            nogoods.append((d, slot))

    if on_date_planned:
        on_date_planned(n_days, n_days)

    planned = {id(s["course"]) for s in schedules}
    left_AM = [c for c in courses_AM if id(c) not in planned]
    left_PM = [c for c in courses_PM if id(c) not in planned]

    if save:
        save_to_timetable_db(schedules)

    summary = {
        "total_scheduled": len(schedules),
        "am_scheduled": len(courses_AM) - len(left_AM),
        "pm_scheduled": len(courses_PM) - len(left_PM),
        "am_skipped": len(left_AM),
        "pm_skipped": len(left_PM),
        "skipped_am_codes": [c["code"] for c in left_AM],
        "skipped_pm_codes": [c["code"] for c in left_PM],
        "relaxed_courses": [
            {
                "code": s["course"]["code"],
                "date": str(s["date"]),
                "period": s["period"],
                "students": _size(s["course"]),
            }
            for s in schedules
            if course_rule(s["course"]) == RELAXED
        ],
        "refused_cbe": refused_cbe,
        "rebooked_after_fit_check": 0,
        "solver_status": status_name,
        "alpha": round(alpha, 2),
        "spread_bound": spread_bound,
        "fit_rounds": fit_rounds,
        "solve_seconds": round(time.perf_counter() - started, 2),
        "timings": {k: round(v, 2) for k, v in timings.items()},
        "fit_checks_run": len(fit_cache),
    }
    if not save:
        summary["schedules"] = schedules
    return summary
