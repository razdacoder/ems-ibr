"""Point SystemSettings.logo at a file that exists, or clear it.

A logo uploaded before CLOUDINARY_URL was set is stored under a local-disk
name (``branding/images.jpeg``). Once Cloudinary is configured the field
looks that name up on Cloudinary, finds nothing, and every attendance sheet
prints the placeholder. This command:

- does nothing when the logo is found where the field looks for it;
- moves the logo to Cloudinary when it is still on this machine's disk;
- otherwise clears the field, so the admin re-uploads it from Settings.
"""

from django.core.files.base import File
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand

from ems.models import SystemSettings


class Command(BaseCommand):
    help = "Move a local-disk institution logo to Cloudinary, or clear a missing one"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true", help="Report what would change, change nothing"
        )

    def handle(self, *args, dry_run=False, **options):
        for settings_obj in SystemSettings.objects.exclude(logo="").exclude(logo__isnull=True):
            self._repair(settings_obj, dry_run)

    def _repair(self, settings_obj, dry_run):
        logo = settings_obj.logo
        name = logo.name
        label = f"Session {settings_obj.session}: logo {name!r}"

        if logo.storage.exists(name):
            self.stdout.write(self.style.SUCCESS(f"{label} is in place."))
            return

        if logo.storage is not default_storage and default_storage.exists(name):
            if dry_run:
                self.stdout.write(f"{label} would be moved from local disk to Cloudinary.")
                return
            with default_storage.open(name, "rb") as f:
                logo.save(name.rsplit("/", 1)[-1], File(f), save=True)
            self.stdout.write(self.style.SUCCESS(f"{label} moved to {logo.name!r}."))
            return

        if dry_run:
            self.stdout.write(self.style.WARNING(f"{label} is missing and would be cleared."))
            return
        settings_obj.logo = None
        settings_obj.save(update_fields=["logo"])
        self.stdout.write(
            self.style.WARNING(f"{label} is missing; cleared. Re-upload it in Settings.")
        )
