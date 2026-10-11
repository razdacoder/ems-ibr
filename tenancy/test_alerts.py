"""Platform alerts, the renewal digest and backup run records."""
from datetime import datetime, timedelta, timezone as dt_timezone
from unittest import mock

from django.core import mail
from django.test import override_settings
from django.utils import timezone

from tenancy import alerts, backups
from tenancy.models import BackupRun, PlatformAdmin, School
from tenancy.tasks import alert_renewals, fail_stale_provisioning, send_email
from tenancy.test_school_lifecycle import SchoolConsoleTestCase, run_inline

SATURDAY = datetime(2026, 10, 10, 1, 0, tzinfo=dt_timezone.utc)


class AlertTestCase(SchoolConsoleTestCase):
    def alerts_sent(self):
        return [m for m in mail.outbox if m.subject.startswith("[Ordo]")]


class AlertTests(AlertTestCase):
    def test_a_school_whose_setup_stalls_alerts_the_owners(self):
        School.objects.filter(pk=self.tenant.pk).update(
            status=School.Status.PROVISIONING,
            provisioning_started_at=timezone.now() - timedelta(hours=1),
        )
        mail.outbox.clear()

        with run_inline(send_email), self.captureOnCommitCallbacks(execute=True):
            fail_stale_provisioning()

        [alert] = self.alerts_sent()
        self.assertIn("Setting up Test School failed", alert.subject)
        self.assertEqual(alert.to, ["owner@ordo.app"])
        self.assertIn("console.localhost/console/schools/", alert.body)

    @override_settings(PLATFORM_ALERT_EMAILS=["ops@ordo.app"])
    def test_alert_emails_override_the_owners(self):
        with run_inline(send_email), self.captureOnCommitCallbacks(execute=True):
            alerts.send("Something", ["line"])
        [alert] = self.alerts_sent()
        self.assertEqual(alert.to, ["ops@ordo.app"])

    def test_an_alert_that_cannot_be_sent_never_raises(self):
        with mock.patch.object(alerts, "recipients", side_effect=RuntimeError("db down")), \
                mock.patch.object(alerts.logger, "disabled", True):
            alerts.send("Something", ["line"])


class RenewalTests(AlertTestCase):
    def renews_in(self, days):
        School.objects.filter(pk=self.tenant.pk).update(
            renews_on=timezone.now().date() + timedelta(days=days)
        )
        mail.outbox.clear()
        with run_inline(send_email), self.captureOnCommitCallbacks(execute=True):
            alert_renewals()
        return self.alerts_sent()

    def test_reminds_two_weeks_one_week_and_one_day_out(self):
        for days in (14, 7, 1, 0):
            with self.subTest(days=days):
                [alert] = self.renews_in(days)
                self.assertIn("Test School", alert.body)

    def test_stays_quiet_on_other_days(self):
        for days in (13, 3, -1):
            with self.subTest(days=days):
                self.assertEqual(self.renews_in(days), [])

    def test_a_lapsed_plan_comes_up_weekly(self):
        [alert] = self.renews_in(-7)
        self.assertIn("lapsed 7 days ago", alert.body)


class BackupRunTests(AlertTestCase):
    def test_a_successful_attempt_is_recorded_with_its_size(self):
        def back_up(started, report):
            report["size"] = 1234
            return "db/daily/x.dump"

        with mock.patch.object(backups, "back_up", side_effect=back_up), \
                mock.patch.object(backups, "_ping"):
            backups.attempt(SATURDAY)

        run = BackupRun.objects.get()
        self.assertTrue(run.ok)
        self.assertEqual((run.key, run.size_bytes), ("db/daily/x.dump", 1234))

    def test_a_failed_attempt_is_recorded_with_its_error(self):
        with mock.patch.object(backups, "back_up", side_effect=backups.BackupError("R2 is down")), \
                mock.patch.object(backups, "_ping"), mock.patch.object(backups.logger, "disabled", True):
            with self.assertRaises(backups.BackupError):
                backups.attempt(SATURDAY)

        run = BackupRun.objects.get()
        self.assertFalse(run.ok)
        self.assertIn("R2 is down", run.error)

    def test_the_team_hears_once_retries_are_used_up(self):
        times = iter([SATURDAY + timedelta(hours=h) for h in range(20)])
        with mock.patch.object(backups, "attempt", side_effect=backups.BackupError("R2 is down")), \
                mock.patch.object(backups.logger, "disabled", True):
            backups.run_forever(now=lambda: next(times), sleep=lambda s: None, rounds=4)

        # Three retries stay quiet; the fourth failure gives up until tomorrow.
        [alert] = self.alerts_sent()
        self.assertIn("nightly database backup failed", alert.subject)

    def test_the_owner_list_skips_admins_who_never_joined(self):
        pending = PlatformAdmin(email="new@ordo.app", name="New", role=PlatformAdmin.Role.OWNER)
        pending.set_unusable_password()
        pending.save()
        self.assertEqual(alerts.recipients(), ["owner@ordo.app"])
