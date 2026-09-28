"""Spec 0001: every planning stage counts the uploaded student list.

Covers the empty class block (timetable, distribution), the inactive switch,
``planned_students`` and the allocation staleness refusal, the readiness
endpoint, and ``Class.size`` staying in step with the list.
"""
import random
import re
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from ems import tasks
from ems.models import (
    BackgroundJob,
    Class,
    Distribution,
    Faculty,
    GenerationConstraints,
    SeatArrangement,
    Student,
    TimeTable,
    User,
)
from ems.upload_handlers import upload_class_students

from .helpers import (
    enrol,
    listed_class,
    make_class,
    make_course,
    make_department,
    make_hall,
    quietly,
    schedule,
)

DATE, PERIOD = "2026-08-17", "AM"
IN_MEMORY_LAYER = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}


def super_admin():
    return User.objects.create_user(
        email="sa@example.com", password="x", role=User.Role.SUPER_ADMIN, is_staff=True
    )


def allow_generation():
    """Everything ``_assert_generation_allowed`` needs, for the departments
    that exist so far. Call again after adding departments."""
    constraints = GenerationConstraints.objects.first() or GenerationConstraints(
        configured_at=timezone.now()
    )
    constraints.cbe_faculty_groups = {f.slug: 1 for f in Faculty.objects.all()}
    constraints.save()


def run(task, *args):
    """Run a task inline against a fresh job; return the job afterwards."""
    job = BackgroundJob.objects.create(
        job_id=f"job-{random.random()}", job_type="distribution",
        created_by=User.objects.first(),
    )
    quietly(task.apply, args=[job.job_id, job.created_by_id, *args])
    job.refresh_from_db()
    return job


@override_settings(CHANNEL_LAYERS=IN_MEMORY_LAYER)
class PipelineTestCase(TestCase):
    def setUp(self):
        random.seed(0)
        self.admin = super_admin()
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def post(self, url, data=None):
        return self.client.post(url, data or {}, format="json")


class StudentCountTests(TestCase):
    def test_counts_only_students_of_the_class_department(self):
        cls = listed_class(3)
        stray = make_department("zz")
        Student.objects.create(
            first_name="A", last_name="B", matric_no="X1", email="x@example.com",
            department=stray, level=cls,
        )

        self.assertEqual(Class.objects.student_count_map()[cls.id], 3)
        self.assertEqual(Class.objects.get(pk=cls.pk).student_count, 3)

    def test_a_class_with_a_declared_size_and_no_list_counts_zero(self):
        cls = make_class(40)

        self.assertEqual(Class.objects.student_count_map()[cls.id], 0)

    def test_total_skips_inactive_classes(self):
        listed_class(5)
        off = listed_class(7)
        off.is_active = False
        off.save()

        self.assertEqual(Class.objects.total_student_count(), 5)


class NoDeclaredSizeInPlanningTests(TestCase):
    """Key invariant: no planning code reads ``Class.size``."""

    PLANNING = [
        "utils.py", "tasks.py", "readiness.py",
        "api/views/scheduling.py", "api/views/jobs.py", "api/views/system.py",
    ]

    def test_planning_modules_never_read_class_size(self):
        root = Path(__file__).resolve().parent.parent
        for name in self.PLANNING:
            source = (root / name).read_text()
            with self.subTest(module=name):
                self.assertIsNone(re.search(r"\.size\b", source))


