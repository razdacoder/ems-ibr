"""Hall rules: the hard fill cap, course limits by hall size, and hall
groups that keep a course's halls together (see ems/halls.py)."""
import random

from django.test import SimpleTestCase, TestCase

from ems.halls import (
    course_limit,
    group_from_name,
    group_ranks,
    normalise_course_limits,
)
from ems import readiness
from ems.models import Distribution, Hall, SeatArrangement, TimeTable
from ems.utils import (
    convert_hall_to_dict, distribute_classes_to_halls, get_halls, reconcile_unplaced,
)

from .helpers import enrol, listed_class, make_class, make_course, make_hall, no_fill_cap, schedule
from .test_relaxed_seating import ManualAssignmentTests

DATE, PERIOD = "2026-08-17", "AM"


def distribute(
    course_limits=None, group_order=None, utilization=1.0, small_course_threshold=0
):
    halls = convert_hall_to_dict(
        Hall.objects.all(), safety_factor=utilization, pattern="sequential",
        course_limits=course_limits,
    )
    timetables = list(TimeTable.objects.select_related("course", "class_obj__department"))
    return distribute_classes_to_halls(
        timetables, halls, group_order=group_order,
        small_course_threshold=small_course_threshold,
    )


def halls_of(result, course):
    return {h["name"] for h in result if any(c["course"] == course for c in h["classes"])}


class GroupTests(SimpleTestCase):
    def test_the_group_is_the_letters_the_name_starts_with(self):
        self.assertEqual(group_from_name("BE 3"), "BE")
        self.assertEqual(group_from_name("BJ4"), "BJ")
        self.assertEqual(group_from_name("AUD 1"), "AUD")
        self.assertEqual(group_from_name("AG 1 & 2"), "AG")
        self.assertEqual(group_from_name("12"), "12")

    def test_configured_groups_come_first_then_the_biggest(self):
        halls = [("AUD", 500), ("BE", 100), ("BJ", 120), ("OBA", 120)]
        ranks = group_ranks(halls, ["be", "BJ"])
        self.assertEqual(sorted(ranks, key=ranks.get), ["BE", "BJ", "AUD", "OBA"])


class CourseLimitTests(SimpleTestCase):
    TIERS = [
        {"max_seats": 300, "courses": 6},
        {"max_seats": None, "courses": 8},
        {"max_seats": 120, "courses": 4},
    ]

    def test_a_hall_takes_the_first_tier_it_fits(self):
        self.assertEqual(course_limit(100, self.TIERS), 4)
        self.assertEqual(course_limit(120, self.TIERS), 4)
        self.assertEqual(course_limit(121, self.TIERS), 6)
        self.assertEqual(course_limit(5000, self.TIERS), 8)

    def test_bad_tiers_are_refused(self):
        with self.assertRaises(ValueError):
            normalise_course_limits([{"max_seats": 100, "courses": 4}])  # no open tier
        with self.assertRaises(ValueError):
            normalise_course_limits([{"max_seats": None, "courses": 0}])
        with self.assertRaises(ValueError):
            normalise_course_limits([
                {"max_seats": 100, "courses": 4},
                {"max_seats": 100, "courses": 5},
                {"max_seats": None, "courses": 8},
            ])


class HallGroupFieldTests(TestCase):
    def test_a_blank_group_is_filled_from_the_name(self):
        self.assertEqual(make_hall("BE 3", 5, 5).group, "BE")

    def test_a_set_group_is_kept(self):
        hall = Hall.objects.create(
            name="Annex", group="be", capacity=25, rows=5, columns=5,
        )
        self.assertEqual(hall.group, "BE")


