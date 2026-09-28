"""Relaxed seating for courses too big for one period (spec 0002).

A paper course above the strict per course limit is seated on the even
parity half of each hall with only side, front and back neighbours blocked.
At most one per period; a course above even that limit is refused.
"""
import random
from datetime import date

from django.test import RequestFactory, TestCase
from django.urls import reverse

from ems import seating_rules, tasks
from ems.csv_gen import export_arrangements
from ems.models import Hall, SeatArrangement, TimeTable
from ems.seating_rules import RELAXED, RELAXED_SHEET_LINE, STRICT
from ems.utils import (
    _quarters_can_seat,
    allocate_students_to_seats,
    classify_courses,
    convert_hall_to_dict,
    distribute_classes_to_halls,
    generate,
    get_courses,
    get_halls,
    reconcile_unplaced,
    relaxed_course_code,
    split_course,
)

from .helpers import enrol, listed_class, make_course, make_department, make_hall, quietly, schedule
from .test_attendance_sheets import read_sheets
from .test_student_lists import PipelineTestCase, allow_generation, run

DATE, PERIOD = "2026-08-17", "AM"
EIGHT = seating_rules.neighbours(STRICT)
FOUR = seating_rules.neighbours(RELAXED)


def four_halls():
    """Four 10 x 10 halls: strict limit 4 x 25 = 100, relaxed limit 4 x 50 = 200."""
    for n in range(4):
        make_hall(f"Room {n}", 10, 10)


def course_with(code, *sizes):
    """A paper course taken by one listed class per size, linked the way
    class course uploads link them (the course's classes)."""
    course = make_course(code)
    classes = []
    for size in sizes:
        cls = listed_class(size, make_department())
        cls.courses.add(course)
        classes.append(cls)
    return course, classes


def seat_grid(seat_positions, students, cols):
    """seat number map -> {(row, col): course}"""
    course_of = {s["name"]: s["course"] for s in students}
    return {divmod(seat - 1, cols): course_of[name] for name, seat in seat_positions.items()}


def conflicts(grid, course, offsets):
    """Pairs of same course students within ``offsets`` of each other."""
    return [
        (cell, (cell[0] + dr, cell[1] + dc))
        for cell, c in grid.items()
        if c == course
        for dr, dc in offsets
        if grid.get((cell[0] + dr, cell[1] + dc)) == course
    ]


def students_for(bites):
    """[(course, count)] -> allocator input, matric order within each course."""
    return [
        {"student_id": None, "name": f"{course}-{n:04}", "course": course, "cls_id": 1}
        for course, count in bites
        for n in range(count)
    ]


class SeatingRuleTests(TestCase):
    def test_even_half_counts_quarters_00_and_11(self):
        self.assertEqual(seating_rules.even_half(10, 10), 50)
        self.assertEqual(seating_rules.even_half(5, 5), 9 + 4)
        self.assertEqual(seating_rules.even_half(7, 10), 4 * 5 + 3 * 5)
        self.assertEqual(seating_rules.even_half(0, 10), 0)

    def test_limits_sum_over_the_halls(self):
        halls = [(10, 10), (7, 10), (1, 30)]
        # A 1 row hall counts 0 toward the strict limit.
        self.assertEqual(seating_rules.strict_limit(halls), 25 + 15)
        self.assertEqual(seating_rules.relaxed_limit(halls), 50 + 35 + 15)

    def test_classify_switches_one_student_past_each_limit(self):
        self.assertEqual(seating_rules.classify(100, 100, 200), STRICT)
        self.assertEqual(seating_rules.classify(101, 100, 200), RELAXED)
        self.assertEqual(seating_rules.classify(200, 100, 200), RELAXED)
        self.assertEqual(seating_rules.classify(201, 100, 200), "refused")

    def test_relaxed_blocks_only_side_front_and_back(self):
        self.assertEqual(sorted(FOUR), [(-1, 0), (0, -1), (0, 1), (1, 0)])
        self.assertEqual(len(EIGHT), 8)

    def test_even_seats_never_share_an_edge(self):
        seats = set(seating_rules.even_seats(7, 9))
        self.assertEqual(len(seats), seating_rules.even_half(7, 9))
        for r, c in seats:
            for dr, dc in FOUR:
                self.assertNotIn((r + dr, c + dc), seats)