class TimetableGateTests(PipelineTestCase):
    URL = "/api/timetable/generate/"
    BODY = {"start_date": "2026-08-17", "end_date": "2026-08-22"}

    def setUp(self):
        super().setUp()
        make_hall("Hall A", 10, 10)
        self.course = make_course("GNS 101")
        self.full = listed_class(4, name="ND I")
        self.empty = make_class(40, make_department("wft"), name="HND I")
        for cls in (self.full, self.empty):
            cls.courses.add(self.course)
        allow_generation()

    def test_refuses_and_names_an_active_class_with_no_list(self):
        response = self.post(self.URL, self.BODY)

        self.assertEqual(response.status_code, 409)
        self.assertIn("WFT HND I", response.data["detail"])
        self.assertIn("readiness", response.data["detail"])
        self.assertFalse(BackgroundJob.objects.exists())

    def test_readiness_lists_the_empty_class(self):
        report = self.client.get("/api/readiness/?stage=timetable").data

        self.assertFalse(report["ready"])
        self.assertEqual(
            [(c["label"], c["courses"]) for c in report["empty_classes"]],
            [("WFT HND I", ["GNS 101"])],
        )

    def test_an_inactive_empty_class_no_longer_blocks(self):
        self.empty.is_active = False
        self.empty.save()

        response = self.post(self.URL, self.BODY)

        self.assertEqual(response.status_code, 202)

    def test_the_task_refuses_too_when_reached_anyway(self):
        job = run(tasks.generate_timetable_task, "2026-08-17", "2026-08-22")

        self.assertEqual(job.status, "failed")
        self.assertEqual(
            [c["label"] for c in job.result_data["empty_classes"]], ["WFT HND I"]
        )

    def test_the_timetable_leaves_out_inactive_classes(self):
        self.empty.is_active = False
        self.empty.save()

        job = run(tasks.generate_timetable_task, "2026-08-17", "2026-08-22")

        self.assertEqual(job.status, "success", job.result_data)
        self.assertEqual(
            set(TimeTable.objects.values_list("class_obj_id", flat=True)),
            {self.full.id},
        )


class DistributionTests(PipelineTestCase):
    def setUp(self):
        super().setUp()
        make_hall("Hall A", 10, 10)
        make_hall("Hall B", 10, 10)
        self.cls = listed_class(12, make_department("ac"), name="ND I")
        self.other = listed_class(9, make_department("bf"), name="ND I")
        self.row = schedule(self.cls, make_course("GNS 101"), DATE, PERIOD)
        self.other_row = schedule(self.other, make_course("ACC 111"), DATE, PERIOD)
        allow_generation()

    def distribute(self):
        return run(tasks.generate_distribution_task, DATE, PERIOD)

    def test_records_the_count_it_planned_for_every_row(self):
        job = self.distribute()

        self.assertEqual(job.status, "success", job.result_data)
        self.row.refresh_from_db()
        self.other_row.refresh_from_db()
        self.assertEqual(self.row.planned_students, 12)
        self.assertEqual(self.other_row.planned_students, 9)
        self.assertEqual(job.result_data["unplaced_by_class"], [])

    def test_refuses_a_slot_with_an_empty_active_class(self):
        empty = make_class(40, make_department("wft"), name="HND I")
        schedule(empty, make_course("WFT 101"), DATE, PERIOD)
        allow_generation()

        response = self.post(
            "/api/distribution/generate/", {"date": DATE, "period": PERIOD}
        )
        job = self.distribute()

        self.assertEqual(response.status_code, 409)
        self.assertIn("WFT HND I", response.data["detail"])
        self.assertEqual(job.status, "failed")
        self.assertFalse(Distribution.objects.exists())

    def test_generate_all_checks_every_slot_before_distributing_any(self):
        empty = make_class(40, make_department("wft"), name="HND I")
        schedule(empty, make_course("WFT 101"), "2026-08-18", "PM")
        allow_generation()

        response = self.post("/api/distribution/generate-all/")
        job = run(tasks.generate_distribution_all_task)

        self.assertEqual(response.status_code, 409)
        self.assertEqual(job.status, "failed")
        self.assertFalse(Distribution.objects.exists())

    def test_skips_inactive_rows_and_reports_them(self):
        self.other.is_active = False
        self.other.save()

        job = self.distribute()

        self.assertEqual(job.status, "success", job.result_data)
        self.other_row.refresh_from_db()
        self.assertIsNone(self.other_row.planned_students)
        seated_rows = set(
            Distribution.objects.values_list("items__schedule_id", flat=True)
        )
        self.assertEqual(seated_rows, {self.row.id})
        self.assertEqual(
            job.result_data["skipped_inactive"],
            [{"date": DATE, "period": PERIOD, "class_id": self.other.id,
              "label": "BF ND I", "course": "ACC 111"}],
        )

    def test_reports_a_course_too_big_for_the_halls_without_blocking_allocation(self):
        big = listed_class(80, make_department("gs"), name="ND II")
        big_row = schedule(big, make_course("GNS 202"), DATE, PERIOD)

        job = self.distribute()

        self.assertEqual(
            [(u["timetable_id"], u["planned"], u["assigned"])
             for u in job.result_data["unplaced_by_class"]],
            [(big_row.id, 80, 50)],
        )
        report = self.client.get(
            f"/api/readiness/?stage=allocation&date={DATE}&period={PERIOD}"
        ).data
        self.assertTrue(report["ready"])


