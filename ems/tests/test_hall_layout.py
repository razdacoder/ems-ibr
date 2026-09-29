"""Halls that are not a full rows x columns rectangle.

A hall may carry a seat mask (``Hall.layout``): rows of different lengths,
aisles, pillars. Timetable, distribution, allocation, reconcile and manual
assignment all read seats through ``seating_rules.HallLayout``. A hall with
no mask must behave exactly as before.
"""
import io
import random
from datetime import date

from django.test import SimpleTestCase, TestCase

from ems import seating_rules
from ems.api.serializers.hall import HallSerializer
from ems.models import Hall, SeatArrangement, TimeTable
from ems.seating_rules import STRICT, hall_layout, mask_from_row_seats, normalise_mask
from ems.upload_handlers import UploadError, upload_halls
from ems.utils import (
    allocate_students_to_seats,
    convert_hall_to_dict,
    distribute_classes_to_halls,
    hall_effective_capacity,
    is_valid_position,
    reconcile_unplaced,
)

from .helpers import (
    enrol, listed_class, make_class, make_course, no_fill_cap, quietly, schedule,
)

DATE, PERIOD = "2026-08-17", "AM"
EIGHT = seating_rules.neighbours(STRICT)

# Short front row centred, an aisle down column 4, a pillar at (3, 1).
AUDITORIUM = (
    "..XX.XX..",
    ".XXX.XXX.",
    "XXXX.XXXX",
    "X.XX.XXXX",
    "XXXX.XXXX",
    "XXXX.XXXX",
)


def make_shaped_hall(name, mask):
    rows, cols = len(mask), len(mask[0])
    return Hall.objects.create(
        name=name, capacity=rows * cols, max_students=0, min_courses=0,
        rows=rows, columns=cols, layout=list(mask),
    )


def conflicts(seat_positions, students, layout):
    """Same-course pairs 8-dir adjacent, and seats that are not real seats."""
    course_of = {s["name"]: s["course"] for s in students}
    grid, bad = {}, []
    for name, number in seat_positions.items():
        cell = layout.cell(number)
        if cell is None:
            bad.append(("no such seat", number))
        else:
            grid[cell] = course_of[name]
    for (r, c), course in grid.items():
        for dr, dc in EIGHT:
            if grid.get((r + dr, c + dc)) == course:
                bad.append((course, (r, c), (r + dr, c + dc)))
    return bad


class MaskTests(SimpleTestCase):
    def test_row_seats_are_placed_by_alignment(self):
        _, _, left = mask_from_row_seats([2, 4], "left")
        _, _, center = mask_from_row_seats([2, 4], "center")
        _, _, right = mask_from_row_seats([2, 4], "right")
        self.assertEqual(left, ("XX..", "XXXX"))
        self.assertEqual(center, (".XX.", "XXXX"))
        self.assertEqual(right, ("..XX", "XXXX"))

    def test_equal_rows_are_a_plain_rectangle(self):
        self.assertEqual(mask_from_row_seats([5, 5, 5]), (3, 5, None))

    def test_bad_masks_are_refused(self):
        with self.assertRaises(ValueError):
            normalise_mask(2, 3, ["XXX"])  # wrong row count
        with self.assertRaises(ValueError):
            normalise_mask(1, 3, ["XX"])  # wrong width
        with self.assertRaises(ValueError):
            normalise_mask(1, 3, ["X?X"])  # unknown character
        with self.assertRaises(ValueError):
            normalise_mask(1, 3, ["..."])  # no seats
        with self.assertRaises(ValueError):
            mask_from_row_seats([3, 4], "middle")

    def test_seats_are_numbered_over_real_seats_only(self):
        layout = hall_layout(2, 3, (".X.", "XXX"))
        self.assertEqual(layout.seat_count, 4)
        self.assertEqual(layout.cell(1), (0, 1))
        self.assertEqual(layout.cell(2), (1, 0))
        self.assertIsNone(layout.cell(5))
        self.assertEqual(layout.seat_number(1, 2), 4)
        self.assertFalse(layout.is_seat(0, 0))


