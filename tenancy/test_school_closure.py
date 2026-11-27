"""Suspending, deleting, restoring and purging schools (spec 0003, child 0004)."""
import os
import tempfile
from datetime import timedelta
from unittest import mock

from botocore.exceptions import ClientError
from django.db import connection
from django.test import override_settings
from django.utils import timezone
from django_tenants.utils import schema_context

from ems.models import BackgroundJob, User
from tenancy import exports
from tenancy.models import Domain, PlatformAdmin, PlatformAuditLog, School
from tenancy.school_views import PURGE_GRACE_DAYS
from tenancy.tasks import EXPORT_WAIT_SECONDS, export_school, purge_schools
from tenancy.test_school_lifecycle import SchoolConsoleTestCase, run_inline

KEY = "exports/school_test-20261011.dump"


def actions(school):
    return list(
        PlatformAuditLog.objects.filter(school=school)
        .order_by("id")
        .values_list("action", flat=True)
    )


class ClosureTestCase(SchoolConsoleTestCase):
    def setUp(self):
        super().setUp()
        self.school = self.tenant
        # Signing in to the console left the connection on the public schema.
        with schema_context(self.school.schema_name):
            self.user = User.objects.create_user(
                email="officer@test.localhost", password="x-123456789"
            )
        self.client.force_authenticate(self.user)

    def url(self, action, school=None):
        return f"/api/platform/schools/{(school or self.school).pk}/{action}/"

    def suspend(self, client=None, reason="Unpaid invoice", school=None):
        return (client or self.owner).post(
            self.url("suspend", school), {"reason": reason}, format="json"
        )

    def delete(self, school=None, confirm=None, client=None):
        school = school or self.school
        with mock.patch.object(export_school, "delay") as queued, \
                self.captureOnCommitCallbacks(execute=True):
            response = (client or self.owner).post(
                self.url("delete", school),
                {"confirm_slug": school.slug if confirm is None else confirm},
                format="json",
            )
        self.queued = queued
        return response

    def refresh(self):
        self.school.refresh_from_db()
        return self.school


class SuspendTests(ClosureTestCase):
    def test_suspending_blocks_school_users_but_not_status_or_branding(self):
        # covers: AC-24
        support = self.sign_in(self.make_admin("support@ordo.app", PlatformAdmin.Role.SUPPORT))
        response = self.suspend(support)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["status"], "suspended")
        self.assertEqual(response.data["suspended_reason"], "Unpaid invoice")

        blocked = self.client.get("/api/auth/me/")
        self.assertEqual(blocked.status_code, 403)
        self.assertEqual(
            blocked.json(),
            {"detail": "This school's access is suspended. Contact Ordo.", "code": "school_suspended"},
        )
        self.assertEqual(self.client.post("/api/auth/login/", {}).status_code, 403)
        status = self.client.get("/api/school/status/")
        self.assertEqual(status.status_code, 200)
        self.assertEqual(status.json(), {"name": "Test School", "status": "suspended"})
        self.assertEqual(self.client.get("/api/system/branding/").status_code, 200)
        self.assertIn("school_suspended", actions(self.school))

    def test_reactivating_restores_access(self):
        # covers: AC-24
        self.suspend()
        response = self.owner.post(self.url("reactivate"))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(self.refresh().status, School.Status.ACTIVE)
        self.assertEqual(self.school.suspended_reason, "")
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 200)

    def test_a_reason_is_required_and_only_an_active_school_suspends(self):
        # covers: AC-24
        response = self.suspend(reason="  ")
        self.assertEqual(response.status_code, 400)
        self.assertIn("reason", response.data["errors"])
        self.suspend()
        again = self.suspend()
        self.assertEqual(again.status_code, 409)
        self.assertEqual(again.data["detail"], "Cannot suspend a school that is suspended.")
        self.owner.post(self.url("reactivate"))
        self.assertEqual(self.owner.post(self.url("reactivate")).status_code, 409)


