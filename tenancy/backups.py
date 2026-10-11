"""Nightly backup of the whole database, and restoring one (spec 0004, assumed).

One ``pg_dump`` of every schema (the public one holds the only record of
slugs, plans and domains) goes to the private bucket ``BACKUP_BUCKET``. On
Sundays (UTC) the same object is also kept as a weekly. Older backups are
pruned only after the new one is verified in the bucket.
"""
import logging
import os
import subprocess
import tempfile
from datetime import datetime, time, timedelta, timezone as dt_timezone

from django.conf import settings

logger = logging.getLogger(__name__)

DAILY = "db/daily/"
WEEKLY = "db/weekly/"


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


def _run(args):
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        raise BackupError(f"{args[0]} exited {result.returncode}: {result.stderr.strip()[:1000]}")


def name_for(now):
    return f"ordo-{now:%Y%m%dT%H%M%SZ}.dump"


def next_run(now, at):
    """The next ``HH:MM`` (UTC) strictly after ``now``."""
    hour, minute = (int(part) for part in at.split(":"))
    candidate = datetime.combine(now.date(), time(hour, minute), tzinfo=dt_timezone.utc)
    if candidate <= now:
        candidate += timedelta(days=1)
    return candidate


def _keys(client, prefix):
    keys = []
    for page in client.get_paginator("list_objects_v2").paginate(
        Bucket=settings.BACKUP_BUCKET, Prefix=prefix
    ):
        keys.extend(item["Key"] for item in page.get("Contents", []))
    # Names carry a sortable UTC timestamp, so newest sorts last.
    return sorted(keys)


def prune(client, prefix, keep):
    """Delete all but the newest ``keep`` objects under ``prefix``."""
    stale = _keys(client, prefix)[:-keep] if keep > 0 else []
    for key in stale:
        client.delete_object(Bucket=settings.BACKUP_BUCKET, Key=key)
    return stale


def back_up(now=None):
    """Dump, upload, verify, then prune. Returns the daily key."""
    now = now or datetime.now(dt_timezone.utc)
    client = _bucket()
    name = name_for(now)
    daily = DAILY + name
    extra = {"ServerSideEncryption": settings.BACKUP_S3_SSE} if settings.BACKUP_S3_SSE else {}

    with tempfile.TemporaryDirectory() as folder:
        path = os.path.join(folder, name)
        _run(
            [
                "pg_dump",
                "--format=custom",
                "--no-owner",
                f"--file={path}",
                f"--dbname={settings.BACKUP_DATABASE_URL}",
            ]
        )
        size = os.path.getsize(path)
        if size == 0:
            raise BackupError("pg_dump wrote an empty file.")
        client.upload_file(path, settings.BACKUP_BUCKET, daily, ExtraArgs=extra)

    # Never prune on the strength of an upload that didn't land whole.
    head = client.head_object(Bucket=settings.BACKUP_BUCKET, Key=daily)
    if head.get("ContentLength") != size:
        raise BackupError(
            f"{daily} is {head.get('ContentLength')} bytes in the bucket, expected {size}."
        )

    if now.weekday() == 6:
        client.copy_object(
            Bucket=settings.BACKUP_BUCKET,
            Key=WEEKLY + name,
            CopySource={"Bucket": settings.BACKUP_BUCKET, "Key": daily},
            **extra,
        )

    prune(client, DAILY, settings.BACKUP_KEEP_DAILY)
    prune(client, WEEKLY, settings.BACKUP_KEEP_WEEKLY)

    with open(settings.BACKUP_HEARTBEAT_FILE, "w") as heartbeat:
        heartbeat.write(now.isoformat())
    logger.info("Backed up the database to %s (%s bytes).", daily, size)
    return daily


def is_live(target_url):
    """Whether ``target_url`` names the same database as ``DATABASE_URL``."""
    from urllib.parse import urlparse

    def ident(url):
        parsed = urlparse(url)
        return (parsed.hostname, parsed.port or 5432, parsed.path.lstrip("/"))

    live = settings.DATABASES["default"]
    live_ident = (live.get("HOST"), int(live.get("PORT") or 5432), live.get("NAME"))
    return ident(target_url) == live_ident


def restore(key, target_url):
    """Download ``key`` and ``pg_restore`` it into the empty ``target_url``."""
    client = _bucket()
    with tempfile.TemporaryDirectory() as folder:
        path = os.path.join(folder, "restore.dump")
        client.download_file(settings.BACKUP_BUCKET, key, path)
        _run(
            [
                "pg_restore",
                "--no-owner",
                "--exit-on-error",
                f"--dbname={target_url}",
                path,
            ]
        )