class RelaxedQuarterUsageTests(TestCase):
    """relaxed_quarter_usage must match where the allocator actually seats a
    relaxed course, for every bite size, or the distribution model drifts."""

    def test_matches_the_allocator_for_every_k_on_odd_and_even_halls(self):
        for rows, cols in [(5, 5), (6, 6), (7, 10), (4, 7)]:
            for k in range(seating_rules.even_half(rows, cols) + 1):
                with self.subTest(rows=rows, cols=cols, k=k):
                    students = students_for([("R", k)])
                    seats, unplaced, _ = quietly(
                        allocate_students_to_seats, students, rows, cols,
                        relaxed_courses={"R"},
                    )
                    self.assertEqual(unplaced, [])
                    cells = [divmod(s - 1, cols) for s in seats.values()]
                    actual = (
                        sum(1 for r, c in cells if r % 2 == 0 and c % 2 == 0),
                        sum(1 for r, c in cells if r % 2 == 1 and c % 2 == 1),
                    )
                    self.assertEqual(
                        seating_rules.relaxed_quarter_usage(rows, cols, k), actual
                    )


class QuartersModelTests(TestCase):
    def test_a_relaxed_course_fills_the_even_half_and_strict_courses_the_rest(self):
        bites = [("R", 50), ("A", 25), ("B", 25)]
        self.assertTrue(_quarters_can_seat(10, 10, bites, relaxed_course="R"))

    def test_the_same_bite_is_refused_under_the_strict_rule(self):
        self.assertFalse(_quarters_can_seat(10, 10, [("R", 50)]))

    def test_a_relaxed_bite_bigger_than_the_even_half_is_refused(self):
        self.assertFalse(_quarters_can_seat(10, 10, [("R", 51)], relaxed_course="R"))

    def test_strict_courses_only_get_what_the_relaxed_course_left(self):
        # R's 50 seats fill quarters (0,0) and (1,1); a 26th strict student
        # of A cannot fit a 25 seat odd quarter.
        self.assertFalse(
            _quarters_can_seat(10, 10, [("R", 50), ("A", 26)], relaxed_course="R")
        )
        # A small relaxed bite leaves room in (0,0) for a strict course.
        self.assertTrue(
            _quarters_can_seat(10, 10, [("R", 10), ("A", 20)], relaxed_course="R")
        )


class AllocatorTests(TestCase):
    def test_seats_a_full_relaxed_course_beside_strict_ones_under_each_rule(self):
        students = students_for([("R", 50), ("A", 25), ("B", 25)])
        seats, unplaced, _ = quietly(
            allocate_students_to_seats, students, 10, 10, relaxed_courses={"R"}
        )
        grid = seat_grid(seats, students, 10)

        self.assertEqual(unplaced, [])
        self.assertEqual(conflicts(grid, "R", FOUR), [])
        self.assertEqual(conflicts(grid, "A", EIGHT), [])
        self.assertEqual(conflicts(grid, "B", EIGHT), [])
        # The relaxed rule is actually in use: R has diagonal neighbours.
        self.assertTrue(conflicts(grid, "R", EIGHT))

    def test_relaxed_matric_order_rises_with_seat_number(self):
        students = students_for([("R", 30), ("A", 20)])
        seats, _, _ = quietly(
            allocate_students_to_seats, students, 10, 10, relaxed_courses={"R"}
        )
        r_seats = [seats[s["name"]] for s in students if s["course"] == "R"]
        self.assertEqual(r_seats, sorted(r_seats))

    def test_without_relaxed_courses_every_course_stays_8_direction(self):
        students = students_for([("R", 50)])
        seats, unplaced, _ = quietly(allocate_students_to_seats, students, 10, 10)

        self.assertEqual(len(unplaced), 25)
        self.assertEqual(conflicts(seat_grid(seats, students, 10), "R", EIGHT), [])


