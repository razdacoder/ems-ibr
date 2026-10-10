"""Timetable generation books no period fuller than distribution can seat.

Regression cover for the Oct 2026 run: periods booked to their seat total
(8,098 of 8,100) left 84 classes without a hall, because course limits and
the one-quarter-per-course rule stop the packer filling every seat."""
from datetime import date

from ems import tasks
from ems.models import GenerationConstraints, SystemSettings, TimeTable
from ems.utils import (
    classify_courses, convert_hall_to_dict, courses_short_of_halls, generate,
    get_courses, get_halls, split_course,
)

from .helpers import listed_class, make_course, make_department, make_hall, quietly
from .test_student_lists import PipelineTestCase, allow_generation, run

MON, TUE = date(2026, 8, 17), date(2026, 8, 18)


class FitTestCase(PipelineTestCase):
    """One 10 x 10 hall at 100%: 100 seats, at most 4 courses. Five courses
    of 20 students add up to exactly 100 seats, so seat counting books all
    five into one period; the fifth course has no hall it may join."""

    def setUp(self):
        super().setUp()
        SystemSettings.objects.create(session="2026/2027", semester="1st Semester")
        GenerationConstraints.objects.all().delete()
        GenerationConstraints.objects.create(seat_pattern="sequential", pbe_hall_utilization=1)
        make_hall("Hall A", 10, 10)
        dep = make_department("ac")
        for i in range(5):
            listed_class(20, dep, name=f"ND {i}").courses.add(make_course(f"ACC 11{i}"))
        allow_generation()

    def plan(self, fit_check=None):
        courses, _ = classify_courses(get_courses(), 1000, 2000)
        am, pm = split_course(courses)
        return quietly(
            generate, [MON, TUE], am, pm, get_halls(pattern="sequential"),
            pbe_utilization=1.0, save=False, fit_check=fit_check,
        )

    def halls(self):
        constraints = GenerationConstraints.objects.get()
        from ems.models import Hall
        return convert_hall_to_dict(
            Hall.objects.all(), safety_factor=1.0, pattern="sequential",
            course_limits=constraints.hall_course_limits,
        )


class CoursesShortOfHallsTests(FitTestCase):
    def test_names_the_course_the_halls_cannot_take(self):
        courses, _ = classify_courses(get_courses(), 1000, 2000)

        short = courses_short_of_halls(courses, self.halls())

        self.assertEqual(len(short), 1)

    def test_four_courses_fit(self):
        courses, _ = classify_courses(get_courses(), 1000, 2000)

        self.assertEqual(courses_short_of_halls(courses[:4], self.halls()), [])


class GenerateFitTests(FitTestCase):
    def per_date(self, summary):
        dates = {}
        for s in summary["schedules"]:
            dates.setdefault(s["date"], set()).add(s["course"]["code"])
        return sorted(len(codes) for codes in dates.values())

    def test_seat_counting_alone_overfills_the_period(self):
        self.assertEqual(self.per_date(self.plan()), [5])

    def test_the_fit_check_moves_the_extra_course_to_the_next_date(self):
        summary = self.plan(lambda courses: courses_short_of_halls(courses, self.halls()))

        self.assertEqual(self.per_date(summary), [1, 4])
        self.assertEqual(summary["rebooked_after_fit_check"], 1)
        self.assertEqual(summary["am_skipped"], 0)


class PipelineFitTests(FitTestCase):
    def test_every_class_gets_hall_space_after_a_full_run(self):
        job = run(tasks.generate_timetable_task, str(MON), str(TUE))
        self.assertEqual(job.status, "success", job.result_data)
        self.assertEqual(TimeTable.objects.values("date").distinct().count(), 2)

        job = run(tasks.generate_distribution_all_task)

        self.assertEqual(job.status, "success", job.result_data)
        self.assertEqual(job.result_data["unplaced_by_class"], [])
        self.assertEqual(job.result_data["warnings"], [])
