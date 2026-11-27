"""Whole database backup and restore (spec 0003, child 0007)."""
import json
import os
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta, timezone as dt_timezone
from io import BytesIO, StringIO
from pathlib import Path
from unittest import mock
from urllib.parse import quote

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import SimpleTestCase, override_settings

from tenancy import backups

SATURDAY = datetime(2026, 10, 10, 1, 0, tzinfo=dt_timezone.utc)
SUNDAY = datetime(2026, 10, 11, 1, 0, tzinfo=dt_timezone.utc)
MANIFEST = {"schemas": ["public", "school_alpha"], "schools": 1}


def utc(day, hour, minute=0):
    return datetime(2026, 10, day, hour, minute, tzinfo=dt_timezone.utc)


class FakeCursor:
    def __init__(self, manifest):
        self.manifest = manifest
        self.sql = ""

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql):
        self.sql = sql

    def fetchone(self):
        if "pg_export_snapshot" in self.sql:
            return ("snap-1",)
        return (self.manifest["schools"],)

    def fetchall(self):
        return [(name,) for name in reversed(self.manifest["schemas"])]


class FakeConnection:
    def __init__(self, manifest=MANIFEST):
        self.manifest = manifest
        self.session = None

    def set_session(self, **session):
        self.session = session

    def cursor(self):
        return FakeCursor(self.manifest)

    def rollback(self):
        pass

    def close(self):
        pass


def fake_tools(dump=b"PGDMP-dump", list_fails=False, calls=None):
    """A subprocess.run stand in: pg_dump writes ``dump``, pg_restore lists it."""

    def run(args, **kwargs):
        if calls is not None:
            calls.append(args)
        if args[0] == "pg_dump":
            path = next(arg.split("=", 1)[1] for arg in args if arg.startswith("--file="))
            Path(path).write_bytes(dump)
        if args[0] == "pg_restore" and list_fails:
            return mock.Mock(returncode=1, stderr="input file does not appear to be a valid archive")
        return mock.Mock(returncode=0, stderr="")

    return run


class LockedObject(Exception):
    pass


class FakeBucket:
    """Just enough of a boto3 S3 client. Like R2 under a bucket lock, it
    refuses overwrites, and it has no delete at all."""

    def __init__(self, keys=(), size_override=None, copy_failures=0):
        self.objects = {key: b"x" for key in keys}
        self.size_override = size_override
        self.copy_failures = copy_failures
        self.copied = []

    def _put(self, key, body):
        if key in self.objects:
            raise LockedObject(key)
        self.objects[key] = body

    def upload_file(self, path, bucket, key, ExtraArgs=None):
        self._put(key, Path(path).read_bytes())

    def put_object(self, Bucket, Key, Body, **extra):
        self._put(Key, Body.encode() if isinstance(Body, str) else Body)

    def head_object(self, Bucket, Key):
        size = len(self.objects[Key]) if self.size_override is None else self.size_override
        return {"ContentLength": size}

    def copy(self, CopySource, Bucket, Key, ExtraArgs=None):
        if self.copy_failures:
            self.copy_failures -= 1
            raise ConnectionError("R2 is down")
        self._put(Key, self.objects[CopySource["Key"]])
        self.copied.append(Key)

    def list_objects_v2(self, Bucket, Prefix):
        return {"Contents": [{"Key": key} for key in self.objects if key.startswith(Prefix)]}

    def get_paginator(self, name):
        bucket = self

        class Paginator:
            def paginate(self, Bucket, Prefix):
                return [bucket.list_objects_v2(Bucket, Prefix)]

        return Paginator()

    def get_object(self, Bucket, Key):
        return {"Body": BytesIO(self.objects[Key])}

    def download_file(self, bucket, key, path):
        Path(path).write_bytes(self.objects[key])


