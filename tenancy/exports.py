"""A deleted school's final export, and removing what a purge leaves behind.

The export is a ``pg_dump`` of the school's schema in a private S3
compatible bucket (``EXPORT_BUCKET``, Cloudflare R2). It is kept only until
the school is purged or restored (spec 0003, child 0004).
"""
import logging
import os
import shutil
import subprocess
import tempfile

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

# Written instead of a key when the school never went live: nothing to keep.
NEVER_ACTIVE = "never_active"


class ExportError(Exception):
    pass


def _bucket():
    import boto3

    if not settings.EXPORT_BUCKET:
        raise ExportError("EXPORT_BUCKET is not set.")
    return boto3.client(
        "s3",
        endpoint_url=settings.EXPORT_S3_ENDPOINT or None,
        aws_access_key_id=settings.EXPORT_S3_ACCESS_KEY_ID or None,
        aws_secret_access_key=settings.EXPORT_S3_SECRET_ACCESS_KEY or None,
        region_name=settings.EXPORT_S3_REGION or None,
    )


def key_for(schema_name):
    return f"exports/{schema_name}-{timezone.now():%Y%m%d}.dump"


def dump_schema(schema_name, path):
    """``pg_dump`` one schema to ``path`` over the direct connection."""
    result = subprocess.run(
        [
            "pg_dump",
            f"--schema={schema_name}",
            "--format=custom",
            "--no-owner",
            f"--file={path}",
            f"--dbname={settings.EXPORT_DATABASE_URL}",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise ExportError(f"pg_dump exited {result.returncode}: {result.stderr.strip()[:1000]}")


def export_schema(schema_name):
    """Dump the schema and upload it. Returns the bucket key."""
    key = key_for(schema_name)
    with tempfile.TemporaryDirectory() as folder:
        path = os.path.join(folder, "school.dump")
        dump_schema(schema_name, path)
        extra = {"ServerSideEncryption": settings.EXPORT_S3_SSE} if settings.EXPORT_S3_SSE else {}
        _bucket().upload_file(path, settings.EXPORT_BUCKET, key, ExtraArgs=extra)
    return key


def is_verified(ref):
    """Whether a purge may go ahead: the sentinel, or a non empty object."""
    if ref == NEVER_ACTIVE:
        return True
    if not ref:
        return False
    from botocore.exceptions import ClientError

    try:
        head = _bucket().head_object(Bucket=settings.EXPORT_BUCKET, Key=ref)
    except ClientError:
        return False
    return head.get("ContentLength", 0) > 0


def delete_export(ref):
    """Remove the export, if there is one. Missing already is fine."""
    if not ref or ref == NEVER_ACTIVE:
        return
    _bucket().delete_object(Bucket=settings.EXPORT_BUCKET, Key=ref)


def delete_media(schema_name):
    """Remove the school's uploads under ``<schema_name>/`` on every backend."""
    folder = os.path.join(settings.MEDIA_ROOT, schema_name)
    if os.path.isdir(folder):
        shutil.rmtree(folder)
    if getattr(settings, "CLOUDINARY_URL", ""):
        import cloudinary.api

        from ems.cloudinary_storage import _configure

        _configure()
        cloudinary.api.delete_resources_by_prefix(f"{schema_name}/", resource_type="image")
