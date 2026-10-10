"""A run that finishes without doing everything says what it left undone
(``result_data['warnings']``), and a bulk run with a failed slot fails."""
from ems import tasks
from ems.models import GenerationConstraints, SeatArrangement, SystemSettings

from .helpers import listed_class, make_course, make_department, make_hall
from .test_student_lists import PipelineTestCase, allow_generation, run


class WarningsTestCase(PipelineTestCase):
    def setUp(self):
        super().setUp()
        SystemSettings.objects.create(session="2026/2027", semester="1st Semester")
        self.dep = make_department("ac")
        make_hall("Hall A", 10, 10)
        make_hall("Hall B", 10, 10)

    def course(self, code, students, name):
        listed_class(students, self.dep, name=name).courses.add(make_course(code))

    def timetable(self, start="2026-08-17", end="2026-08-21"):
        allow_generation()
        return run(tasks.generate_timetable_task, start, end)


class TimetableWarningTests(WarningsTestCase):
    def test_courses_with_no_room_are_named_and_the_message_says_so(self):
        for i in range(3):
            self.course(f"ACC 11{i}", 80, f"ND {i}")  # one fits a 200 seat period

        job = self.timetable("2026-08-17", "2026-08-17")

        self.assertEqual(job.status, "success", job.result_data)
        [warning] = job.result_data["warnings"]
        self.assertEqual(warning["title"], "2 courses could not be scheduled")
        self.assertEqual(len(warning["items"]), 2)
        self.assertTrue(job.result_data["message"].startswith(
            "Timetable generated without 2 courses"
        ))

    def test_a_course_too_big_for_any_period_is_a_warning(self):
        self.course("GNS 101", 300, "ND I")  # more than the halls hold

        job = self.timetable()

        [warning] = job.result_data["warnings"]
        self.assertIn("too big for one period", warning["title"])
        self.assertEqual(warning["items"], ["GNS 101 (300 students)"])

    def test_a_complete_timetable_has_no_warnings(self):
        self.course("ACC 111", 30, "ND I")

        job = self.timetable()

        self.assertEqual(job.result_data["warnings"], [])
        self.assertEqual(job.result_data["message"], "Timetable generated successfully")


class AllocationWarningTests(WarningsTestCase):
    def plan(self, students=90):
        self.course("ACC 111", students, "ND I")
        self.timetable("2026-08-17", "2026-08-17")
        run(tasks.generate_distribution_all_task)

    def test_a_failed_slot_fails_the_bulk_run_and_is_named(self):
        self.plan()
        GenerationConstraints.objects.update(pbe_hall_utilization="0.30")

        job = run(tasks.generate_allocation_all_task)

        self.assertEqual(job.status, "failed")
        self.assertEqual(len(job.result_data["failed_slots"]), 1)
        self.assertIn("2026-08-17 AM", job.error_message)
        self.assertIn("retry", job.error_message)

    def test_retry_finishes_once_the_cause_is_fixed(self):
        self.plan()
        GenerationConstraints.objects.update(pbe_hall_utilization="0.30")
        run(tasks.generate_allocation_all_task)
        GenerationConstraints.objects.update(pbe_hall_utilization="1.00")

        job = run(tasks.generate_allocation_all_task)

        self.assertEqual(job.status, "success", job.error_message)
        self.assertEqual(job.result_data["warnings"], [])

    def test_students_left_without_a_seat_are_counted_by_hall(self):
        self.plan()
        run(tasks.generate_allocation_all_task)
        seated = SeatArrangement.objects.filter(seat_number__isnull=False)
        hall = seated.first().hall
        SeatArrangement.objects.filter(pk=seated.first().pk).update(seat_number=None)

        [warning] = tasks._unplaced_students_warning("2026-08-17", "AM")

        self.assertEqual(warning["title"], "1 student has no seat on 2026-08-17 AM")
        self.assertEqual(warning["items"], [f"{hall.name}: 1"])
