"""Nightly backup of the whole database, and restoring one (spec 0003, child 0007).

One ``pg_dump`` of every schema (the public one holds the only record of
slugs, plans and domains) goes to the private bucket ``BACKUP_BUCKET``, with a
manifest read in the same snapshot. The first verified backup of each UTC
Sunday is also copied to ``db/weekly/``. The app never deletes a backup: R2
lifecycle rules expire them and a bucket lock protects them (deploy/README.md).
"""
import json
import logging
import os
import subprocess
import tempfile
import time as clock
import traceback
import urllib.request
from datetime import datetime, time, timedelta, timezone as dt_timezone

from django.conf import settings

logger = logging.getLogger(__name__)

DAILY = "db/daily/"
WEEKLY = "db/weekly/"
RETRIES = 3
RETRY_DELAY = timedelta(hours=1)
COPY_RETRIES = 3
COPY_RETRY_SECONDS = 60
PING_TIMEOUT = 10
FAIL_BODY_BYTES = 10 * 1024


class BackupError(Exception):
    pass


def _bucket():
    import boto3

    if not settings.BACKUP_BUCKET:
        raise BackupError("BACKUP_BUCKET is not set.")
    return boto3.client(
        "s3",
        endpoint_url=settings.BACKUP_S3_ENDPOINT or None,
        aws_access_key_id=settings.BACKUP_S3_ACCESS_KEY_ID or None,
        aws_secret_access_key=settings.BACKUP_S3_SECRET_ACCESS_KEY or None,
        region_name=settings.BACKUP_S3_REGION or None,
    )


def _extra():
    return {"ServerSideEncryption": settings.BACKUP_S3_SSE} if settings.BACKUP_S3_SSE else {}


def _connect(url):
    import psycopg2

    return psycopg2.connect(url)


def _run(args):
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        raise BackupError(f"{args[0]} exited {result.returncode}: {result.stderr.strip()[:1000]}")
    return result


def name_for(started):
    return f"ordo-{started:%Y%m%dT%H%M%SZ}"


def next_run(now, at):
    """The next ``HH:MM`` (UTC) strictly after ``now``."""
    hour, minute = (int(part) for part in at.split(":"))
    candidate = datetime.combine(now.date(), time(hour, minute), tzinfo=dt_timezone.utc)
    if candidate <= now:
        candidate += timedelta(days=1)
    return candidate


def read_manifest(cursor):
    """The schemas a restore must bring back, and how many schools they hold."""
    cursor.execute(
        "SELECT nspname FROM pg_namespace WHERE nspname = 'public' OR nspname LIKE 'school\\_%'"
    )
    schemas = sorted(row[0] for row in cursor.fetchall())
    cursor.execute("SELECT count(*) FROM public.tenancy_school")
    return {"schemas": schemas, "schools": cursor.fetchone()[0]}


def _dump(path):
    """``pg_dump`` into ``path`` and return the manifest read in the same snapshot."""
    connection = _connect(settings.BACKUP_DATABASE_URL)
    try:
        connection.set_session(isolation_level="REPEATABLE READ", readonly=True)
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_export_snapshot()")
            snapshot = cursor.fetchone()[0]
            manifest = read_manifest(cursor)
            # The snapshot only lives while this transaction stays open.
            _run(
                [
                    "pg_dump",
                    "--format=custom",
                    "--no-owner",
                    f"--snapshot={snapshot}",
                    f"--file={path}",
                    f"--dbname={settings.BACKUP_DATABASE_URL}",
                ]
            )
        connection.rollback()
    finally:
        connection.close()
    return manifest