def seat_slot(result, relaxed):
    """Seat every hall of a distribution result with the real allocator.
    Returns (unplaced names, {hall name: grid})."""
    unplaced, grids = [], {}
    for hall_result in result:
        hall = Hall.objects.get(id=hall_result["id"])
        students = [
            {"student_id": None, "name": f"{item['id']}-{n:04}", "course": item["course"],
             "cls_id": item["class"]}
            for item in hall_result["classes"]
            for n in range(item["student_range"])
        ]
        codes = {item["course"] for item in hall_result["classes"]}
        seats, left, _ = quietly(
            allocate_students_to_seats, students, hall.rows, hall.columns,
            relaxed_courses={relaxed} & codes,
        )
        unplaced += left
        grids[hall.name] = seat_grid(seats, students, hall.columns)
    return unplaced, grids


def distribute_slot(pattern="sequential", utilization=1.0):
    halls = convert_hall_to_dict(Hall.objects.all(), safety_factor=utilization, pattern=pattern)
    timetables = list(TimeTable.objects.select_related("course", "class_obj__department"))
    relaxed = relaxed_course_code(timetables)
    return distribute_classes_to_halls(timetables, halls, relaxed_course=relaxed), relaxed


class DistributionTests(TestCase):
    def setUp(self):
        random.seed(0)

    def test_a_relaxed_course_is_distributed_and_seated_in_full(self):
        four_halls()
        big = make_course("GNS 202")
        for _ in range(3):  # 150 students: above the strict limit of 100
            TimeTable.objects.create(
                class_obj=listed_class(50), course=big, date=DATE, period=PERIOD,
                seating_rule=RELAXED,
            )
        for code, size in [("ACC 111", 40), ("BFN 111", 30), ("MKT 111", 20)]:
            schedule(listed_class(size), make_course(code), DATE, PERIOD)

        result, relaxed = distribute_slot()
        unplaced, grids = seat_slot(result, relaxed)

        given = sum(
            c["student_range"] for h in result for c in h["classes"] if c["course"] == "GNS 202"
        )
        self.assertEqual(given, 150)
        self.assertEqual(sum(c["student_range"] for h in result for c in h["classes"]), 240)
        self.assertEqual(unplaced, [])
        for name, grid in grids.items():
            with self.subTest(hall=name):
                self.assertEqual(conflicts(grid, "GNS 202", FOUR), [])
                for code in ("ACC 111", "BFN 111", "MKT 111"):
                    self.assertEqual(conflicts(grid, code, EIGHT), [])

    def test_the_same_course_stored_strict_is_capped_at_the_strict_limit(self):
        four_halls()
        schedule(listed_class(150), make_course("GNS 202"), DATE, PERIOD)

        result, _ = distribute_slot()

        self.assertEqual(sum(c["student_range"] for h in result for c in h["classes"]), 100)

    def test_every_hall_is_fully_seatable_with_one_relaxed_course_per_slot(self):
        for seed in range(12):
            with self.subTest(seed=seed):
                rng = random.Random(seed)
                Hall.objects.all().delete()
                TimeTable.objects.all().delete()
                for n in range(rng.randint(2, 5)):
                    make_hall(f"Hall {n}", rng.choice([7, 8, 10, 12, 15]), rng.choice([9, 10, 15]))
                sizes = list(Hall.objects.values_list("rows", "columns"))
                strict = seating_rules.strict_limit(sizes)
                relaxed = seating_rules.relaxed_limit(sizes)
                big = make_course(f"S{seed}BIG")
                remaining = rng.randint(strict + 1, relaxed)
                while remaining > 0:
                    part = min(remaining, rng.choice([30, 55, 80]))
                    TimeTable.objects.create(
                        class_obj=listed_class(part), course=big, date=DATE,
                        period=PERIOD, seating_rule=RELAXED,
                    )
                    remaining -= part
                seats = sum(r * c for r, c in sizes)
                demand = relaxed
                n = 0
                while demand < seats * rng.uniform(0.6, 1.1):
                    size = rng.choice([7, 12, 19, 23, 31, 40])
                    schedule(listed_class(size), make_course(f"S{seed}C{n:02}"), DATE, PERIOD)
                    demand += size
                    n += 1
                random.seed(seed)

                result, code = distribute_slot()
                unplaced, grids = seat_slot(result, code)

                self.assertEqual(unplaced, [])
                for grid in grids.values():
                    self.assertEqual(conflicts(grid, code, FOUR), [])