class AllocationStalenessTests(PipelineTestCase):
    def setUp(self):
        super().setUp()
        make_hall("Hall A", 10, 10)
        self.cls = listed_class(6, make_department("ac"), name="ND I")
        schedule(self.cls, make_course("GNS 101"), DATE, PERIOD)
        schedule(self.cls, make_course("GNS 102"), "2026-08-18", PERIOD)
        allow_generation()
        run(tasks.generate_distribution_all_task)

    def allocate(self):
        return self.post("/api/allocation/generate/", {"date": DATE, "period": PERIOD})

    def test_a_fresh_distribution_is_ready_to_allocate(self):
        self.assertEqual(self.allocate().status_code, 202)

    def test_refuses_when_a_student_joined_after_distribution(self):
        enrol(self.cls, ["9999999999"])

        response = self.allocate()
        job = run(tasks.generate_allocation_task, DATE, PERIOD)

        self.assertEqual(response.status_code, 409)
        self.assertIn("AC ND I (GNS 101): planned 6, now 7", response.data["detail"])
        self.assertEqual(job.status, "failed")
        self.assertEqual(
            [(s["planned"], s["current"]) for s in job.result_data["stale"]], [(6, 7)]
        )
        self.assertFalse(SeatArrangement.objects.exists())

    def test_regenerating_the_slot_distribution_clears_the_refusal(self):
        enrol(self.cls, ["9999999999"])
        Distribution.objects.filter(date=DATE, period=PERIOD).delete()

        run(tasks.generate_distribution_task, DATE, PERIOD)

        self.assertEqual(self.allocate().status_code, 202)

    def test_allocate_all_refuses_and_seats_nobody_when_any_slot_is_stale(self):
        enrol(self.cls, ["9999999999"])

        response = self.post("/api/allocation/generate-all/")
        job = run(tasks.generate_allocation_all_task)

        self.assertEqual(response.status_code, 409)
        self.assertEqual(job.status, "failed")
        self.assertFalse(SeatArrangement.objects.exists())

    def test_a_row_never_distributed_counts_as_stale(self):
        TimeTable.objects.update(planned_students=None)

        report = self.client.get("/api/readiness/?stage=allocation").data

        self.assertFalse(report["ready"])
        self.assertEqual({s["planned"] for s in report["stale"]}, {None})


class ReadinessEndpointTests(PipelineTestCase):
    def test_needs_a_known_stage(self):
        self.assertEqual(self.client.get("/api/readiness/?stage=nope").status_code, 400)

    def test_needs_date_and_period_together(self):
        response = self.client.get(f"/api/readiness/?stage=allocation&date={DATE}")

        self.assertEqual(response.status_code, 400)

    def test_is_for_super_admins_only(self):
        officer = User.objects.create_user(
            email="do@example.com", password="x", role=User.Role.DATA_OFFICER
        )
        self.client.force_authenticate(officer)

        self.assertEqual(
            self.client.get("/api/readiness/?stage=timetable").status_code, 403
        )