class DistributionRuleTests(TestCase):
    def setUp(self):
        random.seed(0)

    def test_no_hall_holds_more_courses_than_its_limit(self):
        make_hall("Big", 20, 20)  # 400 seats
        for n in range(10):
            schedule(listed_class(20), make_course(f"C{n:02}"))

        result = distribute(course_limits=[
            {"max_seats": 300, "courses": 8},
            {"max_seats": None, "courses": 3},
        ])

        [big] = result
        self.assertEqual(len({c["course"] for c in big["classes"]}), 3)

    THREE_COURSES = [{"max_seats": None, "courses": 3}]

    def three_courses_and(self, *small):
        make_hall("Big", 20, 20)  # 400 seats
        make_hall("Small", 5, 5)
        for code in ("A", "B", "C"):
            schedule(listed_class(20), make_course(code))
        for code, size in small:
            schedule(listed_class(size), make_course(code))

    def test_a_small_course_joins_a_hall_in_use_instead_of_opening_one(self):
        self.three_courses_and(("D", 4))

        without = distribute(course_limits=self.THREE_COURSES)
        self.assertEqual(halls_of(without, "D"), {"Small"})

        [big] = distribute(course_limits=self.THREE_COURSES, small_course_threshold=10)
        self.assertEqual(big["name"], "Big")
        self.assertEqual({c["course"] for c in big["classes"]}, {"A", "B", "C", "D"})
        self.assertEqual(sum(c["student_range"] for c in big["classes"]), 64)

    def test_a_hall_goes_at_most_one_course_over_its_limit(self):
        self.three_courses_and(("D", 4), ("E", 4))

        result = distribute(course_limits=self.THREE_COURSES, small_course_threshold=10)

        # Big can take one of them, not both, so Small still opens for both.
        by_name = {h["name"]: {c["course"] for c in h["classes"]} for h in result}
        self.assertEqual(by_name, {"Big": {"A", "B", "C"}, "Small": {"D", "E"}})

    def test_a_course_over_the_threshold_still_opens_a_hall(self):
        self.three_courses_and(("D", 15))

        result = distribute(course_limits=self.THREE_COURSES, small_course_threshold=10)

        self.assertEqual(halls_of(result, "D"), {"Small"})

    def test_the_fill_cap_is_never_passed(self):
        make_hall("Room", 10, 10)
        for n in range(6):
            schedule(listed_class(25), make_course(f"C{n:02}"))

        [room] = distribute(utilization=0.9)

        self.assertEqual(sum(c["student_range"] for c in room["classes"]), 90)

    def test_a_course_spills_into_the_neighbouring_group(self):
        for name in ("AA 1", "AA 2", "BB 1", "CC 1"):
            make_hall(name, 10, 10)  # 25 seats per quarter
        course = make_course("GNS 101")
        schedule(listed_class(60), course)

        # CC stands next to AA; BB is further away.
        result = distribute(group_order=["AA", "CC", "BB"])

        self.assertEqual(halls_of(result, "GNS 101"), {"AA 1", "AA 2", "CC 1"})

    def test_a_started_course_carries_on_before_a_new_one_opens(self):
        for n in range(4):
            make_hall(f"Room {n}", 10, 10)
        for code in ("A", "B", "C", "D"):
            schedule(listed_class(40), make_course(code))
        schedule(listed_class(30), make_course("E"))

        result = distribute()
        order = [h["name"] for h in result]

        # Every course sits in one unbroken run of halls.
        for code in ("A", "B", "C", "D", "E"):
            positions = sorted(order.index(n) for n in halls_of(result, code))
            self.assertEqual(positions, list(range(positions[0], positions[-1] + 1)), code)


