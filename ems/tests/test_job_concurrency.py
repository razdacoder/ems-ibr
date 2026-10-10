"""One generation job at a time, and a killed job does not stay "running"
forever (where it could be neither retried, deleted, nor got past)."""
from datetime import timedelta
from unittest import mock

from django.utils import timezone

from ems.api.views import jobs as job_views
from ems.models import BackgroundJob, SystemSettings

from .helpers import listed_class, make_course, make_department, make_hall, schedule
from .test_student_lists import PipelineTestCase, allow_generation


class ConcurrencyTestCase(PipelineTestCase):
    def setUp(self):
        super().setUp()
        SystemSettings.objects.create(session="2026/2027", semester="1st Semester")
        schedule(
            listed_class(30, make_department("ac"), name="ND I"),
            make_course("ACC 111"), "2026-08-17", "AM",
        )
        make_hall("Hall A", 10, 10)
        allow_generation()

    def job(self, status, minutes_ago=0, job_type="allocation_all", job_id=None):
        job = BackgroundJob.objects.create(
            job_id=job_id or f"{status}-{minutes_ago}-{job_type}", job_type=job_type,
            status=status, created_by=self.admin,
        )
        BackgroundJob.objects.filter(pk=job.pk).update(
            started_at=timezone.now() - timedelta(minutes=minutes_ago)
        )
        return job

    def distribute_all(self):
        return self.post("/api/distribution/generate-all/")


class OneJobAtATimeTests(ConcurrencyTestCase):
    def test_a_second_run_is_refused_while_the_first_is_queued(self):
        self.assertEqual(self.distribute_all().status_code, 202)

        response = self.distribute_all()

        self.assertEqual(response.status_code, 409)
        self.assertIn("distribution job is still pending", response.data["detail"])

    def test_any_stage_blocks_any_other(self):
        self.job("running", job_type="timetable")

        response = self.distribute_all()

        self.assertEqual(response.status_code, 409)
        self.assertIn("timetable job is still running", response.data["detail"])

    def test_a_finished_job_does_not_block(self):
        self.job("success")
        self.job("failed")

        self.assertEqual(self.distribute_all().status_code, 202)

    def test_clearing_a_slot_waits_too(self):
        self.job("running", job_type="timetable")

        response = self.post(
            "/api/distribution/clear/", {"date": "2026-08-17", "period": "AM"}
        )

        self.assertEqual(response.status_code, 409)
        self.assertIn("before clearing a slot", response.data["detail"])


class StaleJobTests(ConcurrencyTestCase):
    def test_a_job_past_the_time_limit_is_failed_and_does_not_block(self):
        job = self.job("running", minutes_ago=31)

        self.assertEqual(self.distribute_all().status_code, 202)

        job.refresh_from_db()
        self.assertEqual(job.status, "failed")
        self.assertIn("Stopped without finishing", job.error_message)
        self.assertIsNotNone(job.completed_at)

    def test_a_job_no_worker_picked_up_says_so(self):
        job = self.job("pending", minutes_ago=31)

        self.client.get("/api/jobs/")

        job.refresh_from_db()
        self.assertEqual(job.status, "failed")
        self.assertIn("Never started", job.error_message)

    def test_a_job_within_the_time_limit_is_left_alone(self):
        job = self.job("running", minutes_ago=29)

        self.client.get("/api/jobs/")

        job.refresh_from_db()
        self.assertEqual(job.status, "running")

    def test_a_stale_job_can_then_be_deleted(self):
        job = self.job("running", minutes_ago=31)

        response = self.client.delete(f"/api/jobs/{job.job_id}/")

        self.assertEqual(response.status_code, 204)


class RetryTests(ConcurrencyTestCase):
    def test_retry_queues_the_task_even_in_a_fresh_process(self):
        failed = self.job("failed", job_type="distribution_all", job_id="old-run")
        job_views._TASK_MAP.clear()  # nothing has been generated in this process

        with mock.patch(
            "ems.tasks.generate_distribution_all_task.apply_async"
        ) as queued, self.captureOnCommitCallbacks(execute=True):
            response = self.post(f"/api/jobs/{failed.job_id}/retry/")

        self.assertEqual(response.status_code, 202, response.data)
        queued.assert_called_once()

    def test_retry_is_refused_while_another_job_runs(self):
        failed = self.job("failed", job_type="distribution_all", job_id="old-run")
        self.job("running", job_type="allocation_all")

        response = self.post(f"/api/jobs/{failed.job_id}/retry/")

        self.assertEqual(response.status_code, 409)