class ClassSizeSyncTests(PipelineTestCase):
    HEADER = "MATRIC NUMBER,FIRSTNAME,LASTNAME,EMAIL,PHONE NUMBER\n"

    def setUp(self):
        super().setUp()
        self.cls = make_class(0, make_department("ac"), name="ND I")
        self.new_home = make_class(0, make_department("bf"), name="ND I")

    def size(self, cls):
        return Class.objects.get(pk=cls.pk).size

    def test_size_follows_upload_delete_and_move(self):
        body = "".join(f"24300000{n},Ada,Obi,a{n}@example.com,080\n" for n in range(3))
        upload_class_students(
            SimpleUploadedFile("s.csv", (self.HEADER + body).encode()), self.cls
        )
        self.assertEqual(self.size(self.cls), 3)

        first, second, _ = Student.objects.order_by("matric_no")
        self.client.delete(f"/api/students/{first.id}/")
        self.assertEqual(self.size(self.cls), 2)

        response = self.client.patch(
            f"/api/students/{second.id}/", {"class_id": self.new_home.id}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.size(self.cls), 1)
        self.assertEqual(self.size(self.new_home), 1)
        second.refresh_from_db()
        self.assertEqual(second.department_id, self.new_home.department_id)

    def test_reupload_into_another_class_updates_both(self):
        [student] = enrol(self.cls, ["2430000001"])
        body = f"{student.matric_no},Ada,Obi,a@example.com,080\n"

        upload_class_students(
            SimpleUploadedFile("s.csv", (self.HEADER + body).encode()), self.new_home
        )

        self.assertEqual(self.size(self.cls), 0)
        self.assertEqual(self.size(self.new_home), 1)

    def test_single_row_saves_outside_the_api_sync_too(self):
        [student] = enrol(self.cls, ["2430000001"])
        self.assertEqual(self.size(self.cls), 1)

        student.delete()

        self.assertEqual(self.size(self.cls), 0)

    def test_a_written_size_is_ignored(self):
        enrol(self.cls, ["2430000001"])

        response = self.client.patch(
            f"/api/classes/{self.cls.id}/", {"size": 99}, format="json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["size"], 1)

    def test_class_csv_size_column_is_optional_and_ignored(self):
        from ems.upload_handlers import upload_classes_for_department

        dept = self.cls.department
        upload_classes_for_department(
            SimpleUploadedFile("c.csv", b"Name,Size\nHND I,40\n"), dept
        )
        upload_classes_for_department(SimpleUploadedFile("c.csv", b"Name\nHND II\n"), dept)

        self.assertEqual(
            dict(Class.objects.filter(department=dept).values_list("name", "size")),
            {"ND I": 0, "HND I": 0, "HND II": 0},
        )


class ActiveSwitchTests(PipelineTestCase):
    def setUp(self):
        super().setUp()
        self.mine = make_class(0, make_department("ac"), name="ND I")
        self.theirs = make_class(0, make_department("bf"), name="ND I")
        self.officer = User.objects.create_user(
            email="ac@example.com", password="x", department=self.mine.department
        )

    def test_an_officer_switches_their_own_class_off(self):
        self.client.force_authenticate(self.officer)

        response = self.client.patch(
            f"/api/classes/{self.mine.id}/", {"is_active": False}, format="json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["is_active"])

    def test_an_officer_cannot_switch_another_department_class(self):
        self.client.force_authenticate(self.officer)

        response = self.client.patch(
            f"/api/classes/{self.theirs.id}/", {"is_active": False}, format="json"
        )

        # The class is outside their department, so it is not even visible.
        self.assertIn(response.status_code, (403, 404))
        self.theirs.refresh_from_db()
        self.assertTrue(self.theirs.is_active)

    def test_dashboard_total_leaves_out_inactive_classes(self):
        enrol(self.mine, ["2430000001", "2430000002"])
        enrol(self.theirs, ["2430000003"])
        self.theirs.is_active = False
        self.theirs.save()

        response = self.client.get("/api/system/dashboard/")

        self.assertEqual(response.data["students_count"], 2)
