"""Whole database backup and restore (spec 0004, assumed)."""
import os
import tempfile
from datetime import datetime, timezone as dt_timezone
from io import StringIO
from unittest import mock

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings

from tenancy import backups

SATURDAY = datetime(2026, 10, 10, 1, 0, tzinfo=dt_timezone.utc)
SUNDAY = datetime(2026, 10, 11, 1, 0, tzinfo=dt_timezone.utc)


def fake_pg_dump(contents=b"PGDMP-dump"):
    """A subprocess.run stand in that writes ``contents`` to --file."""

    def run(args, **kwargs):
        path = next(arg.split("=", 1)[1] for arg in args if arg.startswith("--file="))
        with open(path, "wb") as dump:
            dump.write(contents)
        return mock.Mock(returncode=0, stderr="")

    return run


class FakeBucket:
    """Just enough of a boto3 S3 client, keyed by object name."""

    def __init__(self, keys=(), size_override=None):
        self.objects = {key: 1 for key in keys}
        self.size_override = size_override
        self.deleted = []
        self.copied = []

    def upload_file(self, path, bucket, key, ExtraArgs=None):
        self.objects[key] = os.path.getsize(path)

    def head_object(self, Bucket, Key):
        size = self.objects[Key] if self.size_override is None else self.size_override
        return {"ContentLength": size}

    def copy_object(self, Bucket, Key, CopySource, **extra):
        self.objects[Key] = self.objects[CopySource["Key"]]
        self.copied.append(Key)

    def delete_object(self, Bucket, Key):
        del self.objects[Key]
        self.deleted.append(Key)

    def get_paginator(self, name):
        bucket = self

        class Paginator:
            def paginate(self, Bucket, Prefix):
                contents = [{"Key": key} for key in bucket.objects if key.startswith(Prefix)]
                return [{"Contents": contents}]

        return Paginator()


