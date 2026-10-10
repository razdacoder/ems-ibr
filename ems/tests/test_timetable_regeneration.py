"""Generating the timetable again replaces it together with everything
planned from it, in one step that a failure leaves untouched."""
from unittest import mock

from django.utils import timezone

from ems import tasks
from ems.models import (
    Distribution, DistributionItem, SeatArrangement, SystemSettings, TimeTable,
)

from .helpers import listed_class, make_course, make_department, make_hall
from .test_student_lists import PipelineTestCase, allow_generation, run


class RegenerationTestCase(PipelineTestCase):
    def setUp(self):
        super().setUp()
        SystemSettings.objects.create(session="2026/2027", semester="1st Semester")
        dep = make_department("ac")
        for name, code in (("ND I", "ACC 111"), ("ND II", "ACC 211")):
            listed_class(30, dep, name=name).courses.add(make_course(code))
        make_hall("Hall A", 10, 10)
        make_hall("Hall B", 10, 10)
        allow_generation()

    def plan_everything(self):
        for task, args in (
            (tasks.generate_timetable_task, ("2026-08-17", "2026-08-21")),
            (tasks.generate_distribution_all_task, ()),
            (tasks.generate_allocation_all_task, ()),
        ):
            job = run(task, *args)
            self.assertEqual(job.status, "success", job.result_data)

    def publish(self):
        SystemSettings.objects.update(timetable_published_at=timezone.now())


class RegenerateTests(RegenerationTestCase):
    def test_old_distribution_and_seating_go_with_the_old_timetable(self):
        self.plan_everything()

        job = run(tasks.generate_timetable_task, "2026-08-17", "2026-08-21")

        self.assertEqual(job.status, "success", job.result_data)
        self.assertTrue(TimeTable.objects.exists())
        self.assertFalse(Distribution.objects.exists())
        self.assertFalse(DistributionItem.objects.exists())
        self.assertFalse(SeatArrangement.objects.exists())

    def test_the_new_timetable_distributes_and_seats_from_scratch(self):
        self.plan_everything()
        run(tasks.generate_timetable_task, "2026-08-17", "2026-08-21")

        job = run(tasks.generate_distribution_all_task)
        self.assertEqual(job.status, "success", job.result_data)
        self.assertEqual(job.result_data["slots_skipped"], 0)
        job = run(tasks.generate_allocation_all_task)
        self.assertEqual(job.status, "success", job.result_data)

        self.assertEqual(SeatArrangement.objects.filter(seat_number__isnull=False).count(), 60)


class FailedRegenerateTests(RegenerationTestCase):
    def test_a_failed_run_leaves_the_old_plan_and_publication(self):
        self.plan_everything()
        self.publish()
        before = (
            set(TimeTable.objects.values_list("id", flat=True)),
            Distribution.objects.count(),
            SeatArrangement.objects.count(),
        )

        with mock.patch.object(tasks, "save_to_timetable_db", side_effect=RuntimeError("disk")):
            job = run(tasks.generate_timetable_task, "2026-08-17", "2026-08-21")

        self.assertEqual(job.status, "failed")
        self.assertEqual(
            (
                set(TimeTable.objects.values_list("id", flat=True)),
                Distribution.objects.count(),
                SeatArrangement.objects.count(),
            ),
            before,
        )
        self.assertIsNotNone(SystemSettings.objects.get().timetable_published_at)

    def test_a_run_that_fails_while_planning_changes_nothing(self):
        self.plan_everything()
        self.publish()
        timetable = set(TimeTable.objects.values_list("id", flat=True))

        with mock.patch.object(tasks, "generate", side_effect=RuntimeError("boom")):
            job = run(tasks.generate_timetable_task, "2026-08-17", "2026-08-21")

        self.assertEqual(job.status, "failed")
        self.assertEqual(set(TimeTable.objects.values_list("id", flat=True)), timetable)
        self.assertIsNotNone(SystemSettings.objects.get().timetable_published_at)


class ProgressTests(RegenerationTestCase):
    def test_progress_follows_the_dates_as_they_are_planned(self):
        reports = []
        real_report = tasks._Progress.report

        def record(progress, pct, status, force=False):
            reports.append((pct, status))
            real_report(progress, pct, status, force=True)

        with mock.patch.object(tasks._Progress, "report", autospec=True, side_effect=record):
            job = run(tasks.generate_timetable_task, "2026-08-17", "2026-08-21")

        self.assertEqual(job.status, "success", job.result_data)
        self.assertEqual(job.progress_percentage, 100)
        percents = [pct for pct, _ in reports]
        self.assertEqual(percents, sorted(percents))
        per_date = [status for _, status in reports if status.startswith("Planned date")]
        self.assertEqual(per_date, [f"Planned date {n}/5" for n in range(1, 6)])
        # Planning, not a placeholder loop, moves the bar from 10% to 90%.
        self.assertEqual([p for p, s in reports if s.startswith("Planned date")][-1], 90)