def _copy_weekly(client, started, daily):
    """Copy the first verified backup of a UTC Sunday to ``db/weekly/``.

    Returns the weekly dump key, or None when it isn't due. Only the copy is
    retried, never the dump. The manifest goes first, so a weekly exists once
    its ``.dump`` does.
    """
    if started.weekday() != 6:
        return None
    listed = client.list_objects_v2(
        Bucket=settings.BACKUP_BUCKET, Prefix=f"{WEEKLY}ordo-{started:%Y%m%d}"
    )
    if any(item["Key"].endswith(".dump") for item in listed.get("Contents", [])):
        return None

    weekly = WEEKLY + daily[len(DAILY):]
    pending = [".json", ".dump"]
    for attempt in range(COPY_RETRIES + 1):
        try:
            # The bucket lock refuses overwrites, so never copy a key twice.
            while pending:
                client.copy(
                    {"Bucket": settings.BACKUP_BUCKET, "Key": daily + pending[0]},
                    settings.BACKUP_BUCKET,
                    weekly + pending[0],
                    ExtraArgs=_extra(),
                )
                pending.pop(0)
            return weekly + ".dump"
        except Exception:
            if attempt == COPY_RETRIES:
                raise
            logger.warning("Weekly copy of %s failed, retrying.", daily, exc_info=True)
            clock.sleep(COPY_RETRY_SECONDS)


def back_up(started=None):
    """Dump, list, upload, verify, copy the weekly, write the heartbeat.

    Returns the daily dump key. Raises on any failure, before the heartbeat.
    """
    started = started or datetime.now(dt_timezone.utc)
    client = _bucket()
    daily = DAILY + name_for(started)
    dump_key, manifest_key = daily + ".dump", daily + ".json"

    with tempfile.TemporaryDirectory() as folder:
        path = os.path.join(folder, "backup.dump")
        manifest = _dump(path)
        size = os.path.getsize(path)
        if size == 0:
            raise BackupError("pg_dump wrote an empty file.")
        _run(["pg_restore", "--list", path])

        client.upload_file(path, settings.BACKUP_BUCKET, dump_key, ExtraArgs=_extra())
        client.put_object(
            Bucket=settings.BACKUP_BUCKET,
            Key=manifest_key,
            Body=json.dumps({**manifest, "dump": dump_key, "started": started.isoformat()}),
            ContentType="application/json",
            **_extra(),
        )

    head = client.head_object(Bucket=settings.BACKUP_BUCKET, Key=dump_key)
    if head.get("ContentLength") != size:
        raise BackupError(
            f"{dump_key} is {head.get('ContentLength')} bytes in the bucket, expected {size}."
        )

    weekly = _copy_weekly(client, started, daily)

    with open(settings.BACKUP_HEARTBEAT_FILE, "w") as heartbeat:
        heartbeat.write(started.isoformat())
    logger.info(
        "Backed up the database to %s (%s bytes)%s.",
        dump_key,
        size,
        f", weekly {weekly}" if weekly else "",
    )
    return dump_key


def _ping(path="", body=None):
    """Tell the outside monitor. Never raises: a ping never fails a backup."""
    url = settings.BACKUP_HEARTBEAT_URL
    if not url:
        return
    request = urllib.request.Request(
        url.rstrip("/") + path, data=body, method="POST" if body is not None else "GET"
    )
    try:
        urllib.request.urlopen(request, timeout=PING_TIMEOUT).close()
    except Exception:
        logger.warning("Backup monitor ping to %s failed.", path or "success", exc_info=True)


def attempt(started=None):
    """One backup attempt: ping success, or log it, post ``/fail`` and re-raise."""
    try:
        key = back_up(started)
    except Exception:
        logger.exception("Database backup failed.")
        _ping("/fail", traceback.format_exc().encode()[-FAIL_BODY_BYTES:])
        raise
    _ping()
    return key


def next_attempt(now, at, failed, retries_used):
    """When to try next, and whether that try is a retry of the current run.

    The earlier of the next retry (while retries are left) and the next
    scheduled time. A scheduled run always starts with a fresh retry count.
    """
    scheduled = next_run(now, at)
    if failed and retries_used < RETRIES and now + RETRY_DELAY < scheduled:
        return now + RETRY_DELAY, True
    return scheduled, False


