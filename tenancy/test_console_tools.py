"""Backup health, usage history, staff search, the schools CSV and announcements."""
import csv
import io
from datetime import timedelta
from unittest import mock

from django.utils import timezone
from django_tenants.utils import schema_context

from ems.models import User
from tenancy.models import Announcement, BackupRun, PlatformAdmin, School, StaffDirectoryEntry, UsageSnapshot
from tenancy.tasks import index_staff
from tenancy.testcases import SchoolClient
from tenancy.test_school_lifecycle import SchoolConsoleTestCase


class BackupHealthTests(SchoolConsoleTestCase):
    def backup(self):
        return self.owner.get("/api/platform/overview/").data["backup"]

    def test_no_backup_yet_is_stale(self):
        data = self.backup()
        self.assertTrue(data["stale"])
        self.assertIsNone(data["last_success"])

    def test_a_recent_success_is_healthy_even_after_a_later_failure(self):
        now = timezone.now()
        BackupRun.objects.create(
            started_at=now - timedelta(hours=3), finished_at=now, ok=True, key="k", size_bytes=10
        )
        BackupRun.objects.create(
            started_at=now - timedelta(hours=1), finished_at=now, ok=False, error="boom"
        )
        data = self.backup()
        self.assertFalse(data["stale"])
        self.assertEqual(data["last_success"]["size_bytes"], 10)
        self.assertFalse(data["last_run"]["ok"])
        self.assertEqual([r["ok"] for r in data["recent"]], [True, False])

    def test_a_success_older_than_26_hours_is_stale(self):
        old = timezone.now() - timedelta(hours=27)
        BackupRun.objects.create(started_at=old, finished_at=old, ok=True)
        self.assertTrue(self.backup()["stale"])


class UsageHistoryTests(SchoolConsoleTestCase):
    def test_returns_snapshots_oldest_first_with_the_limits(self):
        today = timezone.now().date()
        for days in (2, 1, 500):
            UsageSnapshot.objects.create(
                school=self.tenant, taken_on=today - timedelta(days=days),
                students=days, staff_users=1, jobs_last_24h=0,
            )
        data = self.owner.get(f"/api/platform/schools/{self.tenant.pk}/usage/?days=30").data
        self.assertEqual([s["students"] for s in data["snapshots"]], [2, 1])
        self.assertIn("max_students", data["limits"])


class StaffSearchTests(SchoolConsoleTestCase):
    def setUp(self):
        super().setUp()
        with schema_context(self.tenant.schema_name):
            User.objects.create_user(
                email="ada@test.localhost", password="x-123456789", first_name="Ada", last_name="Obi"
            )
            User.objects.create_user(
                email="support+1@ordo.invalid", password="x",
                support_expires_at=timezone.now() + timedelta(hours=1),
            )
        index_staff()

    def test_finds_which_school_an_email_belongs_to(self):
        data = self.owner.get("/api/platform/staff/?q=ada@").data
        [hit] = data["results"]
        self.assertEqual(hit["school"]["slug"], "test")
        self.assertEqual(hit["name"], "Ada Obi")
        self.assertIsNotNone(data["indexed_at"])

    def test_support_shadow_users_are_never_indexed(self):
        self.assertFalse(StaffDirectoryEntry.objects.filter(email__startswith="support+").exists())

    def test_a_short_query_is_refused(self):
        self.assertEqual(self.owner.get("/api/platform/staff/?q=ad").status_code, 400)

    def test_reindexing_replaces_the_schools_rows(self):
        index_staff()
        self.assertEqual(StaffDirectoryEntry.objects.filter(email="ada@test.localhost").count(), 1)

    def test_a_purged_school_drops_out_of_the_search(self):
        School.objects.filter(pk=self.tenant.pk).update(status=School.Status.PURGED)
        with mock.patch("tenancy.tasks.logger"):
            index_staff()
        self.assertFalse(StaffDirectoryEntry.objects.exists())

    def test_reindex_now_queues_the_task(self):
        with mock.patch("tenancy.tasks.index_staff.delay") as delay:
            response = self.owner.post("/api/platform/staff/reindex/")
        self.assertEqual(response.status_code, 202)
        delay.assert_called_once()


class SchoolExportTests(SchoolConsoleTestCase):
    def test_exports_every_school_as_csv_with_its_latest_usage(self):
        School.objects.filter(pk=self.tenant.pk).update(contact_name="=HYPERLINK(1)")
        UsageSnapshot.objects.create(
            school=self.tenant, taken_on=timezone.now().date(),
            students=40, staff_users=3, jobs_last_24h=1,
        )
        response = self.owner.get("/api/platform/schools/export/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment", response["Content-Disposition"])
        rows = list(csv.DictReader(io.StringIO(response.content.decode())))
        [row] = [r for r in rows if r["slug"] == "test"]
        self.assertEqual(row["students"], "40")
        # Spreadsheet formulas are defused.
        self.assertEqual(row["contact_name"], "'=HYPERLINK(1)")


class AnnouncementTests(SchoolConsoleTestCase):
    def post(self, client=None, **data):
        return (client or self.owner).post(
            "/api/platform/announcements/", {"message": "Maintenance tonight", **data}, format="json"
        )

    def school_announcements(self):
        from rest_framework.authtoken.models import Token

        with schema_context(self.tenant.schema_name):
            user = User.objects.get_or_create(email="u@test.localhost")[0]
            token = Token.objects.get_or_create(user=user)[0].key
        return SchoolClient(HTTP_AUTHORIZATION=f"Token {token}").get("/api/school/").data["announcements"]

    def test_an_owner_announces_and_every_school_sees_it_until_withdrawn(self):
        created = self.post(level="warning")
        self.assertEqual(created.status_code, 201, created.data)
        self.assertEqual(created.data["state"], "showing")

        [shown] = self.school_announcements()
        self.assertEqual((shown["message"], shown["level"]), ("Maintenance tonight", "warning"))

        self.owner.post(f"/api/platform/announcements/{created.data['id']}/withdraw/")
        self.assertEqual(self.school_announcements(), [])

    def test_a_scheduled_or_ended_announcement_is_not_shown(self):
        now = timezone.now()
        self.post(starts_at=(now + timedelta(hours=1)).isoformat())
        Announcement.objects.create(
            message="old", starts_at=now - timedelta(days=2), ends_at=now - timedelta(days=1)
        )
        self.assertEqual(self.school_announcements(), [])

    def test_the_end_must_follow_the_start(self):
        now = timezone.now()
        response = self.post(starts_at=now.isoformat(), ends_at=(now - timedelta(hours=1)).isoformat())
        self.assertEqual(response.status_code, 400)

    def test_support_admins_can_read_but_not_announce(self):
        support = self.sign_in(self.make_admin("support@ordo.app", role=PlatformAdmin.Role.SUPPORT))
        self.assertEqual(self.post(client=support).status_code, 403)
        self.assertEqual(support.get("/api/platform/announcements/").status_code, 200)