class NotReadyTests(ClosureTestCase):
    def test_a_school_being_set_up_answers_503_except_status(self):
        # covers: AC-24
        school = School.objects.create(
            schema_name="school_soon", slug="soon", name="Soon", plan=self.tenant.plan,
            first_admin_name="X", first_admin_email="x@soon.test",
        )
        Domain.objects.create(domain="soon.localhost", tenant=school, is_primary=True)
        # Django logs every 5xx.
        with self.assertLogs("django.request", "ERROR"):
            response = self.client.get("/api/auth/me/", HTTP_HOST="soon.localhost")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "school_not_ready")
        status = self.client.get("/api/school/status/", HTTP_HOST="soon.localhost")
        self.assertEqual(status.json(), {"name": "Soon", "status": "provisioning"})


class DeleteTests(ClosureTestCase):
    def test_deleting_blocks_users_and_queues_the_export(self):
        # covers: AC-25
        response = self.delete()
        self.assertEqual(response.status_code, 200, response.data)
        school = self.refresh()
        self.assertEqual(school.status, School.Status.PENDING_DELETION)
        self.assertEqual(
            school.purge_after, school.deletion_requested_at + timedelta(days=PURGE_GRACE_DAYS)
        )
        self.assertEqual(school.final_export_ref, "")
        self.queued.assert_called_once_with(school.pk)
        self.assertEqual(self.client.get("/api/auth/me/").json()["code"], "school_suspended")
        self.assertIn("school_deletion_requested", actions(school))

    def test_the_slug_must_be_typed_and_only_an_owner_deletes(self):
        # covers: AC-25, AC-16
        response = self.delete(confirm="tset")
        self.assertEqual(response.status_code, 400)
        self.assertIn("confirm_slug", response.data["errors"])
        support = self.sign_in(self.make_admin("support@ordo.app", PlatformAdmin.Role.SUPPORT))
        self.assertEqual(self.delete(client=support).status_code, 403)
        self.assertEqual(self.refresh().status, School.Status.ACTIVE)

    def test_a_school_already_pending_deletion_cannot_be_deleted_again(self):
        self.delete()
        self.assertEqual(self.delete().status_code, 409)

    def test_a_school_that_was_never_active_needs_no_export(self):
        # covers: AC-25
        School.objects.filter(pk=self.school.pk).update(
            status=School.Status.FAILED, was_ever_active=False
        )
        self.delete()
        self.assertEqual(self.refresh().final_export_ref, exports.NEVER_ACTIVE)
        self.queued.assert_not_called()


class ExportTests(ClosureTestCase):
    def setUp(self):
        super().setUp()
        self.delete()

    def export(self):
        with schema_context("public"):
            export_school.apply(args=(self.school.pk,))

    @mock.patch("tenancy.exports.export_schema", return_value=KEY)
    def test_the_export_key_is_recorded(self, export_schema):
        # covers: AC-25
        self.export()
        export_schema.assert_called_once_with("school_test")
        self.assertEqual(self.refresh().final_export_ref, KEY)
        self.assertIn("school_exported", actions(self.school))

    @mock.patch("tenancy.exports.export_schema", return_value=KEY)
    def test_the_export_waits_while_a_job_is_running(self, export_schema):
        # covers: AC-25
        with schema_context(self.school.schema_name):
            job = BackgroundJob.objects.create(
                job_id="busy", job_type="timetable", status="running", created_by=self.user
            )
        with mock.patch.object(export_school, "apply_async") as later:
            self.export()
        later.assert_called_once_with(args=(self.school.pk,), countdown=EXPORT_WAIT_SECONDS)
        export_schema.assert_not_called()

        with schema_context(self.school.schema_name):
            BackgroundJob.objects.filter(pk=job.pk).update(status="completed")
        self.export()
        self.assertEqual(self.refresh().final_export_ref, KEY)

    @mock.patch("tenancy.exports.export_schema", side_effect=exports.ExportError("disk full"))
    def test_a_failing_export_is_retried_three_times_then_audited(self, export_schema):
        # covers: AC-25
        with self.assertLogs("tenancy.tasks", "ERROR"):
            self.export()
        self.assertEqual(export_schema.call_count, 4)
        self.assertEqual(self.refresh().final_export_ref, "")
        self.assertIn("export_failed", actions(self.school))

    @mock.patch("tenancy.exports.delete_export")
    @mock.patch("tenancy.exports.export_schema", return_value=KEY)
    def test_an_export_finishing_after_a_restore_is_thrown_away(self, export_schema, delete):
        def restore_meanwhile(schema_name):
            School.objects.filter(pk=self.school.pk).update(status=School.Status.ACTIVE)
            return KEY

        export_schema.side_effect = restore_meanwhile
        self.export()
        delete.assert_called_once_with(KEY)
        self.assertEqual(self.refresh().final_export_ref, "")