def run_forever(now=None, sleep=clock.sleep, rounds=None):
    """Back up now, then on schedule with retries. ``rounds`` bounds it in tests."""
    now = now or (lambda: datetime.now(dt_timezone.utc))
    retries_used = 0
    done = 0
    while rounds is None or done < rounds:
        done += 1
        try:
            attempt(now())
            failed = False
        except Exception:
            failed = True
        current = now()
        wake, is_retry = next_attempt(current, settings.BACKUP_TIME_UTC, failed, retries_used)
        retries_used = retries_used + 1 if is_retry else 0
        logger.info(
            "Next backup %s at %s UTC.",
            f"retry ({retries_used} of {RETRIES})" if is_retry else "run",
            f"{wake:%Y-%m-%d %H:%M}",
        )
        sleep(max((wake - current).total_seconds(), 0))


def latest_key(client):
    """The newest ``db/daily/*.dump`` key. Names carry a sortable UTC time."""
    keys = []
    for page in client.get_paginator("list_objects_v2").paginate(
        Bucket=settings.BACKUP_BUCKET, Prefix=DAILY
    ):
        keys.extend(item["Key"] for item in page.get("Contents", []) if item["Key"].endswith(".dump"))
    if not keys:
        raise BackupError(f"No backups under {DAILY} in {settings.BACKUP_BUCKET}.")
    return max(keys)


def _identity(cursor):
    cursor.execute("SELECT system_identifier FROM pg_control_system()")
    system = cursor.fetchone()[0]
    cursor.execute("SELECT current_database()")
    return system, cursor.fetchone()[0]


def check_target(target_url, into_live=False):
    """Refuse the live database (unless ``into_live``) and any non empty target."""
    from django.db import connection as live

    with live.cursor() as cursor:
        live_identity = _identity(cursor)

    target = _connect(target_url)
    try:
        with target.cursor() as cursor:
            if _identity(cursor) == live_identity and not into_live:
                raise BackupError(
                    "The target is the live database. Restore into a scratch database, "
                    "or pass --into-live if you really mean it."
                )
            cursor.execute(
                "SELECT nspname FROM pg_namespace WHERE nspname NOT IN ('public', "
                "'information_schema') AND nspname NOT LIKE 'pg\\_%' ORDER BY nspname"
            )
            schemas = [row[0] for row in cursor.fetchall()]
            cursor.execute(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"
            )
            tables = [row[0] for row in cursor.fetchall()]
    finally:
        target.close()
    if schemas or tables:
        found = ", ".join([f"schema {name}" for name in schemas] + [f"table {t}" for t in tables[:5]])
        raise BackupError(f"The target isn't empty ({found}). Restore only into an empty database.")


def restore(key, target_url):
    """Download ``key`` and ``pg_restore`` it into ``target_url``."""
    client = _bucket()
    with tempfile.TemporaryDirectory() as folder:
        path = os.path.join(folder, "restore.dump")
        client.download_file(settings.BACKUP_BUCKET, key, path)
        _run(
            [
                "pg_restore",
                "--no-owner",
                "--no-privileges",
                "--exit-on-error",
                f"--dbname={target_url}",
                path,
            ]
        )


def verify(key, target_url):
    """Compare the restored ``target_url`` with the manifest beside ``key``.

    Returns ``(expected, actual)``; they match when the restore is whole.
    """
    client = _bucket()
    body = client.get_object(Bucket=settings.BACKUP_BUCKET, Key=key.removesuffix(".dump") + ".json")
    saved = json.loads(body["Body"].read())
    expected = {"schemas": saved["schemas"], "schools": saved["schools"]}
    target = _connect(target_url)
    try:
        with target.cursor() as cursor:
            actual = read_manifest(cursor)
    finally:
        target.close()
    return expected, actual
