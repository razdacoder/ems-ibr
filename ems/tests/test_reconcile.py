"""reconcile_unplaced: the cross hall safety net for students a hall could not seat."""
from collections import Counter

from django.test import TestCase

from ems.models import SeatArrangement
from ems.utils import reconcile_unplaced

from .helpers import enrol, make_class, make_course, make_hall

DATE, PERIOD = "2026-08-17", "AM"


def neighbours(seat, cols):
    r, c = divmod(seat - 1, cols)
    return {
        (r + dr) * cols + (c + dc) + 1
        for dr in (-1, 0, 1)
        for dc in (-1, 0, 1)
        if (dr or dc) and 0 <= c + dc < cols and r + dr >= 0
    }


class ReconcileUnplacedTests(TestCase):
    def setUp(self):
        self.course = make_course("ACC 121")
        self.cls = make_class(6)
        self.students = enrol(self.cls, [f"24300000{n:02}" for n in range(6)])

    def leave_unplaced(self, students, home_hall):
        for s in students:
            SeatArrangement.objects.create(
                date=DATE, period=PERIOD, student=s, seat_number=None,
                hall=home_hall, course=self.course, cls=self.cls,
            )

    def test_keeps_a_class_overflow_together_in_one_hall(self):
        # Regression: ranking halls by free cells alone changed the winner
        # after every student, so a class was dealt out a few at a time across
        # many halls, breaking its matric range in the hall directory.
        hall_a = make_hall("Hall A", 6, 6)
        make_hall("Hall B", 6, 6)
        self.leave_unplaced(self.students, hall_a)

        reseated = reconcile_unplaced(DATE, PERIOD)

        self.assertEqual(reseated, 6)
        halls_used = Counter(
            SeatArrangement.objects.filter(date=DATE, period=PERIOD)
            .values_list("hall__name", flat=True)
        )
        self.assertEqual(len(halls_used), 1, halls_used)

    def test_never_seats_two_students_of_a_course_side_by_side(self):
        hall = make_hall("Hall A", 6, 6)
        self.leave_unplaced(self.students, hall)

        reconcile_unplaced(DATE, PERIOD)

        seats = list(
            SeatArrangement.objects.filter(hall=hall).values_list("seat_number", flat=True)
        )
        self.assertNotIn(None, seats)
        for seat in seats:
            self.assertFalse(neighbours(seat, 6) & set(seats), f"seat {seat} has a neighbour")

    def test_moves_on_to_another_hall_once_the_first_has_no_legal_seat(self):
        # A 4 x 4 hall holds at most 4 students of one course safely.
        hall_a = make_hall("Hall A", 4, 4)
        make_hall("Hall B", 4, 4)
        self.leave_unplaced(self.students, hall_a)

        reseated = reconcile_unplaced(DATE, PERIOD)

        self.assertEqual(reseated, 6)
        per_hall = sorted(
            Counter(
                SeatArrangement.objects.values_list("hall__name", flat=True)
            ).values()
        )
        self.assertEqual(per_hall, [2, 4])

    def test_seats_the_overflow_in_ascending_matric_order(self):
        hall = make_hall("Hall A", 6, 6)
        self.leave_unplaced(reversed(self.students), hall)

        reconcile_unplaced(DATE, PERIOD)

        by_matric = list(
            SeatArrangement.objects.order_by("student__matric_no")
            .values_list("seat_number", flat=True)
        )
        self.assertEqual(by_matric, sorted(by_matric))

    def test_leaves_students_unplaced_when_no_hall_has_a_legal_seat(self):
        hall = make_hall("Tiny", 1, 1)
        self.leave_unplaced(self.students[:2], hall)

        reseated = reconcile_unplaced(DATE, PERIOD)

        self.assertEqual(reseated, 1)
        self.assertEqual(
            SeatArrangement.objects.filter(seat_number__isnull=True).count(), 1
        )

    def test_does_nothing_when_nobody_is_unplaced(self):
        make_hall("Hall A", 6, 6)

        self.assertEqual(reconcile_unplaced(DATE, PERIOD), 0)
