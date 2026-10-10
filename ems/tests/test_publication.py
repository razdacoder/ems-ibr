"""Timetable publication is separate from generation: a generated timetable
is a draft that department officers cannot see until a super admin
publishes it, and publishing notifies each department."""
from rest_framework.test import APIClient

from ems import tasks
from ems.models import Notification, SystemSettings, TimeTable, User

from .helpers import listed_class, make_course, make_department, make_hall, schedule
from .test_student_lists import PipelineTestCase, allow_generation, run


def officer(email, department, **fields):
    return User.objects.create_user(
        email=email, password="x", department=department, **fields
    )


class PublicationTestCase(PipelineTestCase):
    def setUp(self):
        super().setUp()
        self.ac = make_department("ac")
        self.bf = make_department("bf")
        ac_class = listed_class(3, self.ac, name="ND I")
        bf_class = listed_class(3, self.bf, name="ND I")
        schedule(ac_class, make_course("ACC 111"), "2026-08-17", "AM")
        schedule(ac_class, make_course("ACC 112"), "2026-08-19", "AM")
        schedule(bf_class, make_course("BFN 111"), "2026-08-18", "PM")
        self.ada = officer("ada@example.com", self.ac)
        self.bola = officer("bola@example.com", self.bf)
        self.officer_client = APIClient()
        self.officer_client.force_authenticate(self.ada)

    def publish(self, **body):
        return self.post("/api/timetable/publish/", body)


class DraftVisibilityTests(PublicationTestCase):
    def test_an_officer_sees_no_draft(self):
        data = self.officer_client.get("/api/timetable/").data
        dates = self.officer_client.get("/api/timetable/dates/").data
        export = self.officer_client.get("/api/exports/timetable/")

        self.assertEqual(data["results"], [])
        self.assertTrue(data["generated"])
        self.assertFalse(data["published"])
        self.assertEqual(dates, {"dates": []})
        self.assertEqual(export.status_code, 403)

    def test_the_committee_sees_the_draft(self):
        data = self.client.get("/api/timetable/").data

        self.assertEqual(len(data["results"]), 3)
        self.assertFalse(data["published"])

    def test_once_published_an_officer_sees_their_own_department(self):
        self.publish()

        data = self.officer_client.get("/api/timetable/").data
        export = self.officer_client.get("/api/exports/timetable/")

        self.assertEqual(
            sorted(r["course"]["code"] for r in data["results"]), ["ACC 111", "ACC 112"]
        )
        self.assertEqual(export.status_code, 200)


