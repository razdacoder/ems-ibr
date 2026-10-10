"""One slot's distribution or allocation can be cleared and planned again
without touching the other slots, and distributing a slot replaces what it
had instead of adding a second plan."""
from datetime import timedelta

from django.utils import timezone

from ems import tasks
from ems.models import (
    BackgroundJob, Distribution, DistributionItem, SeatArrangement, SystemSettings,
    TimeTable,
)

from .helpers import listed_class, make_course, make_department, make_hall, schedule
from .test_student_lists import PipelineTestCase, allow_generation, run

MON, TUE = ("2026-08-17", "AM"), ("2026-08-18", "AM")


class SlotTestCase(PipelineTestCase):
    def setUp(self):
        super().setUp()
        SystemSettings.objects.create(session="2026/2027", semester="1st Semester")
        dep = make_department("ac")
        schedule(listed_class(30, dep, name="ND I"), make_course("ACC 111"), *MON)
        schedule(listed_class(30, dep, name="ND II"), make_course("ACC 211"), *TUE)
        make_hall("Hall A", 10, 10)
        make_hall("Hall B", 10, 10)
        allow_generation()

    def plan(self):
        for task in (tasks.generate_distribution_all_task, tasks.generate_allocation_all_task):
            job = run(task)
            self.assertEqual(job.status, "success", job.result_data)

    def slot(self, model, slot):
        return model.objects.filter(date=slot[0], period=slot[1])

    def clear(self, what, slot):
        return self.post(f"/api/{what}/clear/", {"date": slot[0], "period": slot[1]})


class ClearDistributionTests(SlotTestCase):
    def test_clears_the_slot_its_seats_and_its_planned_counts(self):
        self.plan()

        response = self.clear("distribution", MON)

        self.assertEqual(response.status_code, 200, response.data)
        self.assertFalse(self.slot(Distribution, MON).exists())
        self.assertFalse(self.slot(SeatArrangement, MON).exists())
        self.assertFalse(DistributionItem.objects.filter(schedule__date=MON[0]).exists())
        self.assertEqual(
            list(self.slot(TimeTable, MON).values_list("planned_students", flat=True)),
            [None],
        )

    def test_leaves_the_other_slots_alone(self):
        self.plan()
        seats = set(self.slot(SeatArrangement, TUE).values_list("id", flat=True))

        self.clear("distribution", MON)

        self.assertTrue(self.slot(Distribution, TUE).exists())
        self.assertEqual(set(self.slot(SeatArrangement, TUE).values_list("id", flat=True)), seats)

    def test_generate_all_plans_the_cleared_slot_again(self):
        self.plan()
        self.clear("distribution", MON)

        self.plan()

        self.assertEqual(self.slot(SeatArrangement, MON).filter(seat_number__isnull=False).count(), 30)


class ClearAllocationTests(SlotTestCase):
    def test_clears_only_the_slots_seats(self):
        self.plan()

        response = self.clear("allocation", MON)

        self.assertEqual(response.status_code, 200, response.data)
        self.assertFalse(self.slot(SeatArrangement, MON).exists())
        self.assertTrue(self.slot(Distribution, MON).exists())
        self.assertTrue(self.slot(SeatArrangement, TUE).exists())


class ClearGuardTests(SlotTestCase):
    def running_job(self, started_minutes_ago):
        job = BackgroundJob.objects.create(
            job_id=f"busy-{started_minutes_ago}", job_type="allocation_all",
            status="running", created_by=self.admin,
        )
        BackgroundJob.objects.filter(pk=job.pk).update(
            started_at=timezone.now() - timedelta(minutes=started_minutes_ago)
        )

    def test_refused_while_a_planning_job_runs(self):
        self.running_job(started_minutes_ago=1)

        self.assertEqual(self.clear("distribution", MON).status_code, 409)
        self.assertEqual(self.clear("allocation", MON).status_code, 409)

    def test_a_job_past_the_hard_time_limit_does_not_block(self):
        self.running_job(started_minutes_ago=31)

        self.assertEqual(self.clear("distribution", MON).status_code, 200)

    def test_rejects_a_bad_slot(self):
        for body in ({}, {"date": "17/08/2026", "period": "AM"}, {"date": MON[0], "period": "XX"}):
            self.assertEqual(self.post("/api/distribution/clear/", body).status_code, 400, body)

    def test_only_super_admins_clear(self):
        from .test_publication import officer

        self.client.force_authenticate(officer("ada@example.com", make_department("bf")))

        self.assertEqual(self.clear("distribution", MON).status_code, 403)


class LeftoverDistributionTests(SlotTestCase):
    def leave_only_shells(self, slot):
        """Distribution rows whose items went with their timetable rows."""
        DistributionItem.objects.filter(
            distribution__date=slot[0], distribution__period=slot[1]
        ).delete()

    def test_generate_all_redistributes_a_slot_left_with_empty_rows(self):
        run(tasks.generate_distribution_all_task)
        self.leave_only_shells(MON)

        job = run(tasks.generate_distribution_all_task)

        self.assertEqual(job.result_data["slots_skipped"], 1)  # TUE only
        self.assertTrue(DistributionItem.objects.filter(schedule__date=MON[0]).exists())
        self.assertFalse(self.slot(Distribution, MON).filter(items__isnull=True).exists())

    def test_single_slot_generate_is_not_blocked_by_empty_rows(self):
        run(tasks.generate_distribution_all_task)
        self.leave_only_shells(MON)

        response = self.post(
            "/api/distribution/generate/", {"date": MON[0], "period": MON[1]}
        )

        self.assertEqual(response.status_code, 202, response.data)

    def test_distributing_a_slot_twice_leaves_one_plan(self):
        run(tasks.generate_distribution_task, *MON)
        once = sorted(self.slot(Distribution, MON).values_list("hall_id", flat=True))

        run(tasks.generate_distribution_task, *MON)

        self.assertEqual(
            sorted(self.slot(Distribution, MON).values_list("hall_id", flat=True)), once
        )
        self.assertEqual(
            sum(DistributionItem.objects.filter(schedule__date=MON[0])
                .values_list("no_of_students", flat=True)),
            30,
        )
