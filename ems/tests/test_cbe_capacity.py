"""CBE capacity and the exam-day estimate: a full-day CBE course has the CBE
centre to itself, and the estimate counts days the way the generator does
(one exam per class per day, CBE capacity included)."""
import random
from datetime import date, timedelta

from django.utils import timezone

from ems import tasks
from ems.models import Course, GenerationConstraints, SystemSettings, TimeTable
from ems.utils import can_schedule_full_day_cbe, cbe_min_days, cbe_sections, generate

from .helpers import listed_class, make_course, make_department, make_hall, quietly
from .test_student_lists import PipelineTestCase, allow_generation, run

MON = date(2026, 8, 17)


def cbe_course(code, cid, size):
    return {
        "id": cid, "code": code, "exam_type": "CBE",
        "classes": [{"id": cid, "name": f"C{cid}", "size": size,
                     "department_slug": "d", "faculty_slug": "f"}],
    }


def planned(courses, dates):
    """generate()'s schedule without touching the database."""
    summary = quietly(
        generate, dates, courses, [], [{"id": 1, "name": "h", "capacity": 100}],
        save=False,
    )
    return summary


class FullDayCbeTests(PipelineTestCase):
    def test_two_full_day_courses_never_share_a_day(self):
        summary = planned(
            [cbe_course("GST 101", 1, 6000), cbe_course("GST 102", 2, 6000)],
            [MON, MON + timedelta(days=1)],
        )

        days = {}
        for s in summary["schedules"]:
            days.setdefault(s["date"], set()).add(s["course"]["code"])
        self.assertEqual(sorted(len(codes) for codes in days.values()), [1, 1])

    def test_with_one_day_the_second_is_left_out_and_named(self):
        summary = planned(
            [cbe_course("GST 101", 1, 6000), cbe_course("GST 102", 2, 6000)], [MON]
        )

        self.assertEqual(summary["am_skipped"], 1)

    def test_a_day_with_a_smaller_cbe_paper_is_not_free_for_a_full_day(self):
        booked = [{"course": cbe_course("CSC 101", 3, 500), "date": MON, "period": "AM"}]

        self.assertFalse(
            can_schedule_full_day_cbe(booked, MON, cbe_course("GST 101", 1, 6000))
        )


class CbeMinDaysTests(PipelineTestCase):
    def test_full_day_courses_take_a_day_each_and_small_ones_share(self):
        cbe, _ = cbe_sections([
            cbe_course("GST 101", 1, 6000),
            cbe_course("GST 102", 2, 5000),
            cbe_course("CSC 101", 3, 3000),
            cbe_course("CSC 102", 4, 3000),  # 6000 small students: 2 days at 4500
        ])

        self.assertEqual(cbe_min_days(cbe), 4)

    def test_paper_courses_are_ignored(self):
        cbe, _ = cbe_sections([{**cbe_course("ACC 111", 1, 9000), "exam_type": "PBE"}])

        self.assertEqual(cbe_min_days(cbe), 0)


class OversizedCbeTests(PipelineTestCase):
    def test_a_one_class_paper_past_the_split_threshold_is_refused(self):
        cbe, refused = cbe_sections([cbe_course("GST 101", 1, 9500)])

        self.assertEqual(cbe, [])
        self.assertEqual(refused, [{"code": "GST 101", "students": 9500, "limit": 9000}])

    def test_the_generator_refuses_it_instead_of_skipping_it(self):
        summary = planned([cbe_course("GST 101", 1, 9500)], [MON, MON + timedelta(days=1)])

        self.assertEqual(summary["am_skipped"], 0)
        self.assertEqual([r["code"] for r in summary["refused_cbe"]], ["GST 101"])


class EstimateTests(PipelineTestCase):
    def setUp(self):
        super().setUp()
        random.seed(0)
        SystemSettings.objects.create(session="2026/2027", semester="1st Semester")
        self.dep = make_department("ac")
        make_hall("Hall A", 10, 10)
        make_hall("Hall B", 10, 10)

    def estimate(self):
        response = self.client.get("/api/timetable/estimate/")
        self.assertEqual(response.status_code, 200, response.data)
        return response.data

    def test_a_class_needs_a_day_for_every_exam_am_or_pm(self):
        GenerationConstraints.objects.create(
            configured_at=timezone.now(), class_period_overrides={"ND II": "PM"}
        )
        cls = listed_class(30, self.dep, name="ND II")
        for i in range(3):
            cls.courses.add(make_course(f"ACC 21{i}"))
            cls.courses.add(Course.objects.create(name="c", code=f"CBE 21{i}", exam_type="CBE"))

        estimate = self.estimate()

        self.assertEqual(estimate["per_class_min_days"], 6)
        self.assertEqual(estimate["bottleneck"], "per_class")

    def test_the_recommended_window_fits_every_exam(self):
        GenerationConstraints.objects.create(
            configured_at=timezone.now(), class_period_overrides={"ND II": "PM"},
            excluded_weekdays=[6],
        )
        cls = listed_class(30, self.dep, name="ND II")
        for i in range(3):
            cls.courses.add(make_course(f"ACC 21{i}"))
            cls.courses.add(Course.objects.create(name="c", code=f"CBE 21{i}", exam_type="CBE"))
        allow_generation()
        days = self.estimate()["recommended_exam_days"]
        end = MON + timedelta(days=days - 1 + days // 6)  # Sundays excluded

        job = run(tasks.generate_timetable_task, str(MON), str(end))

        self.assertEqual(job.result_data["warnings"], [], job.result_data)
        self.assertEqual(TimeTable.objects.count(), 6)

    def test_full_day_cbe_courses_can_be_the_bottleneck(self):
        GenerationConstraints.objects.create(
            configured_at=timezone.now(),
            cbe_fullday_threshold=40, cbe_daily_cap_per_period=40,
            cbe_autosplit_threshold=100,
        )
        for i in range(3):
            listed_class(50, self.dep, name=f"ND {i}").courses.add(
                Course.objects.create(name="c", code=f"GST 10{i}", exam_type="CBE")
            )

        estimate = self.estimate()

        self.assertEqual(estimate["cbe_min_days"], 3)
        self.assertEqual(estimate["min_exam_days"], 3)
        self.assertEqual(estimate["bottleneck"], "cbe_capacity")