class PublishTests(PublicationTestCase):
    def test_publishing_records_who_and_when(self):
        response = self.publish()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["published"])
        self.assertEqual(response.data["published_by"], "sa@example.com")
        self.assertFalse(response.data["already_published"])
        self.assertIsNotNone(SystemSettings.objects.get().timetable_published_at)

    def test_each_department_is_told_about_its_own_papers(self):
        response = self.publish()

        self.assertEqual(response.data["notified"], {"departments": 2, "users": 2})
        self.assertEqual(
            dict(Notification.objects.values_list("recipient__email", "body")),
            {
                "ada@example.com": "Department ac has 2 papers, 17 Aug to 19 Aug 2026.",
                "bola@example.com": "Department bf has 1 paper, Tue 18 Aug 2026.",
            },
        )
        self.assertEqual(
            set(Notification.objects.values_list("kind", "link")),
            {("timetable_published", "/timetable")},
        )

    def test_only_the_chosen_departments_are_told(self):
        response = self.publish(department_ids=[self.bf.id])

        self.assertEqual(response.data["notified"], {"departments": 1, "users": 1})
        self.assertEqual(
            list(Notification.objects.values_list("recipient__email", flat=True)),
            ["bola@example.com"],
        )

    def test_individual_users_can_be_told_too(self):
        member = User.objects.create_user(
            email="ecm@example.com", password="x", role=User.Role.EXAM_COMMITTEE,
            is_staff=True,
        )

        response = self.publish(department_ids=[], user_ids=[member.id, self.ada.id])

        self.assertEqual(response.data["notified"], {"departments": 0, "users": 2})
        self.assertEqual(
            sorted(Notification.objects.values_list("recipient__email", flat=True)),
            ["ada@example.com", "ecm@example.com"],
        )

    def test_a_department_user_named_twice_gets_one_message(self):
        self.publish(user_ids=[self.ada.id])

        self.assertEqual(Notification.objects.filter(recipient=self.ada).count(), 1)

    def test_publishing_without_notifying(self):
        response = self.publish(notify=False)

        self.assertTrue(response.data["published"])
        self.assertFalse(Notification.objects.exists())

    def test_the_publisher_and_inactive_users_are_not_told(self):
        self.admin.department = self.ac
        self.admin.save()
        officer("gone@example.com", self.ac, is_active=False)

        self.publish()

        self.assertEqual(
            sorted(Notification.objects.values_list("recipient__email", flat=True)),
            ["ada@example.com", "bola@example.com"],
        )

    def test_publishing_again_keeps_the_first_time_and_resends(self):
        first = self.publish().data["published_at"]

        again = self.publish(department_ids=[self.ac.id])

        self.assertTrue(again.data["already_published"])
        self.assertEqual(again.data["published_at"], first)
        self.assertEqual(Notification.objects.filter(recipient=self.ada).count(), 2)

    def test_nothing_to_publish(self):
        TimeTable.objects.all().delete()

        self.assertEqual(self.publish().status_code, 400)

    def test_rejects_ids_that_are_not_a_list(self):
        self.assertEqual(self.publish(department_ids="ac").status_code, 400)

    def test_only_super_admins_publish(self):
        response = self.officer_client.post("/api/timetable/publish/", {}, format="json")

        self.assertEqual(response.status_code, 403)
        self.assertFalse(SystemSettings.objects.filter(
            timetable_published_at__isnull=False
        ).exists())

    def test_status_lists_departments_for_the_picker(self):
        data = self.client.get("/api/timetable/publication/").data

        self.assertEqual(
            [(d["slug"], d["papers"], d["users"]) for d in data["departments"]],
            [("ac", 2, 1), ("bf", 1, 1)],
        )

    def test_officers_see_status_without_the_picker(self):
        data = self.officer_client.get("/api/timetable/publication/").data

        self.assertEqual(data["published"], False)
        self.assertNotIn("departments", data)


class UnpublishTests(PublicationTestCase):
    def test_withdrawing_hides_it_and_tells_those_who_were_told(self):
        self.publish(department_ids=[self.ac.id])

        response = self.post("/api/timetable/unpublish/")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["published"])
        self.assertEqual(response.data["notified"], {"users": 1})
        self.assertEqual(
            list(
                Notification.objects.filter(kind="timetable_withdrawn")
                .values_list("recipient__email", flat=True)
            ),
            ["ada@example.com"],
        )
        self.assertEqual(self.officer_client.get("/api/timetable/").data["results"], [])

    def test_withdrawing_a_draft_is_refused(self):
        self.assertEqual(self.post("/api/timetable/unpublish/").status_code, 409)


class BackToDraftTests(PublicationTestCase):
    def test_a_new_timetable_is_a_draft(self):
        self.publish()
        make_hall("Hall A", 10, 10)
        allow_generation()

        job = run(tasks.generate_timetable_task, "2026-08-17", "2026-08-29")

        self.assertEqual(job.status, "success", job.result_data)
        self.assertIsNone(SystemSettings.objects.get().timetable_published_at)

    def test_resetting_the_timetable_unpublishes_it(self):
        self.publish()

        self.post("/api/system/reset/", {"scope": "timetable"})

        self.assertIsNone(SystemSettings.objects.get().timetable_published_at)

    def test_resetting_allocation_keeps_it_published(self):
        self.publish()

        self.post("/api/system/reset/", {"scope": "allocation"})

        self.assertIsNotNone(SystemSettings.objects.get().timetable_published_at)