class BackupTestCase(SimpleTestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.heartbeat = os.path.join(folder.name, "ok")
        overrides = override_settings(
            BACKUP_BUCKET="ordo-backups",
            BACKUP_HEARTBEAT_FILE=self.heartbeat,
            BACKUP_HEARTBEAT_URL="https://hc.example/ping/abc",
            BACKUP_DATABASE_URL="postgres://ordo@db/ordo",
            BACKUP_S3_SSE="",
        )
        overrides.enable()
        self.addCleanup(overrides.disable)
        quiet = mock.patch.object(backups.logger, "disabled", True)
        quiet.start()
        self.addCleanup(quiet.stop)
        urlopen = mock.patch.object(backups.urllib.request, "urlopen")
        self.urlopen = urlopen.start()
        self.addCleanup(urlopen.stop)

    def patched(self, bucket, **tools):
        stack = mock.patch.multiple(
            backups,
            _bucket=mock.Mock(return_value=bucket),
            _connect=mock.Mock(return_value=FakeConnection()),
        )
        run = mock.patch.object(backups.subprocess, "run", side_effect=fake_tools(**tools))
        stack.start()
        run.start()
        self.addCleanup(stack.stop)
        self.addCleanup(run.stop)

    def pings(self):
        return [
            (call.args[0].get_method(), call.args[0].full_url, call.args[0].data)
            for call in self.urlopen.call_args_list
        ]


class BackUpTests(BackupTestCase):
    def test_uploads_the_dump_and_its_manifest_then_pings(self):
        bucket = FakeBucket()
        calls = []
        self.patched(bucket, calls=calls)

        key = backups.attempt(SATURDAY)

        self.assertEqual(key, "db/daily/ordo-20261010T010000Z.dump")
        self.assertEqual(bucket.objects[key], b"PGDMP-dump")
        manifest = json.loads(bucket.objects["db/daily/ordo-20261010T010000Z.json"])
        self.assertEqual(manifest["schemas"], ["public", "school_alpha"])
        self.assertEqual(manifest["schools"], 1)
        self.assertEqual(bucket.copied, [])
        self.assertEqual(Path(self.heartbeat).read_text(), SATURDAY.isoformat())
        self.assertEqual(self.pings(), [("GET", "https://hc.example/ping/abc", None)])

        pg_dump, pg_list = calls
        self.assertEqual(pg_dump[0], "pg_dump")
        self.assertIn("--snapshot=snap-1", pg_dump)
        self.assertIn("--no-owner", pg_dump)
        self.assertEqual(pg_list[:2], ["pg_restore", "--list"])

    def test_the_manifest_is_read_in_a_repeatable_read_snapshot(self):
        connection_ = FakeConnection()
        with mock.patch.object(backups, "_connect", return_value=connection_), mock.patch.object(
            backups.subprocess, "run", side_effect=fake_tools()
        ), tempfile.TemporaryDirectory() as folder:
            backups._dump(os.path.join(folder, "x.dump"))
        self.assertEqual(connection_.session["isolation_level"], "REPEATABLE READ")

    def test_a_size_mismatch_fails_the_attempt_and_posts_the_error(self):
        self.patched(FakeBucket(size_override=3))

        with self.assertRaises(backups.BackupError):
            backups.attempt(SATURDAY)

        self.assertFalse(os.path.exists(self.heartbeat))
        [(method, url, body)] = self.pings()
        self.assertEqual((method, url), ("POST", "https://hc.example/ping/abc/fail"))
        self.assertIn(b"expected 10", body)
        self.assertIn(b"Traceback", body)

    def test_an_archive_that_does_not_list_is_never_uploaded(self):
        bucket = FakeBucket()
        self.patched(bucket, list_fails=True)

        with self.assertRaisesMessage(backups.BackupError, "valid archive"):
            backups.attempt(SATURDAY)

        self.assertEqual(bucket.objects, {})
        self.assertFalse(os.path.exists(self.heartbeat))
        self.assertEqual(self.pings()[0][1], "https://hc.example/ping/abc/fail")

    def test_an_empty_dump_is_never_uploaded(self):
        bucket = FakeBucket()
        self.patched(bucket, dump=b"")
        with self.assertRaisesMessage(backups.BackupError, "empty"):
            backups.back_up(SATURDAY)
        self.assertEqual(bucket.objects, {})

    def test_the_fail_body_is_the_last_10_kb(self):
        with mock.patch.object(backups, "back_up", side_effect=RuntimeError("x" * 50_000)):
            with self.assertRaises(RuntimeError):
                backups.attempt(SATURDAY)
        body = self.pings()[0][2]
        self.assertEqual(len(body), 10 * 1024)
        self.assertTrue(body.rstrip().endswith(b"x"))

    def test_a_failing_ping_never_fails_a_backup(self):
        self.urlopen.side_effect = OSError("monitor unreachable")
        self.patched(FakeBucket())
        self.assertEqual(backups.attempt(SATURDAY), "db/daily/ordo-20261010T010000Z.dump")
        self.assertTrue(os.path.exists(self.heartbeat))

    @override_settings(BACKUP_HEARTBEAT_URL="")
    def test_no_pings_without_a_monitor_url(self):
        self.patched(FakeBucket())
        backups.attempt(SATURDAY)
        self.urlopen.assert_not_called()

    @override_settings(BACKUP_BUCKET="")
    def test_needs_a_bucket(self):
        with self.assertRaisesMessage(backups.BackupError, "BACKUP_BUCKET"):
            backups.back_up(SATURDAY)


class WeeklyTests(BackupTestCase):
    def test_the_first_sunday_backup_becomes_the_weekly(self):
        bucket = FakeBucket()
        self.patched(bucket)

        backups.back_up(SUNDAY)
        backups.back_up(SUNDAY + timedelta(hours=5))

        self.assertEqual(
            bucket.copied,
            ["db/weekly/ordo-20261011T010000Z.json", "db/weekly/ordo-20261011T010000Z.dump"],
        )

    def test_a_failing_copy_is_retried_alone(self):
        bucket = FakeBucket(copy_failures=2)
        calls = []
        self.patched(bucket, calls=calls)

        with mock.patch.object(backups.clock, "sleep") as sleep:
            backups.back_up(SUNDAY)

        self.assertEqual([args[0] for args in calls], ["pg_dump", "pg_restore"])
        self.assertEqual(sleep.call_args_list, [mock.call(60), mock.call(60)])
        self.assertIn("db/weekly/ordo-20261011T010000Z.dump", bucket.objects)

    def test_a_retry_never_copies_a_landed_key_twice(self):
        bucket = FakeBucket()
        self.patched(bucket)
        real_copy = bucket.copy
        failed = []

        def flaky(CopySource, Bucket, Key, ExtraArgs=None):
            if Key.endswith(".dump") and not failed:
                failed.append(Key)
                raise ConnectionError("R2 is down")
            return real_copy(CopySource, Bucket, Key, ExtraArgs)

        bucket.copy = flaky
        with mock.patch.object(backups.clock, "sleep"):
            backups.back_up(SUNDAY)
        self.assertEqual(
            bucket.copied,
            ["db/weekly/ordo-20261011T010000Z.json", "db/weekly/ordo-20261011T010000Z.dump"],
        )

    def test_a_copy_that_keeps_failing_fails_the_run(self):
        self.patched(FakeBucket(copy_failures=10))
        with mock.patch.object(backups.clock, "sleep") as sleep:
            with self.assertRaises(ConnectionError):
                backups.back_up(SUNDAY)
        self.assertEqual(sleep.call_count, 3)
        self.assertFalse(os.path.exists(self.heartbeat))

    def test_the_app_never_deletes_a_backup(self):
        source = Path(backups.__file__).read_text()
        self.assertNotIn("delete_object", source)


class Clock:
    def __init__(self, start):
        self.now = start

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.now += timedelta(seconds=seconds)


@override_settings(BACKUP_TIME_UTC="01:00")
class ScheduleTests(SimpleTestCase):
    def run_daemon(self, start, outcomes):
        """Run ``len(outcomes)`` rounds; True succeeds. Returns the attempt times."""
        clock = Clock(start)
        times = []
        results = iter(outcomes)

        def attempt(started):
            times.append(started)
            if not next(results):
                raise backups.BackupError("R2 is down")

        with mock.patch.object(backups, "attempt", side_effect=attempt), mock.patch.object(
            backups.logger, "disabled", True
        ):
            backups.run_forever(now=clock, sleep=clock.sleep, rounds=len(outcomes))
        return times

    def test_a_failing_run_makes_four_attempts_an_hour_apart(self):
        times = self.run_daemon(utc(10, 3), [False] * 6)
        self.assertEqual(
            times,
            [utc(10, 3), utc(10, 4), utc(10, 5), utc(10, 6), utc(11, 1), utc(11, 2)],
        )

    def test_the_scheduled_run_starts_on_time_with_a_fresh_count(self):
        times = self.run_daemon(utc(10, 23, 30), [False] * 7)
        self.assertEqual(
            times,
            [
                utc(10, 23, 30),
                utc(11, 0, 30),
                utc(11, 1),  # the 01:30 retry is dropped
                utc(11, 2),
                utc(11, 3),
                utc(11, 4),
                utc(12, 1),
            ],
        )

    def test_success_waits_for_the_next_scheduled_time(self):
        times = self.run_daemon(utc(10, 3), [True, True])
        self.assertEqual(times, [utc(10, 3), utc(11, 1)])

    def test_next_run_is_strictly_after_now(self):
        self.assertEqual(backups.next_run(utc(11, 0, 30), "01:00"), utc(11, 1))
        self.assertEqual(backups.next_run(utc(11, 1), "01:00"), utc(12, 1))


class BackupCommandTests(BackupTestCase):
    def test_a_one_off_failure_exits_non_zero(self):
        with mock.patch.object(backups, "back_up", side_effect=backups.BackupError("boom")):
            with self.assertRaisesMessage(CommandError, "boom"):
                call_command("backup_database", stdout=StringIO())


class RestoreCommandTests(BackupTestCase):
    def restore(self, *args, **options):
        out = StringIO()
        call_command("restore_database", *args, stdout=out, **options)
        return out.getvalue()

    def test_latest_picks_the_newest_daily_dump(self):
        bucket = FakeBucket(
            [
                "db/daily/ordo-20261009T010000Z.dump",
                "db/daily/ordo-20261011T010000Z.dump",
                "db/daily/ordo-20261011T010000Z.json",
                "db/weekly/ordo-20261012T010000Z.dump",
            ]
        )
        self.assertEqual(backups.latest_key(bucket), "db/daily/ordo-20261011T010000Z.dump")

    def test_needs_a_key_or_latest(self):
        with self.assertRaises(CommandError):
            self.restore(target_url="postgres://x/y")

    def test_restores_with_no_owner_and_no_privileges(self):
        bucket = FakeBucket(["db/daily/ordo-20261011T010000Z.dump"])
        calls = []
        with mock.patch.object(backups, "_bucket", return_value=bucket), mock.patch.object(
            backups, "check_target"
        ) as check, mock.patch.object(
            backups.subprocess, "run", side_effect=fake_tools(calls=calls)
        ):
            self.restore(latest=True, target_url="postgres://x/ordo_restore_drill")

        check.assert_called_once_with("postgres://x/ordo_restore_drill", into_live=False)
        [args] = calls
        self.assertEqual(args[0], "pg_restore")
        for flag in ("--no-owner", "--no-privileges", "--exit-on-error"):
            self.assertIn(flag, args)

    def test_verify_fails_on_a_manifest_mismatch(self):
        key = "db/daily/ordo-20261011T010000Z.dump"
        bucket = FakeBucket([key])
        bucket.objects[key.replace(".dump", ".json")] = json.dumps(MANIFEST).encode()
        restored = FakeConnection({"schemas": ["public"], "schools": 1})
        with mock.patch.object(backups, "_bucket", return_value=bucket), mock.patch.object(
            backups, "check_target"
        ), mock.patch.object(backups, "restore"), mock.patch.object(
            backups, "_connect", return_value=restored
        ):
            with self.assertRaisesMessage(CommandError, "doesn't match"):
                self.restore(key, target_url="postgres://x/y", verify=True)

            restored.manifest = MANIFEST
            self.assertIn("matches the manifest", self.restore(key, target_url="postgres://x/y", verify=True))


def database_url(name):
    db = connection.settings_dict
    return (
        f"postgresql://{quote(db['USER'] or '')}:{quote(db['PASSWORD'] or '')}"
        f"@{db['HOST'] or 'localhost'}:{db['PORT'] or 5432}/{name}"
    )


@unittest.skipUnless(shutil.which("pg_dump") and shutil.which("pg_restore"), "needs pg_dump")
class PostgresRoundTripTests(BackupTestCase):
    """The real tools against the test database and a scratch one beside it."""

    databases = {"default"}

    def setUp(self):
        super().setUp()
        self.live = database_url(connection.settings_dict["NAME"])
        self.scratch_name = f"ordo_backup_test_{os.getpid()}"
        self.scratch = database_url(self.scratch_name)
        admin = backups._connect(self.live)
        admin.autocommit = True
        with admin.cursor() as cursor:
            cursor.execute(f'DROP DATABASE IF EXISTS "{self.scratch_name}"')
            cursor.execute(f'CREATE DATABASE "{self.scratch_name}"')
        admin.close()
        self.addCleanup(self.drop_scratch)

    def drop_scratch(self):
        admin = backups._connect(self.live)
        admin.autocommit = True
        with admin.cursor() as cursor:
            cursor.execute(f'DROP DATABASE IF EXISTS "{self.scratch_name}" WITH (FORCE)')
        admin.close()

    def test_dump_restore_and_verify(self):
        bucket = FakeBucket()
        with override_settings(BACKUP_DATABASE_URL=self.live), mock.patch.object(
            backups, "_bucket", return_value=bucket
        ):
            key = backups.back_up(SATURDAY)

            with self.assertRaisesMessage(backups.BackupError, "live database"):
                backups.check_target(self.live)
            with self.assertRaisesMessage(backups.BackupError, "isn't empty"):
                backups.check_target(self.live, into_live=True)

            backups.check_target(self.scratch)
            backups.restore(key, self.scratch)
            expected, actual = backups.verify(key, self.scratch)

            with self.assertRaisesMessage(backups.BackupError, "isn't empty"):
                backups.check_target(self.scratch)

        self.assertIn("public", expected["schemas"])
        self.assertEqual(expected, actual)
