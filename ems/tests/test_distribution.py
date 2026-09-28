"""Distribution: how a slot's classes are split across halls.

Regression cover for the Aug 2026 exam run, where the biggest halls were
packed to their whole grid while many small halls sat empty, and the packed
halls then left students unplaced for the cross hall reconcile to scatter.
"""
import random

from django.test import TestCase

from ems.models import Hall, TimeTable
from ems.utils import (
    _max_seatable_bite,
    _quarters_can_seat,
    allocate_students_to_seats,
    convert_hall_to_dict,
    distribute_classes_to_halls,
)

from .helpers import listed_class, make_course, make_hall, quietly, schedule


def run_distribution(pattern="sequential", utilization=1.0):
    """Distribute the whole slot the way generate_distribution_task does."""
    halls = convert_hall_to_dict(
        Hall.objects.all(), safety_factor=utilization, pattern=pattern
    )
    timetables = list(TimeTable.objects.select_related("course", "class_obj__department"))
    return distribute_classes_to_halls(timetables, halls)


def assigned(result):
    """hall name -> students assigned there."""
    return {h["name"]: sum(c["student_range"] for c in h["classes"]) for h in result}


def unplaced_after_seating(hall_result):
    """Seat one hall's assignment with the real allocator; return who is left."""
    hall = Hall.objects.get(id=hall_result["id"])
    students = [
        {"student_id": None, "name": f"{item['id']}-{n:04}", "course": item["course"],
         "cls_id": item["class"]}
        for item in hall_result["classes"]
        for n in range(item["student_range"])
    ]
    _, unplaced, _ = quietly(allocate_students_to_seats, students, hall.rows, hall.columns)
    return unplaced


class QuartersCanSeatTests(TestCase):
    """_quarters_can_seat mirrors the allocator's quarter placer."""

    def test_accepts_four_courses_that_each_fill_one_quarter(self):
        # A 10 x 10 hall has four 5 x 5 quarters of 25 seats.
        bites = [("A", 25), ("B", 25), ("C", 25), ("D", 25)]
        self.assertTrue(_quarters_can_seat(10, 10, bites))

    def test_rejects_a_course_bigger_than_any_quarter(self):
        self.assertFalse(_quarters_can_seat(10, 10, [("A", 26)]))

    def test_rejects_a_mix_whose_total_fits_but_cannot_be_split_into_quarters(self):
        # 100 students for 100 seats, but the fifth course only finds 7 free
        # seats in the emptiest quarter, so the allocator would leave 9 out.
        bites = [("A", 24), ("B", 22), ("C", 20), ("D", 18), ("E", 16)]
        self.assertFalse(_quarters_can_seat(10, 10, bites))

    def test_uses_the_larger_quarters_of_an_odd_sized_hall(self):
        # 5 x 5: quarters of 9, 6, 6 and 4 seats.
        self.assertTrue(_quarters_can_seat(5, 5, [("A", 9), ("B", 6), ("C", 6), ("D", 4)]))
        self.assertFalse(_quarters_can_seat(5, 5, [("A", 10)]))

    def test_an_empty_hall_seats_nothing_and_accepts_no_bites(self):
        self.assertTrue(_quarters_can_seat(10, 10, []))


class MaxSeatableBiteTests(TestCase):
    def hall(self, classes):
        return {"rows": 10, "columns": 10, "classes": classes}

    def test_returns_the_whole_limit_when_it_fits(self):
        self.assertEqual(_max_seatable_bite(self.hall([]), "A", 20), 20)

    def test_shrinks_the_bite_to_what_the_quarters_can_still_hold(self):
        full = [{"course": c, "student_range": 25} for c in "ABC"]
        full.append({"course": "D", "student_range": 20})
        self.assertEqual(_max_seatable_bite(self.hall(full), "E", 20), 5)

    def test_counts_earlier_classes_of_the_same_course_as_one_group(self):
        # Course A already holds 20 of its quarter's 25 seats (from another
        # class), so only 5 more of A fit, even though other quarters are empty.
        hall = self.hall([{"course": "A", "student_range": 20}])
        self.assertEqual(_max_seatable_bite(hall, "A", 25), 5)

    def test_returns_zero_when_nothing_more_fits(self):
        full = [{"course": c, "student_range": 25} for c in "ABCD"]
        self.assertEqual(_max_seatable_bite(self.hall(full), "E", 10), 0)

    def test_returns_zero_for_a_zero_limit(self):
        self.assertEqual(_max_seatable_bite(self.hall([]), "A", 0), 0)


