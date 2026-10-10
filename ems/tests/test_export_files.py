"""Exports stream from a temp file; uploaded media must outlive the container."""
import io
import tempfile
from unittest import mock

from asgiref.sync import async_to_sync
from django.core.files.base import ContentFile
from django.core.files.storage import InMemoryStorage, default_storage
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase, override_settings

from ems import export_files
from ems.checks import check_media_storage
from ems.export_files import ZIP, SpooledFileResponse, spool
from ems.models import SystemSettings


def filled_spool(data):
    f = spool()
    f.write(data)
    return f


class SpooledFileResponseTests(SimpleTestCase):
    # Several chunks, and past the spool limit, so the file is on disk.
    DATA = bytes(range(256)) * (export_files.SPOOL_MAX_BYTES // 256 + 1000)

    def test_sends_the_whole_file_with_attachment_headers(self):
        response = SpooledFileResponse(filled_spool(self.DATA), "sheets.zip", ZIP)

        self.assertEqual(response.getvalue(), self.DATA)
        self.assertEqual(response["Content-Type"], ZIP)
        self.assertEqual(response["Content-Length"], str(len(self.DATA)))
        self.assertEqual(response["Content-Disposition"], 'attachment; filename="sheets.zip"')

    def test_asgi_reads_the_file_in_chunks(self):
        response = SpooledFileResponse(filled_spool(self.DATA), "sheets.zip", ZIP)

        async def collect():
            return [chunk async for chunk in response]

        chunks = async_to_sync(collect)()

        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(c) <= export_files.CHUNK_BYTES for c in chunks))
        self.assertEqual(b"".join(chunks), self.DATA)

    def test_closing_the_response_closes_the_file(self):
        f = filled_spool(b"x")
        response = SpooledFileResponse(f, "a.zip", ZIP)

        response.close()

        self.assertTrue(f.closed)


class MediaStorageCheckTests(SimpleTestCase):
    @override_settings(DEBUG=False, CLOUDINARY_URL="", LOCAL_MEDIA_PERSISTENT=False)
    def test_production_without_persistent_media_is_an_error(self):
        errors = check_media_storage(None)

        self.assertEqual([e.id for e in errors], ["ems.E001"])

    @override_settings(DEBUG=False, CLOUDINARY_URL="cloudinary://k:s@c")
    def test_cloudinary_passes(self):
        self.assertEqual(check_media_storage(None), [])

    @override_settings(DEBUG=False, CLOUDINARY_URL="", LOCAL_MEDIA_PERSISTENT=True)
    def test_a_declared_persistent_volume_passes(self):
        self.assertEqual(check_media_storage(None), [])

    @override_settings(DEBUG=True, CLOUDINARY_URL="")
    def test_development_passes(self):
        self.assertEqual(check_media_storage(None), [])


class RepairLogoTests(TestCase):
    def setUp(self):
        media = tempfile.TemporaryDirectory()
        self.addCleanup(media.cleanup)
        self.enterContext(override_settings(MEDIA_ROOT=media.name))
        # Local disk regardless of CLOUDINARY_URL in .env: no network calls.
        self.logo_field = SystemSettings._meta.get_field("logo")
        self.enterContext(mock.patch.object(self.logo_field, "storage", default_storage))
        self.settings_obj = SystemSettings.objects.create(session="2025/2026")

    def set_logo_name(self, name):
        SystemSettings.objects.filter(pk=self.settings_obj.pk).update(logo=name)

    def repair(self, *args):
        call_command("repair_logo", *args, stdout=io.StringIO())
        self.settings_obj.refresh_from_db()
        return self.settings_obj.logo

    def test_a_logo_that_exists_is_left_alone(self):
        name = default_storage.save("branding/logo.png", ContentFile(b"png"))
        self.set_logo_name(name)

        self.assertEqual(self.repair().name, name)

    def test_a_missing_logo_is_cleared(self):
        self.set_logo_name("branding/images.jpeg")

        self.assertFalse(self.repair())

    def test_dry_run_changes_nothing(self):
        self.set_logo_name("branding/images.jpeg")

        self.assertEqual(self.repair("--dry-run").name, "branding/images.jpeg")

    def test_a_local_logo_moves_to_the_configured_remote_storage(self):
        default_storage.save("branding/images.jpeg", ContentFile(b"jpeg"))
        self.set_logo_name("branding/images.jpeg")
        remote = InMemoryStorage()

        with mock.patch.object(self.logo_field, "storage", remote):
            logo = self.repair()

            self.assertTrue(remote.exists(logo.name))
            with remote.open(logo.name) as f:
                self.assertEqual(f.read(), b"jpeg")
