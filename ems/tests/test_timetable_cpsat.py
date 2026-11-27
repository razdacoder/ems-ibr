"""CP-SAT timetabler (ems.timetable_cpsat): same rules as the greedy."""
from datetime import date, timedelta

from django.test import SimpleTestCase

from ems.seating_rules import RELAXED, STRICT
from ems.timetable_cpsat import generate_cpsat

DAYS = [date(2026, 8, 17) + timedelta(days=i) for i in range(4)]
HALLS = [{"id": 1, "name": "A", "capacity": 100}]


def course(code, classes, exam_type="PBE", rule=STRICT):
    return {
        "id": hash(code), "code": code, "exam_type": exam_type,
        "seating_rule": rule,
        "classes": [{"id": cid, "name": f"C{cid}", "size": size} for cid, size in classes],
    }


def plan(am, pm=(), dates=DAYS, **kw):
    kw.setdefault("time_limit", 10)
    kw.setdefault("spread_time_limit", 10)
    return generate_cpsat(dates, list(am), list(pm), HALLS, pbe_utilization=1.0,
                          save=False, workers=1, **kw)


class CpsatRulesTests(SimpleTestCase):
    def test_a_class_sits_one_exam_a_day(self):
        result = plan([course(f"X{i}", [(1, 10)]) for i in range(4)])
        days = [s["date"] for s in result["schedules"]]
        self.assertEqual(len(days), 4)
        self.assertEqual(len(set(days)), 4)

    def test_seat_total_per_period_is_respected(self):
        result = plan([course(f"X{i}", [(i, 60)]) for i in range(4)])
        per_day = {}
        for s in result["schedules"]:
            per_day[s["date"]] = per_day.get(s["date"], 0) + 60
        self.assertTrue(all(v <= 100 for v in per_day.values()))
        self.assertEqual(result["am_skipped"], 0)

    def test_reports_what_cannot_fit(self):
        # One class, five exams, four days: one must be left out.
        result = plan([course(f"X{i}", [(1, 10)]) for i in range(5)])
        self.assertEqual(result["am_skipped"], 1)

    def test_one_relaxed_course_per_period(self):
        result = plan(
            [course(f"R{i}", [(i, 10)], rule=RELAXED) for i in range(4)],
            dates=DAYS[:2],
        )
        per_day = {}
        for s in result["schedules"]:
            per_day[s["date"]] = per_day.get(s["date"], 0) + 1
        self.assertTrue(all(v <= 1 for v in per_day.values()))
        self.assertEqual(result["am_skipped"], 2)

    def test_full_day_cbe_takes_both_periods_alone(self):
        big = course("BIG", [(1, 3000), (2, 3000)], exam_type="CBE")
        small = course("SMALL", [(3, 100)], exam_type="CBE")
        result = plan([big, small], dates=DAYS[:2], fullday_threshold=4500)
        big_rows = [s for s in result["schedules"] if s["course"]["code"] == "BIG"]
        self.assertEqual({s["period"] for s in big_rows}, {"AM", "PM"})
        small_day = next(s["date"] for s in result["schedules"] if s["course"]["code"] == "SMALL")
        self.assertNotEqual(small_day, big_rows[0]["date"])

    def test_spreads_a_classes_exams_apart(self):
        # Two exams, four days: the best plan leaves at least a day between.
        result = plan([course("A", [(1, 10)]), course("B", [(1, 10)])])
        days = sorted(s["date"] for s in result["schedules"])
        self.assertGreaterEqual((days[1] - days[0]).days, 2)

    def test_fit_check_is_honoured(self):
        # A fit check that refuses any period holding more than two courses.
        def fit_check(courses):
            return courses[2:]

        result = plan([course(f"X{i}", [(i, 5)]) for i in range(6)],
                      dates=DAYS[:3], fit_check=fit_check)
        per_day = {}
        for s in result["schedules"]:
            per_day[s["date"]] = per_day.get(s["date"], 0) + 1
        self.assertTrue(all(v <= 2 for v in per_day.values()))
        self.assertEqual(result["am_skipped"], 0)

    def test_a_stale_initial_alpha_cannot_drop_courses(self):
        # An alpha far too big would rule out every period; it is capped so
        # the greedy's plan stays legal, and nothing is lost.
        result = plan([course(f"X{i}", [(i, 30)]) for i in range(6)],
                      dates=DAYS[:2], initial_alpha=1000,
                      fit_check=lambda courses: [])
        self.assertEqual(result["am_skipped"], 0)
        self.assertLess(result["alpha"], 1000)

    def test_reports_time_per_step(self):
        result = plan([course("A", [(1, 10)])])
        self.assertEqual(
            set(result["timings"]), {"greedy", "phase1", "phase2", "fit_check"}
        )