class RestoreTests(ClosureTestCase):
    @mock.patch("tenancy.exports.delete_export")
    def test_restoring_before_the_purge_reopens_the_school(self, delete):
        # covers: AC-25
        self.delete()
        School.objects.filter(pk=self.school.pk).update(final_export_ref=KEY)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.owner.post(self.url("restore"))
        self.assertEqual(response.status_code, 200, response.data)
        school = self.refresh()
        self.assertEqual(school.status, School.Status.ACTIVE)
        self.assertIsNone(school.purge_after)
        self.assertEqual(school.final_export_ref, "")
        delete.assert_called_once_with(KEY)
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 200)

    def test_restore_refuses_after_the_grace_period(self):
        # covers: AC-25
        self.delete()
        School.objects.filter(pk=self.school.pk).update(purge_after=timezone.now())
        self.assertEqual(self.owner.post(self.url("restore")).status_code, 409)
        self.assertEqual(self.refresh().status, School.Status.PENDING_DELETION)

    def test_restore_only_works_while_pending_deletion(self):
        self.assertEqual(self.owner.post(self.url("restore")).status_code, 409)

    def test_a_never_active_school_goes_back_to_failed_for_retry(self):
        School.objects.filter(pk=self.school.pk).update(
            status=School.Status.FAILED, was_ever_active=False
        )
        self.delete()
        self.owner.post(self.url("restore"))
        self.assertEqual(self.refresh().status, School.Status.FAILED)


class PurgeTests(SchoolConsoleTestCase):
    def setUp(self):
        super().setUp()
        self.create()
        self.school = School.objects.get(slug="unilag")

    def delete_and_expire(self, ref):
        with mock.patch.object(export_school, "delay"), \
                self.captureOnCommitCallbacks(execute=True):
            self.owner.post(
                f"/api/platform/schools/{self.school.pk}/delete/",
                {"confirm_slug": "unilag"}, format="json",
            )
        # 31 days on.
        School.objects.filter(pk=self.school.pk).update(
            final_export_ref=ref, purge_after=timezone.now() - timedelta(days=1)
        )
        # Fire the deferred FK checks the provisioning left in this
        # transaction, or Postgres refuses to drop the tables.
        with connection.cursor() as cursor:
            cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")

    def schema_exists(self):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM information_schema.schemata WHERE schema_name = %s",
                [self.school.schema_name],
            )
            return cursor.fetchone() is not None

    def purge(self):
        with schema_context("public"):
            purge_schools.apply()
        self.school.refresh_from_db()

    @mock.patch("tenancy.exports.delete_media")
    @mock.patch("tenancy.exports.delete_export")
    @mock.patch("tenancy.exports.is_verified", return_value=True)
    def test_a_verified_school_is_purged_and_its_slug_stays_taken(self, verified, delete, media):
        # covers: AC-25, AC-7
        self.delete_and_expire(KEY)
        self.purge()
        verified.assert_called_once_with(KEY)
        self.assertEqual(self.school.status, School.Status.PURGED)
        self.assertIsNotNone(self.school.purged_at)
        self.assertFalse(self.schema_exists())
        self.assertFalse(Domain.objects.filter(tenant=self.school).exists())
        media.assert_called_once_with("school_unilag")
        delete.assert_called_once_with(KEY)
        self.assertIn("school_purged", actions(self.school))

        connection.set_tenant(self.tenant)
        gone = self.client.get("/api/school/status/", HTTP_HOST="unilag.localhost")
        self.assertEqual(gone.status_code, 404)
        self.assertEqual(self.create().status_code, 400)

    def test_without_a_verified_backup_nothing_is_dropped(self):
        # covers: AC-25
        for ref, exists in (("", None), (KEY, False)):
            with self.subTest(ref=ref):
                if not ref:
                    self.delete_and_expire(ref)
                else:
                    School.objects.filter(pk=self.school.pk).update(final_export_ref=ref)
                with mock.patch("tenancy.exports._bucket") as bucket, \
                        self.assertLogs("tenancy.tasks", "ERROR") as logs:
                    bucket.return_value.head_object.side_effect = ClientError(
                        {"Error": {"Code": "404"}}, "HeadObject"
                    )
                    self.purge()
                self.assertIn("no verified export", logs.output[0])
                self.assertEqual(self.school.status, School.Status.PENDING_DELETION)
                self.assertTrue(self.schema_exists())

    def test_a_school_inside_its_grace_period_is_left_alone(self):
        self.delete_and_expire(exports.NEVER_ACTIVE)
        School.objects.filter(pk=self.school.pk).update(
            purge_after=timezone.now() + timedelta(days=1)
        )
        self.purge()
        self.assertEqual(self.school.status, School.Status.PENDING_DELETION)

    @mock.patch("tenancy.exports.delete_media")
    def test_a_never_active_school_is_purged_on_the_sentinel(self, media):
        # covers: AC-25
        School.objects.filter(pk=self.school.pk).update(
            status=School.Status.FAILED, was_ever_active=False
        )
        self.delete_and_expire(exports.NEVER_ACTIVE)
        self.purge()
        self.assertEqual(self.school.status, School.Status.PURGED)
        self.assertFalse(self.schema_exists())

    @mock.patch("tenancy.exports.delete_media")
    def test_a_big_schema_drops_its_tables_in_batches(self, media):
        self.delete_and_expire(exports.NEVER_ACTIVE)
        with mock.patch("tenancy.tasks.PURGE_DROP_BATCH", 5):
            self.purge()
        self.assertFalse(self.schema_exists())