class ReconcileRuleTests(TestCase):
    def setUp(self):
        self.cls = make_class(3)

    def unplaced(self, hall, course, matric):
        [student] = enrol(self.cls, [matric])
        return SeatArrangement.objects.create(
            date=DATE, period=PERIOD, student=student, seat_number=None,
            hall=hall, course=course, cls=self.cls,
        )

    def test_reconcile_stops_at_the_fill_cap(self):
        no_fill_cap(pbe_hall_utilization=0.5)  # 2 x 2 hall: at most 2
        hall = make_hall("Hall A", 2, 2)
        a, b, c = (make_course(code) for code in ("A", "B", "C"))
        [first] = enrol(self.cls, ["M0"])
        SeatArrangement.objects.create(
            date=DATE, period=PERIOD, student=first, seat_number=1,
            hall=hall, course=a, cls=self.cls,
        )
        self.unplaced(hall, b, "M1")
        self.unplaced(hall, c, "M2")

        self.assertEqual(reconcile_unplaced(DATE, PERIOD), 1)

    def test_reconcile_opens_no_course_past_the_limit(self):
        no_fill_cap(hall_course_limits=[{"max_seats": None, "courses": 1}])
        hall = make_hall("Hall A", 3, 3)
        a, b = make_course("A"), make_course("B")
        [first] = enrol(self.cls, ["M0"])
        SeatArrangement.objects.create(
            date=DATE, period=PERIOD, student=first, seat_number=1,
            hall=hall, course=a, cls=self.cls,
        )
        self.unplaced(hall, b, "M1")

        self.assertEqual(reconcile_unplaced(DATE, PERIOD), 0)

    def test_overflow_goes_to_the_nearest_group(self):
        no_fill_cap(hall_group_order=["AA", "BB", "CC"])
        home = make_hall("AA 1", 1, 1)  # full
        make_hall("CC 1", 5, 5)  # two groups away, and bigger
        make_hall("BB 1", 3, 3)  # the neighbour
        course = make_course("A")
        [first] = enrol(self.cls, ["M0"])
        SeatArrangement.objects.create(
            date=DATE, period=PERIOD, student=first, seat_number=1,
            hall=home, course=course, cls=self.cls,
        )
        moved = self.unplaced(home, course, "M1")

        self.assertEqual(reconcile_unplaced(DATE, PERIOD), 1)
        moved.refresh_from_db()
        self.assertEqual(moved.hall.name, "BB 1")


class ManualFillCapTests(ManualAssignmentTests):
    """Reuses the 3 x 3 hall with one seated and one unplaced student."""

    def test_a_hall_at_its_fill_cap_takes_no_one_by_hand(self):
        no_fill_cap(pbe_hall_utilization=0.12)  # 9 seats: at most 1

        response = self.move(9)

        self.assertEqual(response.status_code, 409)
        self.assertIn("fill cap", response.data["detail"])


class ClosedHallTests(TestCase):
    """A closed hall is left out of every generate run (Hall.is_open)."""

    def test_get_halls_leaves_closed_halls_out(self):
        make_hall("Open", 3, 3)
        Hall.objects.filter(pk=make_hall("Shut", 3, 3).pk).update(is_open=False)

        self.assertEqual([h["name"] for h in get_halls()], ["Open"])

    def test_distribution_never_plans_into_a_closed_hall(self):
        make_hall("Open", 10, 10)
        shut = make_hall("Shut", 10, 10)
        shut.is_open = False
        shut.save()
        schedule(listed_class(30), make_course("A"))

        halls = convert_hall_to_dict(Hall.objects.open(), pattern="sequential")
        timetables = list(TimeTable.objects.select_related("course", "class_obj__department"))
        result = distribute_classes_to_halls(timetables, halls)

        self.assertEqual(halls_of(result, "A"), {"Open"})

    def test_reconcile_moves_no_one_into_a_closed_hall(self):
        no_fill_cap()
        cls = make_class(2)
        home = make_hall("AA 1", 1, 1)  # full
        shut = make_hall("BB 1", 3, 3)
        shut.is_open = False
        shut.save()
        course = make_course("A")
        first, second = enrol(cls, ["M0", "M1"])
        SeatArrangement.objects.create(
            date=DATE, period=PERIOD, student=first, seat_number=1,
            hall=home, course=course, cls=cls,
        )
        SeatArrangement.objects.create(
            date=DATE, period=PERIOD, student=second, seat_number=None,
            hall=home, course=course, cls=cls,
        )

        self.assertEqual(reconcile_unplaced(DATE, PERIOD), 0)

    def test_allocation_is_blocked_when_the_distribution_uses_a_closed_hall(self):
        hall = make_hall("Shut", 3, 3)
        Distribution.objects.create(hall=hall, date=DATE, period=PERIOD)
        self.assertTrue(readiness.check("allocation", [(DATE, PERIOD)])["ready"])

        hall.is_open = False
        hall.save()
        report = readiness.check("allocation", [(DATE, PERIOD)])

        self.assertFalse(report["ready"])
        self.assertEqual(
            report["closed_halls"],
            [{"date": DATE, "period": PERIOD, "hall_id": hall.id, "hall": "Shut"}],
        )
        self.assertIn("Shut", readiness.blocking_message(report))