class RectangleRegressionTests(SimpleTestCase):
    """No mask: the old closed-form numbers, unchanged."""

    SIZES = [(1, 1), (1, 7), (2, 2), (3, 5), (10, 10), (14, 15), (15, 20)]

    def test_numbering_and_quarter_maths_match_the_old_formulas(self):
        for rows, cols in self.SIZES:
            with self.subTest(rows=rows, cols=cols):
                layout = hall_layout(rows, cols)
                self.assertEqual(
                    [layout.seat_number(r, c) for r in range(rows) for c in range(cols)],
                    [r * cols + c + 1 for r in range(rows) for c in range(cols)],
                )
                self.assertEqual(
                    seating_rules.largest_quarter(rows, cols),
                    ((rows + 1) // 2) * ((cols + 1) // 2),
                )
                self.assertEqual(
                    seating_rules.even_half(rows, cols),
                    ((rows + 1) // 2) * ((cols + 1) // 2) + (rows // 2) * (cols // 2),
                )
                self.assertEqual(
                    hall_effective_capacity(rows, cols, "checkerboard"),
                    (rows * cols + 1) // 2,
                )
                self.assertEqual(
                    hall_effective_capacity(rows, cols, "sequential"), rows * cols
                )

    def test_a_mask_of_all_seats_is_the_same_hall(self):
        full = ("XXXXX",) * 4
        self.assertEqual(normalise_mask(4, 5, full), None)
        self.assertEqual(
            seating_rules.relaxed_quarter_usage(4, 5, 7),
            seating_rules.relaxed_quarter_usage(4, 5, 7, mask=None),
        )


class ShapedCapacityTests(SimpleTestCase):
    def test_capacity_counts_real_seats_only(self):
        rows, cols = len(AUDITORIUM), len(AUDITORIUM[0])
        layout = hall_layout(rows, cols, AUDITORIUM)
        seats = sum(line.count("X") for line in AUDITORIUM)
        self.assertEqual(layout.seat_count, seats)
        self.assertEqual(
            hall_effective_capacity(rows, cols, "sequential", mask=AUDITORIUM), seats
        )
        even = sum(1 for r, c in layout.seats if r % 2 == c % 2)
        self.assertEqual(
            hall_effective_capacity(rows, cols, "checkerboard", mask=AUDITORIUM), even
        )
        self.assertEqual(sum(layout.quarters.values()), seats)
        self.assertEqual(
            seating_rules.hall_per_course_slice(rows, cols, mask=AUDITORIUM),
            min(layout.quarters.values()),
        )
        self.assertEqual(
            seating_rules.strict_limit([(rows, cols, AUDITORIUM)]),
            min(layout.quarters.values()),
        )

    def test_seats_across_an_aisle_are_not_neighbours(self):
        mask = ("XX.XX",)
        layout = hall_layout(1, 5, mask)
        seat_map = {layout.seat_number(0, 1): "A"}
        # (0, 3) is across the aisle from (0, 1): allowed.
        self.assertTrue(
            is_valid_position(layout.seat_number(0, 3), "A", seat_map, 1, 5, mask=mask)
        )
        # (0, 0) is beside (0, 1): refused.
        self.assertFalse(
            is_valid_position(layout.seat_number(0, 0), "A", seat_map, 1, 5, mask=mask)
        )
        # The hall has 4 seats, so seat 5 does not exist.
        self.assertFalse(is_valid_position(5, "A", {}, 1, 5, mask=mask))

    def test_the_allocator_only_uses_real_seats(self):
        rows, cols = len(AUDITORIUM), len(AUDITORIUM[0])
        layout = hall_layout(rows, cols, AUDITORIUM)
        students = [
            {"name": f"{code}{n:03}", "course": code}
            for code, size in (("A", 8), ("B", 7), ("C", 6))
            for n in range(size)
        ]
        seats, unplaced, _ = quietly(
            allocate_students_to_seats, students, rows, cols, mask=AUDITORIUM
        )
        self.assertEqual(unplaced, [])
        self.assertEqual(conflicts(seats, students, layout), [])
        self.assertEqual(len(set(seats.values())), len(students))


class ShapedPipelineTests(TestCase):
    def setUp(self):
        random.seed(0)

    def test_distribution_hands_each_hall_only_what_its_seats_can_take(self):
        halls = [make_shaped_hall(f"Aud {n}", AUDITORIUM) for n in range(3)]
        for code, size in (("GNS 101", 20), ("MTH 101", 14), ("PHY 101", 9)):
            cls = listed_class(size)
            schedule(cls, make_course(code))

        hall_dicts = convert_hall_to_dict(
            Hall.objects.all(), safety_factor=1.0, pattern="sequential"
        )
        timetables = list(
            TimeTable.objects.select_related("course", "class_obj__department")
        )
        result = distribute_classes_to_halls(timetables, hall_dicts)

        given = sum(i["student_range"] for h in result for i in h["classes"])
        self.assertEqual(given, 43)
        layout = seating_rules.layout_of(halls[0])
        for hall_result in result:
            students = [
                {"name": f"{item['id']}-{n:04}", "course": item["course"]}
                for item in hall_result["classes"]
                for n in range(item["student_range"])
            ]
            seats, unplaced, _ = quietly(
                allocate_students_to_seats, students, layout.rows, layout.cols,
                mask=AUDITORIUM,
            )
            self.assertEqual(unplaced, [], hall_result["name"])
            self.assertEqual(conflicts(seats, students, layout), [])

    def test_reconcile_reseats_onto_a_real_seat(self):
        no_fill_cap()
        hall = make_shaped_hall("Aud", (".X.", "XXX"))
        cls = make_class(1)
        course = make_course("GNS 101")
        schedule(cls, course)
        [student] = enrol(cls, ["M0001"])
        SeatArrangement.objects.create(
            date=date(2026, 8, 17), period=PERIOD, student=student,
            seat_number=None, hall=hall, course=course, cls=cls,
        )

        self.assertEqual(quietly(reconcile_unplaced, DATE, PERIOD), 1)
        seat = SeatArrangement.objects.get().seat_number
        self.assertIsNotNone(seating_rules.layout_of(hall).cell(seat))


class HallInputTests(TestCase):
    def test_row_seats_set_rows_columns_and_layout(self):
        serializer = HallSerializer(data={
            "name": "Aud", "capacity": 20, "rows": 1, "columns": 1, "row_seats": [2, 4], "align": "center",
        })
        self.assertTrue(serializer.is_valid(), serializer.errors)
        hall = serializer.save()
        self.assertEqual((hall.rows, hall.columns), (2, 4))
        self.assertEqual(hall.layout, [".XX.", "XXXX"])
        self.assertEqual(hall.seat_count, 6)
        self.assertEqual(HallSerializer(hall).data["row_seats"], [2, 4])

    def test_changing_rows_without_a_matching_layout_is_refused(self):
        hall = make_shaped_hall("Aud", (".XX.", "XXXX"))
        serializer = HallSerializer(hall, data={"rows": 3}, partial=True)
        self.assertFalse(serializer.is_valid())
        self.assertIn("layout", serializer.errors)

    def test_a_null_layout_makes_the_hall_a_rectangle_again(self):
        hall = make_shaped_hall("Aud", (".XX.", "XXXX"))
        serializer = HallSerializer(hall, data={"layout": None}, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertIsNone(serializer.save().layout)

    def test_upload_reads_row_seats_and_align(self):
        csv = (
            "EXAM VENUE,CAPACITY,MAX STUDENTS,MIN COURSES,ROWS,COLS,ROW_SEATS,ALIGN\n"
            'Aud,20,0,0,,,"2,4",right\n'
            "Box,9,0,0,3,3,,\n"
        )
        upload_halls(io.StringIO(csv))
        self.assertEqual(Hall.objects.get(name="Aud").layout, ["..XX", "XXXX"])
        box = Hall.objects.get(name="Box")
        self.assertEqual((box.rows, box.columns, box.layout), (3, 3, None))

    def test_upload_needs_no_deprecated_columns(self):
        upload_halls(io.StringIO("EXAM VENUE,CAPACITY,ROWS,COLS\nBox,9,3,3\n"))
        self.assertEqual(Hall.objects.get(name="Box").seat_count, 9)

    def test_upload_without_a_shape_is_refused(self):
        csv = (
            "EXAM VENUE,CAPACITY,MAX STUDENTS,MIN COURSES,ROWS,COLS,ROW_SEATS\n"
            "Aud,20,0,0,,,\n"
        )
        with self.assertRaises(UploadError):
            upload_halls(io.StringIO(csv))


class SeatOrderTests(TestCase):
    """How a hall numbers its seats (seating_rules.SEAT_ORDERS)."""

    def numbers(self, seat_order, rows=2, cols=3, mask=None):
        """The grid as rows of seat numbers (None = no seat)."""
        layout = hall_layout(rows, cols, mask, seat_order)
        return [
            [layout.seat_number(r, c) if layout.is_seat(r, c) else None for c in range(cols)]
            for r in range(rows)
        ]

    def test_each_order_numbers_the_grid_as_drawn(self):
        self.assertEqual(self.numbers("rows"), [[1, 2, 3], [4, 5, 6]])
        self.assertEqual(self.numbers("rows_rtl"), [[3, 2, 1], [6, 5, 4]])
        self.assertEqual(self.numbers("snake"), [[1, 2, 3], [6, 5, 4]])
        self.assertEqual(self.numbers("snake_rtl"), [[3, 2, 1], [4, 5, 6]])
        self.assertEqual(self.numbers("columns"), [[1, 3, 5], [2, 4, 6]])
        self.assertEqual(self.numbers("columns_snake"), [[1, 4, 5], [2, 3, 6]])

    def test_a_snake_skips_the_gaps(self):
        self.assertEqual(
            self.numbers("snake", cols=4, mask=("XX.X", "X.XX")),
            [[1, 2, None, 3], [6, None, 5, 4]],
        )

    def test_the_relaxed_model_matches_the_allocator_in_every_order(self):
        for seat_order in seating_rules.SEAT_ORDERS:
            for rows, cols in [(5, 5), (4, 7)]:
                layout = hall_layout(rows, cols, None, seat_order)
                for k in range(0, seating_rules.even_half(rows, cols) + 1, 3):
                    with self.subTest(seat_order=seat_order, rows=rows, cols=cols, k=k):
                        students = [{"name": f"R{n:03}", "course": "R"} for n in range(k)]
                        seats, unplaced, _ = quietly(
                            allocate_students_to_seats, students, rows, cols,
                            relaxed_courses={"R"}, seat_order=seat_order,
                        )
                        self.assertEqual(unplaced, [])
                        cells = [layout.cell(n) for n in seats.values()]
                        actual = (
                            sum(1 for r, c in cells if r % 2 == 0 and c % 2 == 0),
                            sum(1 for r, c in cells if r % 2 == 1 and c % 2 == 1),
                        )
                        self.assertEqual(
                            seating_rules.relaxed_quarter_usage(
                                rows, cols, k, seat_order=seat_order
                            ),
                            actual,
                        )

    def test_matric_order_follows_the_numbering(self):
        students = [{"name": f"M{n:03}", "course": "A"} for n in range(12)]
        seats, unplaced, _ = quietly(
            allocate_students_to_seats, students, 6, 8, seat_order="snake"
        )
        self.assertEqual(unplaced, [])
        by_matric = [seats[s["name"]] for s in students]
        self.assertEqual(by_matric, sorted(by_matric))
        layout = hall_layout(6, 8, None, "snake")
        self.assertEqual(conflicts(seats, students, layout), [])

    def test_the_order_is_set_through_the_api_and_the_upload(self):
        serializer = HallSerializer(data={
            "name": "Aud", "capacity": 9, "rows": 3, "columns": 3, "seat_order": "snake",
        })
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.save().seat_order, "snake")

        upload_halls(io.StringIO(
            "EXAM VENUE,CAPACITY,ROWS,COLS,SEAT_ORDER\nBox,9,3,3,columns\n"
        ))
        self.assertEqual(Hall.objects.get(name="Box").seat_order, "columns")
        with self.assertRaises(UploadError):
            upload_halls(io.StringIO(
                "EXAM VENUE,CAPACITY,ROWS,COLS,SEAT_ORDER\nBox,9,3,3,zigzag\n"
            ))