class TimetableClassificationTests(TestCase):
    def setUp(self):
        random.seed(0)
        four_halls()  # strict limit 100, relaxed limit 200, 400 seats a period

    def generate(self, dates):
        courses, refused = classify_courses(get_courses(), 100, 200)
        am, pm = split_course(courses)
        summary = quietly(
            generate, dates, am, pm, get_halls(pattern="sequential"), pbe_utilization=1.0
        )
        return summary, refused

    def rules(self):
        return {
            code: set(rules)
            for code, rules in _group(
                TimeTable.objects.values_list("course__code", "seating_rule")
            ).items()
        }

    def test_an_oversized_course_is_relaxed_on_every_row_and_others_stay_strict(self):
        course_with("GNS 202", 50, 50, 50)
        course_with("ACC 111", 60)

        self.generate([date(2026, 8, 17)])

        self.assertEqual(self.rules(), {"GNS 202": {RELAXED}, "ACC 111": {STRICT}})
        self.assertEqual(TimeTable.objects.filter(course__code="GNS 202").count(), 3)

    def test_a_course_above_the_relaxed_limit_is_refused_and_named(self):
        course_with("GNS 202", 150, 101)
        course_with("ACC 111", 60)

        summary, refused = self.generate([date(2026, 8, 17)])

        self.assertEqual(
            refused,
            [{"code": "GNS 202", "students": 251, "strict_limit": 100, "relaxed_limit": 200}],
        )
        self.assertFalse(TimeTable.objects.filter(course__code="GNS 202").exists())
        self.assertNotIn("GNS 202", summary["skipped_am_codes"])

    def test_a_course_at_the_strict_limit_stays_strict_and_one_more_is_relaxed(self):
        course_with("AT 101", 100)
        course_with("OVER 101", 101)

        self.generate([date(2026, 8, 17), date(2026, 8, 18)])

        self.assertEqual(self.rules(), {"AT 101": {STRICT}, "OVER 101": {RELAXED}})

    def test_only_one_relaxed_course_sits_each_period(self):
        # 270 seats would fit one period, but two relaxed courses may not share it.
        course_with("R1", 150)
        course_with("R2", 120)
        course_with("R3", 110)

        summary, _ = self.generate([date(2026, 8, 17), date(2026, 8, 18)])

        slots = list(
            TimeTable.objects.values_list("date", "period").order_by("date")
        )
        self.assertEqual(len(slots), 2)
        self.assertEqual(len(set(slots)), 2)
        self.assertEqual(len(summary["skipped_am_codes"]), 1)
        self.assertEqual(
            [(r["code"], r["period"]) for r in summary["relaxed_courses"]],
            [(code, "AM") for code in TimeTable.objects.order_by("date")
             .values_list("course__code", flat=True)],
        )

    def test_cbe_is_never_classified(self):
        course, _ = course_with("CBE 101", 500)
        course.exam_type = "CBE"
        course.save()

        _, refused = self.generate([date(2026, 8, 17)])

        self.assertEqual(refused, [])
        self.assertEqual(self.rules(), {"CBE 101": {STRICT}})


def _group(pairs):
    grouped = {}
    for key, value in pairs:
        grouped.setdefault(key, []).append(value)
    return grouped


class TimetableJobTests(PipelineTestCase):
    def test_the_job_result_lists_relaxed_and_refused_courses(self):
        four_halls()
        course_with("GNS 202", 150)
        course_with("GNS 999", 250)
        allow_generation()

        job = run(tasks.generate_timetable_task, "2026-08-17", "2026-08-19")

        self.assertEqual(job.status, "success", job.result_data)
        [relaxed] = job.result_data["relaxed_courses"]
        self.assertEqual(
            {k: relaxed[k] for k in ("code", "period", "students", "strict_limit", "relaxed_limit")},
            {"code": "GNS 202", "period": "AM", "students": 150,
             "strict_limit": 100, "relaxed_limit": 200},
        )
        self.assertEqual(
            job.result_data["refused_oversized"],
            [{"code": "GNS 999", "students": 250, "strict_limit": 100, "relaxed_limit": 200}],
        )