class BalancedLoadTests(TestCase):
    def setUp(self):
        random.seed(0)  # make_schedules shuffles

    def test_a_light_slot_uses_every_hall_instead_of_packing_the_biggest(self):
        make_hall("AUD", 20, 20)  # 400 seats
        for n in range(4):
            make_hall(f"Room {n}", 10, 10)  # 100 seats each, 800 in all
        for n in range(8):  # 320 students, 40% of the seats
            schedule(listed_class(40), make_course(f"C{n:02}"))

        result = run_distribution()

        self.assertEqual(len(result), 5, "every hall should take a share")
        # About 40% of AUD is its fair share; the old largest first filling
        # put all 320 students in it (80%).
        self.assertLessEqual(assigned(result)["AUD"], 200)
        self.assertEqual(sum(assigned(result).values()), 320)

    def test_halls_fill_in_proportion_to_their_size(self):
        make_hall("Big", 20, 20)
        make_hall("Small", 10, 10)
        for n in range(10):  # 250 of 500 seats
            schedule(listed_class(25), make_course(f"C{n:02}"))

        loads = assigned(run_distribution())

        self.assertEqual(sum(loads.values()), 250)
        self.assertAlmostEqual(
            loads.get("Big", 0) / 400, loads.get("Small", 0) / 100, delta=0.15
        )

    def test_a_slot_that_needs_every_seat_fills_every_hall(self):
        for n in range(3):
            make_hall(f"Room {n}", 10, 10)
        for n in range(12):  # 300 students, 300 seats, 25 per course
            schedule(listed_class(25), make_course(f"C{n:02}"))

        loads = assigned(run_distribution())

        self.assertEqual(loads, {"Room 0": 100, "Room 1": 100, "Room 2": 100})

    def test_no_hall_is_given_more_than_its_budget_when_demand_exceeds_seats(self):
        make_hall("Room A", 10, 10)
        make_hall("Room B", 8, 10)
        for n in range(10):  # 400 students for 180 seats
            schedule(listed_class(40), make_course(f"C{n:02}"))

        loads = assigned(run_distribution())

        self.assertLessEqual(loads["Room A"], 100)
        self.assertLessEqual(loads["Room B"], 80)

    def test_an_empty_slot_assigns_nothing(self):
        make_hall("Room A", 10, 10)

        self.assertEqual(run_distribution(), [])


class SeatableAssignmentTests(TestCase):
    """Whatever distribution gives a hall, the allocator must seat in full.

    Before the fix a hall could be handed its whole grid in a mix of course
    sizes the four adjacency safe quarters cannot hold, so every packed hall
    left students unplaced.
    """

    def test_every_hall_is_fully_seatable_across_many_random_slots(self):
        for seed in range(12):
            with self.subTest(seed=seed):
                rng = random.Random(seed)
                Hall.objects.all().delete()
                TimeTable.objects.all().delete()
                for n in range(rng.randint(2, 5)):
                    make_hall(f"Hall {n}", rng.choice([8, 10, 12, 15]), rng.choice([10, 15]))
                seats = sum(h.rows * h.columns for h in Hall.objects.all())
                demand = 0
                n = 0
                while demand < seats * rng.uniform(0.5, 1.1):
                    size = rng.choice([7, 12, 19, 23, 31, 40, 55])
                    schedule(listed_class(size), make_course(f"S{seed}C{n:02}"))
                    demand += size
                    n += 1
                random.seed(seed)

                result = run_distribution()

                for hall_result in result:
                    self.assertEqual(
                        unplaced_after_seating(hall_result), [],
                        f"{hall_result['name']} was given students it cannot seat",
                    )

    def test_checkerboard_settings_are_fully_seatable_too(self):
        make_hall("Room A", 12, 15)
        make_hall("Room B", 10, 10)
        for n, size in enumerate([40, 33, 27, 20, 18, 11, 9]):
            schedule(listed_class(size), make_course(f"C{n:02}"))
        random.seed(1)

        result = run_distribution(pattern="checkerboard", utilization=0.9)

        for hall_result in result:
            self.assertEqual(unplaced_after_seating(hall_result), [])


class LargeCourseTests(TestCase):
    def setUp(self):
        random.seed(0)

    def test_one_large_course_on_a_light_slot_is_placed_in_full(self):
        # Regression: on a light slot every hall's shared budget is small, so a
        # big course took a small bite in every hall. The one course per hall
        # rule then stopped it growing once spare capacity was released, and
        # the rest of the course was silently left out (COM 115, 1 Sep AM).
        for n in range(10):
            make_hall(f"Room {n}", 10, 10)  # 1000 seats, 25 per quarter
        course = make_course("COM 115")
        for _ in range(3):
            schedule(listed_class(60), course)  # 180 students, one course

        result = run_distribution()

        self.assertEqual(sum(assigned(result).values()), 180)
        for hall_result in result:
            self.assertEqual(unplaced_after_seating(hall_result), [])

    def test_a_class_is_listed_once_per_hall_even_when_topped_up(self):
        for n in range(10):
            make_hall(f"Room {n}", 10, 10)
        course = make_course("COM 115")
        for _ in range(3):
            schedule(listed_class(60), course)

        result = run_distribution()

        for hall_result in result:
            ids = [c["id"] for c in hall_result["classes"]]
            self.assertEqual(len(ids), len(set(ids)), hall_result["name"])

    def test_a_course_too_big_for_every_quarter_is_capped_not_overseated(self):
        # Two 10 x 10 halls can hold at most 25 + 25 students of one course
        # without two of them sitting side by side.
        make_hall("Room A", 10, 10)
        make_hall("Room B", 10, 10)
        schedule(listed_class(80), make_course("GNS 202"))

        result = run_distribution()

        self.assertEqual(sum(assigned(result).values()), 50)
        for hall_result in result:
            self.assertEqual(unplaced_after_seating(hall_result), [])
