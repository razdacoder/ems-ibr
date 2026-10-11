"""Cloudinary storage for uploaded images (the institution logo).

The app's own disk is not persistent on Railway, so a logo saved there
disappears on the next deploy and the attendance sheets lose it. When
``CLOUDINARY_URL`` is set, :func:`select_logo_storage` returns
:class:`CloudinaryImageStorage` instead and the file lives on Cloudinary.
Without it (local development, tests) the logo stays on the local disk.

A stored name is ``<public_id>.<format>``, for example
``school_unilag/branding/logo_3f9a1c2e.png``: the public id locates the
image on Cloudinary, and the format picks the delivery URL's extension.

Both backends keep each school's files apart (spec 0003, child 0001): the
public id starts with the school's schema name, and the local disk keeps
them under ``MEDIA_ROOT/<schema_name>/``. The schema is read on every call,
never at import, because one process serves every school.
"""

import os
import urllib.request
import uuid

import cloudinary
import cloudinary.uploader
import cloudinary.utils
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage, Storage, default_storage
from django.db import connection
from django.utils.deconstruct import deconstructible

# Downloading the logo for a Word export must not hang a request.
DOWNLOAD_TIMEOUT_SECONDS = 15


def _configure():
    url = getattr(settings, "CLOUDINARY_URL", "")
    if url and os.environ.get("CLOUDINARY_URL") != url:
        os.environ["CLOUDINARY_URL"] = url
        cloudinary.reset_config()


@deconstructible
class CloudinaryImageStorage(Storage):
    """Store, serve and fetch images on Cloudinary."""

    def _split(self, name):
        public_id, ext = os.path.splitext(name)
        return public_id, ext.lstrip(".") or None

    def get_available_name(self, name, max_length=None):
        # A random suffix instead of asking Cloudinary whether the name is
        # taken: one upload, no Admin API call (those are rate limited).
        root, ext = os.path.splitext(name)
        return f"{root}_{uuid.uuid4().hex[:8]}{ext}"

    def _save(self, name, content):
        _configure()
        public_id, _ext = self._split(name)
        prefix = f"{connection.schema_name}/"
        if not public_id.startswith(prefix):
            public_id = prefix + public_id
        if hasattr(content, "seek"):
            content.seek(0)
        result = cloudinary.uploader.upload(
            content,
            public_id=public_id,
            resource_type="image",
            overwrite=True,
        )
        return f"{result['public_id']}.{result['format']}"

    def url(self, name):
        _configure()
        public_id, ext = self._split(name)
        return cloudinary.utils.cloudinary_url(
            public_id, format=ext, resource_type="image", secure=True
        )[0]

    def _open(self, name, mode="rb"):
        with urllib.request.urlopen(
            self.url(name), timeout=DOWNLOAD_TIMEOUT_SECONDS
        ) as response:
            return ContentFile(response.read(), name=name)

    def exists(self, name):
        try:
            request = urllib.request.Request(self.url(name), method="HEAD")
            with urllib.request.urlopen(request, timeout=DOWNLOAD_TIMEOUT_SECONDS):
                return True
        except Exception:
            return False

    def delete(self, name):
        _configure()
        public_id, _ext = self._split(name)
        cloudinary.uploader.destroy(public_id, resource_type="image", invalidate=True)

    def size(self, name):
        return self._open(name).size


@deconstructible
class SchoolFileSystemStorage(FileSystemStorage):
    """Local disk under ``MEDIA_ROOT/<schema_name>/`` of the current school.

    Names stay relative (``branding/logo.png``), so a school host serves them
    at ``/media/branding/logo.png`` from its own folder (``core.urls``).
    """

    @property
    def location(self):
        return os.path.abspath(
            os.path.join(self.base_location, connection.schema_name)
        )


def select_logo_storage():
    """Cloudinary when ``CLOUDINARY_URL`` is configured, else local disk."""
    if getattr(settings, "CLOUDINARY_URL", ""):
        return CloudinaryImageStorage()
    return default_storage