class ReconcileTests(TestCase):
    def setUp(self):
        self.hall = make_hall("Hall A", 2, 2)
        self.course = make_course("GNS 202")
        self.cls = listed_class(0)
        self.row = schedule(self.cls, self.course, DATE, PERIOD)
        first, second = enrol(self.cls, ["2400000001", "2400000002"])
        SeatArrangement.objects.create(
            date=DATE, period=PERIOD, student=first, seat_number=1,
            hall=self.hall, course=self.course, cls=self.cls,
        )
        self.left = SeatArrangement.objects.create(
            date=DATE, period=PERIOD, student=second, seat_number=None,
            hall=self.hall, course=self.course, cls=self.cls,
        )

    def test_a_relaxed_student_may_take_the_diagonal_seat_only(self):
        self.row.seating_rule = RELAXED
        self.row.save()

        self.assertEqual(reconcile_unplaced(DATE, PERIOD), 1)

        self.left.refresh_from_db()
        self.assertEqual(self.left.seat_number, 4)

    def test_a_strict_student_is_not_put_on_the_diagonal(self):
        self.assertEqual(reconcile_unplaced(DATE, PERIOD), 0)


class ManualAssignmentTests(PipelineTestCase):
    URL = "/api/allocation/manual-assign/"

    def setUp(self):
        super().setUp()
        self.hall = make_hall("Hall A", 3, 3)
        self.course = make_course("GNS 202")
        self.cls = listed_class(0)
        self.row = schedule(self.cls, self.course, DATE, PERIOD)
        first, second = enrol(self.cls, ["2400000001", "2400000002"])
        SeatArrangement.objects.create(
            date=DATE, period=PERIOD, student=first, seat_number=1,
            hall=self.hall, course=self.course, cls=self.cls,
        )
        self.left = SeatArrangement.objects.create(
            date=DATE, period=PERIOD, student=second, seat_number=None,
            hall=self.hall, course=self.course, cls=self.cls,
        )

    def move(self, seat):
        return self.post(self.URL, {"seat_arrangement_id": self.left.id, "seat_number": seat})

    def test_a_strict_student_cannot_be_moved_next_to_a_diagonal_classmate(self):
        response = self.move(5)

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.data["detail"],
            "Seat 5 is next to a student of the same course (GNS 202).",
        )
        self.left.refresh_from_db()
        self.assertIsNone(self.left.seat_number)

    def test_a_relaxed_student_may_sit_diagonally_but_not_beside(self):
        self.row.seating_rule = RELAXED
        self.row.save()

        self.assertEqual(self.move(2).status_code, 409)
        self.assertEqual(self.move(5).status_code, 200)
        self.left.refresh_from_db()
        self.assertEqual(self.left.seat_number, 5)

    def test_a_seat_away_from_classmates_is_still_allowed(self):
        self.assertEqual(self.move(9).status_code, 200)

    def test_an_occupied_seat_is_still_refused(self):
        response = self.move(1)

        self.assertEqual(response.status_code, 409)
        self.assertIn("already occupied", response.data["detail"])