class BucketTests(SchoolConsoleTestCase):
    def head(self, **result):
        bucket = mock.patch("tenancy.exports._bucket").start()
        self.addCleanup(mock.patch.stopall)
        if "error" in result:
            bucket.return_value.head_object.side_effect = result["error"]
        else:
            bucket.return_value.head_object.return_value = result
        return bucket

    def test_only_a_non_empty_object_or_the_sentinel_is_verified(self):
        # covers: AC-25
        self.assertTrue(exports.is_verified(exports.NEVER_ACTIVE))
        self.assertFalse(exports.is_verified(""))
        self.head(ContentLength=0)
        self.assertFalse(exports.is_verified(KEY))
        self.head(ContentLength=2048)
        self.assertTrue(exports.is_verified(KEY))
        self.head(error=ClientError({"Error": {"Code": "404"}}, "HeadObject"))
        self.assertFalse(exports.is_verified(KEY))

    @override_settings(EXPORT_BUCKET="ordo-exports", EXPORT_S3_SSE="AES256")
    def test_the_dump_is_uploaded_encrypted_under_the_schema_key(self):
        bucket = mock.patch("tenancy.exports._bucket").start()
        self.addCleanup(mock.patch.stopall)
        with mock.patch("tenancy.exports.dump_schema") as dump:
            key = exports.export_schema("school_unilag")
        self.assertRegex(key, r"^exports/school_unilag-\d{8}\.dump$")
        dump.assert_called_once()
        _path, bucket_name, uploaded_key = bucket.return_value.upload_file.call_args.args
        self.assertEqual((bucket_name, uploaded_key), ("ordo-exports", key))
        self.assertEqual(
            bucket.return_value.upload_file.call_args.kwargs,
            {"ExtraArgs": {"ServerSideEncryption": "AES256"}},
        )

    def test_media_under_the_schema_prefix_is_removed(self):
        with tempfile.TemporaryDirectory() as root:
            for schema in ("school_gone", "school_kept"):
                os.makedirs(os.path.join(root, schema, "branding"))
            with override_settings(MEDIA_ROOT=root, CLOUDINARY_URL=""):
                exports.delete_media("school_gone")
            self.assertEqual(os.listdir(root), ["school_kept"])
