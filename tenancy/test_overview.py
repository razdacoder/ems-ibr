"""The console dashboard's overview, ``GET /api/platform/overview/``."""
from datetime import timedelta

from django.utils import timezone

from tenancy.models import PlatformAdmin, School, SupportSession, UsageSnapshot
from tenancy.test_school_lifecycle import SchoolConsoleTestCase

URL = "/api/platform/overview/"


class OverviewTests(SchoolConsoleTestCase):
    def overview(self, client=None):
        response = (client or self.owner).get(URL)
        self.assertEqual(response.status_code, 200, response.data)
        return response.data

    def test_support_admins_can_read_it_and_strangers_cannot(self):
        support = self.sign_in(self.make_admin("support@ordo.app", role=PlatformAdmin.Role.SUPPORT))
        self.assertEqual(support.get(URL).status_code, 200)
        self.assertEqual(self.console.get(URL).status_code, 401)

    def test_counts_schools_by_status_without_the_public_row(self):
        self.create()
        data = self.overview()
        by_status = data["schools"]["by_status"]
        # The test school plus the one just created, both active.
        self.assertEqual(by_status["active"], 2)
        self.assertEqual(data["schools"]["total"], 2)
        self.assertEqual(data["schools"]["new_last_30_days"], 2)

    def test_usage_adds_up_each_schools_latest_snapshot(self):
        self.create()
        other = School.objects.get(slug="unilag")
        today = timezone.now().date()
        UsageSnapshot.objects.create(
            school=self.tenant, taken_on=today - timedelta(days=1),
            students=100, staff_users=5, jobs_last_24h=1,
        )
        UsageSnapshot.objects.create(
            school=self.tenant, taken_on=today, students=120, staff_users=6, jobs_last_24h=2,
        )
        UsageSnapshot.objects.create(
            school=other, taken_on=today, students=30, staff_users=2, jobs_last_24h=0,
        )

        data = self.overview()

        self.assertEqual(data["usage"]["students"], 150)
        self.assertEqual(data["usage"]["staff_users"], 8)
        self.assertEqual(data["usage"]["jobs_last_24h"], 2)
        self.assertEqual(data["usage"]["as_of"], today)
        self.assertEqual(
            [(row["date"], row["students"]) for row in data["trend"]],
            [(today - timedelta(days=1), 100), (today, 150)],
        )

    def test_flags_schools_that_need_attention(self):
        today = timezone.now().date()
        School.objects.filter(pk=self.tenant.pk).update(renews_on=today + timedelta(days=5))
        self.create()
        School.objects.filter(slug="unilag").update(
            status=School.Status.SUSPENDED, suspended_at=timezone.now()
        )

        kinds = {(item["school"]["slug"], item["kind"]) for item in self.overview()["attention"]}

        self.assertEqual(kinds, {("test", "renewal_due"), ("unilag", "suspended")})

    def test_lists_only_running_support_sessions(self):
        now = timezone.now()
        common = {"admin": self.owner_admin, "school": self.tenant, "reason": "Help"}
        running = SupportSession.objects.create(
            **common, ticket_hash="a", ticket_expires_at=now,
            started_at=now, expires_at=now + timedelta(minutes=30),
        )
        SupportSession.objects.create(
            **common, ticket_hash="b", ticket_expires_at=now,
            started_at=now, expires_at=now + timedelta(minutes=30), ended_at=now,
        )

        support = self.overview()["support"]

        self.assertEqual([s["id"] for s in support], [running.id])