class OutdatedRuleTests(PipelineTestCase):
    def setUp(self):
        super().setUp()
        make_hall("Hall A", 10, 10)
        make_hall("Hall B", 10, 10)  # strict limit 50
        self.course, (self.cls,) = course_with("GNS 202", 40)
        schedule(self.cls, self.course, DATE, PERIOD)
        allow_generation()

    def readiness(self):
        return self.client.get(
            f"/api/readiness/?stage=distribution&date={DATE}&period={PERIOD}"
        ).data

    def test_a_course_still_within_its_rule_is_ready(self):
        report = self.readiness()

        self.assertTrue(report["ready"], report)
        self.assertEqual(report["outdated_rules"], [])

    def test_a_strict_course_grown_past_the_strict_limit_blocks_distribution(self):
        enrol(self.cls, [f"25{n:08}" for n in range(20)])  # now 60

        report = self.readiness()
        response = self.post("/api/distribution/generate/", {"date": DATE, "period": PERIOD})
        job = run(tasks.generate_distribution_task, DATE, PERIOD)

        self.assertFalse(report["ready"])
        self.assertEqual(
            report["outdated_rules"],
            [{"date": DATE, "period": PERIOD, "course": "GNS 202",
              "stored_rule": STRICT, "current_rule": RELAXED, "students": 60}],
        )
        self.assertEqual(response.status_code, 409)
        self.assertIn(
            "Timetable seating rule outdated for GNS 202, regenerate the timetable",
            response.data["detail"],
        )
        self.assertEqual(job.status, "failed")
        self.assertEqual(job.result_data["outdated_rules"], report["outdated_rules"])

    def test_generate_all_is_blocked_too(self):
        enrol(self.cls, [f"25{n:08}" for n in range(20)])

        self.assertEqual(self.post("/api/distribution/generate-all/").status_code, 409)


class VisibilityTests(PipelineTestCase):
    def setUp(self):
        super().setUp()
        self.hall = make_hall("BB 1", 4, 4)
        self.relaxed = make_course("GNS 202")
        self.strict = make_course("ACC 111")
        self.gns = listed_class(0, make_department("gs"))
        self.acc = listed_class(0, make_department("ac"))
        TimeTable.objects.create(
            class_obj=self.gns, course=self.relaxed, date=DATE, period=PERIOD,
            seating_rule=RELAXED,
        )
        schedule(self.acc, self.strict, DATE, PERIOD)
        for cls, course, matric, seat in [
            (self.gns, self.relaxed, "2400000001", 1),
            (self.gns, self.relaxed, "2400000003", 6),
            (self.acc, self.strict, "2400000002", 2),
        ]:
            [student] = enrol(cls, [matric])
            SeatArrangement.objects.create(
                date=DATE, period=PERIOD, student=student, seat_number=seat,
                hall=self.hall, course=course, cls=cls,
            )

    def test_the_timetable_list_returns_each_row_rule(self):
        rows = self.client.get("/api/timetable/").data["results"]

        self.assertEqual(
            {r["course"]["code"]: r["seating_rule"] for r in rows},
            {"GNS 202": RELAXED, "ACC 111": STRICT},
        )

    def test_the_hall_view_summarises_each_course_rule(self):
        data = self.client.get(
            "/api/allocation/hall/",
            {"date": DATE, "period": PERIOD, "hall_id": self.hall.id},
        ).data

        self.assertEqual(
            data["courses"],
            [{"code": "ACC 111", "name": "Course ACC 111", "seating_rule": STRICT},
             {"code": "GNS 202", "name": "Course GNS 202", "seating_rule": RELAXED}],
        )
        self.assertEqual(len(data["placed"]), 3)

    def test_only_the_relaxed_course_sheets_carry_the_seating_line(self):
        bulk = read_sheets(
            export_arrangements(RequestFactory().get("/", {"date": DATE, "period": PERIOD}))
        )
        per_hall = read_sheets(
            self.client.get(
                reverse("api-export-attendance-sheets"),
                {"date": DATE, "period": PERIOD, "hall_id": self.hall.id},
            )
        )

        for sheets in (bulk, per_hall):
            by_course = {
                ("GNS 202" if "GNS" in name else "ACC 111"): sheet["text"]
                for name, sheet in sheets.items()
            }
            self.assertIn(RELAXED_SHEET_LINE, by_course["GNS 202"])
            self.assertNotIn(RELAXED_SHEET_LINE, by_course["ACC 111"])

    def test_the_estimate_counts_relaxed_and_refused_courses(self):
        make_hall("BB 2", 4, 4)  # strict limit 8, relaxed limit 16
        course_with("SMALL 101", 5)
        course_with("MID 101", 12)
        course_with("HUGE 101", 30)

        data = self.client.get("/api/timetable/estimate/").data

        self.assertEqual(
            {k: data[k] for k in ("relaxed_count", "refused_count", "strict_limit", "relaxed_limit")},
            {"relaxed_count": 1, "refused_count": 1, "strict_limit": 8, "relaxed_limit": 16},
        )