class BackupTestCase(SimpleTestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.heartbeat = os.path.join(folder.name, "ok")
        overrides = override_settings(
            BACKUP_BUCKET="ordo-backups",
            BACKUP_KEEP_DAILY=2,
            BACKUP_KEEP_WEEKLY=1,
            BACKUP_HEARTBEAT_FILE=self.heartbeat,
        )
        overrides.enable()
        self.addCleanup(overrides.disable)

    def run_backup(self, bucket, now, dump=b"PGDMP-dump"):
        with mock.patch.object(backups, "_bucket", return_value=bucket), mock.patch.object(
            backups.subprocess, "run", side_effect=fake_pg_dump(dump)
        ):
            return backups.back_up(now)


class BackUpTests(BackupTestCase):
    def test_uploads_a_daily_and_writes_the_heartbeat(self):
        bucket = FakeBucket()
        key = self.run_backup(bucket, SATURDAY)

        self.assertEqual(key, "db/daily/ordo-20261010T010000Z.dump")
        self.assertEqual(bucket.objects[key], len(b"PGDMP-dump"))
        self.assertEqual(bucket.copied, [])
        with open(self.heartbeat) as heartbeat:
            self.assertEqual(heartbeat.read(), SATURDAY.isoformat())

    def test_sunday_also_keeps_a_weekly(self):
        bucket = FakeBucket()
        self.run_backup(bucket, SUNDAY)
        self.assertEqual(bucket.copied, ["db/weekly/ordo-20261011T010000Z.dump"])

    def test_prunes_to_the_newest_dailies_and_weeklies(self):
        bucket = FakeBucket(
            [
                "db/daily/ordo-20261008T010000Z.dump",
                "db/daily/ordo-20261009T010000Z.dump",
                "db/weekly/ordo-20261004T010000Z.dump",
            ]
        )
        self.run_backup(bucket, SUNDAY)

        self.assertCountEqual(
            bucket.deleted,
            ["db/daily/ordo-20261008T010000Z.dump", "db/weekly/ordo-20261004T010000Z.dump"],
        )
        self.assertCountEqual(
            bucket.objects,
            [
                "db/daily/ordo-20261009T010000Z.dump",
                "db/daily/ordo-20261011T010000Z.dump",
                "db/weekly/ordo-20261011T010000Z.dump",
            ],
        )

    def test_an_unverified_upload_prunes_nothing(self):
        old = ["db/daily/ordo-20261001T010000Z.dump", "db/daily/ordo-20261002T010000Z.dump"]
        bucket = FakeBucket(old, size_override=3)

        with self.assertRaises(backups.BackupError):
            self.run_backup(bucket, SATURDAY)

        self.assertEqual(bucket.deleted, [])
        self.assertFalse(os.path.exists(self.heartbeat))

    def test_an_empty_dump_is_never_uploaded(self):
        bucket = FakeBucket()
        with self.assertRaises(backups.BackupError):
            self.run_backup(bucket, SATURDAY, dump=b"")
        self.assertEqual(bucket.objects, {})

    def test_a_failed_pg_dump_raises(self):
        failed = mock.Mock(returncode=1, stderr="connection refused")
        with mock.patch.object(backups, "_bucket", return_value=FakeBucket()), mock.patch.object(
            backups.subprocess, "run", return_value=failed
        ):
            with self.assertRaisesMessage(backups.BackupError, "connection refused"):
                backups.back_up(SATURDAY)

    @override_settings(BACKUP_BUCKET="")
    def test_needs_a_bucket(self):
        with self.assertRaisesMessage(backups.BackupError, "BACKUP_BUCKET"):
            backups.back_up(SATURDAY)


class NextRunTests(SimpleTestCase):
    def test_later_today(self):
        now = datetime(2026, 10, 11, 0, 30, tzinfo=dt_timezone.utc)
        self.assertEqual(
            backups.next_run(now, "01:00"), datetime(2026, 10, 11, 1, 0, tzinfo=dt_timezone.utc)
        )

    def test_at_or_after_the_time_is_tomorrow(self):
        now = datetime(2026, 10, 11, 1, 0, tzinfo=dt_timezone.utc)
        self.assertEqual(
            backups.next_run(now, "01:00"), datetime(2026, 10, 12, 1, 0, tzinfo=dt_timezone.utc)
        )


class RestoreCommandTests(BackupTestCase):
    def live_url(self):
        db = settings.DATABASES["default"]
        return f"postgres://u:p@{db['HOST'] or 'localhost'}:{db['PORT'] or 5432}/{db['NAME']}"

    def test_refuses_the_live_database(self):
        with mock.patch("tenancy.management.commands.restore_database.restore") as restore:
            with self.assertRaisesMessage(CommandError, "live database"):
                call_command(
                    "restore_database", "db/daily/x.dump", target_url=self.live_url()
                )
        restore.assert_not_called()

    def test_into_live_overrides_the_guard(self):
        with mock.patch("tenancy.management.commands.restore_database.restore") as restore:
            call_command(
                "restore_database",
                "db/daily/x.dump",
                target_url=self.live_url(),
                into_live=True,
                stdout=StringIO(),
            )
        restore.assert_called_once_with("db/daily/x.dump", self.live_url())

    def test_restores_into_a_scratch_database(self):
        target = "postgres://u:p@localhost:5432/ordo_restore_drill"
        calls = []

        def run(args, **kwargs):
            calls.append(args)
            return mock.Mock(returncode=0, stderr="")

        bucket = mock.Mock()
        with mock.patch.object(backups, "_bucket", return_value=bucket), mock.patch.object(
            backups.subprocess, "run", side_effect=run
        ):
            call_command("restore_database", "db/daily/x.dump", target_url=target, stdout=StringIO())

        bucket.download_file.assert_called_once()
        self.assertEqual(calls[0][0], "pg_restore")
        self.assertIn(f"--dbname={target}", calls[0])
        self.assertIn("--exit-on-error", calls[0])
