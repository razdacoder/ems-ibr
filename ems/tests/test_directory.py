"""Hall directory: one row per (hall, class) with the class's matric range."""
import datetime as dt

from django.test import TestCase

from ems.directory import format_matric_range, hall_summary_rows
from ems.models import SeatArrangement

from .helpers import enrol, make_class, make_course, make_department, make_hall

DATE, PERIOD = dt.date(2026, 8, 17), "AM"


class FormatMatricRangeTests(TestCase):
    def test_shows_the_full_start_and_the_differing_end(self):
        matrics = ["2430113585", "2430113600", "2430113616"]

        self.assertEqual(format_matric_range(matrics), "2430113585 - 3616")

    def test_orders_as_text_like_allocation_does(self):
        # Regression: a numbers first key put the mistyped 9 digit matric at
        # the start, although allocation (order_by matric_no) cut it into the
        # class's last block. The range must follow allocation's text order.
        matrics = ["2450640372", "245064439", "2450640360"]

        self.assertEqual(format_matric_range(matrics), "2450640360 - 4439")

    def test_a_float_style_matric_sorts_with_its_neighbours(self):
        matrics = ["2520320003.0", "2520320002", "2520320004.0"]

        self.assertTrue(format_matric_range(matrics).startswith("2520320002 "))

    def test_a_single_matric_is_shown_alone(self):
        self.assertEqual(format_matric_range(["2430113585", "2430113585"]), "2430113585")

    def test_blank_entries_are_ignored_and_empty_input_gives_empty_text(self):
        self.assertEqual(format_matric_range(["", None]), "")
        self.assertEqual(format_matric_range([]), "")


class HallSummaryRowsTests(TestCase):
    def setUp(self):
        self.course = make_course("ACC 121")
        self.cls = make_class(6, make_department("ac"), name="ND II")
        students = enrol(self.cls, [f"24300000{n:02}" for n in range(6)])
        # Allocation hands blocks out in database hall name order, so
        # "Hall 10" took the first block and "Hall 2" the second.
        self.seat(make_hall("Hall 10", 4, 4), students[:3])
        self.seat(make_hall("Hall 2", 4, 4), students[3:])

    def seat(self, hall, students):
        for n, s in enumerate(students, 1):
            SeatArrangement.objects.create(
                date=DATE, period=PERIOD, student=s, seat_number=n * 2,
                hall=hall, course=self.course, cls=self.cls,
            )

    def test_a_class_split_across_halls_is_listed_in_ascending_matric_order(self):
        rows = hall_summary_rows(DATE, PERIOD)

        self.assertEqual(
            [(r["hall"], r["matric_range"]) for r in rows],
            [("Hall 10", "2430000000 - 0002"), ("Hall 2", "2430000003 - 0005")],
        )

    def test_lists_halls_by_block_start_not_by_hall_name(self):
        # Swap the blocks: now "Hall 2" holds the lower matrics and must come
        # first, even though "Hall 10" sorts first as text.
        SeatArrangement.objects.all().delete()
        students = list(self.cls.student_set.order_by("matric_no"))
        self.seat(make_hall("Hall 2b", 4, 4), students[:3])
        self.seat(make_hall("Hall 10b", 4, 4), students[3:])

        rows = hall_summary_rows(DATE, PERIOD)

        self.assertEqual([r["hall"] for r in rows], ["Hall 2b", "Hall 10b"])

    def test_each_row_carries_the_class_label_and_count(self):
        row = hall_summary_rows(DATE, PERIOD)[0]

        self.assertEqual(row["class_name"], "AC ND II")
        self.assertEqual(row["count"], 3)

    def test_unplaced_students_are_left_out(self):
        SeatArrangement.objects.filter(hall__name="Hall 2").update(seat_number=None)

        rows = hall_summary_rows(DATE, PERIOD)

        self.assertEqual([r["hall"] for r in rows], ["Hall 10"])

    def test_classes_are_grouped_by_label(self):
        other = make_class(1, make_department("bb"), name="ND I")
        [student] = enrol(other, ["1111111111"])
        SeatArrangement.objects.create(
            date=DATE, period=PERIOD, student=student, seat_number=1,
            hall=make_hall("Hall 1", 4, 4), course=self.course, cls=other,
        )

        rows = hall_summary_rows(DATE, PERIOD)

        self.assertEqual(
            [r["class_name"] for r in rows], ["AC ND II", "AC ND II", "BB ND I"]
        )
