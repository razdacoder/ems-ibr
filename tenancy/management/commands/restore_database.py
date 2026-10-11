"""Restore a whole database backup into an empty database (spec 0003, child 0007).

    manage.py restore_database --latest --verify \\
        --target-url postgres://ordo:...@postgres:5432/ordo_restore_drill
    manage.py restore_database db/daily/ordo-20261011T010000Z.dump --target-url ...

Meant for the restore drill (into a scratch database) and for disaster
recovery (into a fresh server). It refuses the live database unless
``--into-live`` is passed, and always refuses a target that isn't empty.
"""
from django.core.management.base import BaseCommand, CommandError

from tenancy import backups


class Command(BaseCommand):
    help = "Download a backup from BACKUP_BUCKET and pg_restore it into an empty database."

    def add_arguments(self, parser):
        which = parser.add_mutually_exclusive_group(required=True)
        which.add_argument(
            "key", nargs="?", help="Bucket key, e.g. db/daily/ordo-20261011T010000Z.dump"
        )
        which.add_argument("--latest", action="store_true", help="The newest daily backup.")
        parser.add_argument("--target-url", required=True, help="An empty Postgres database.")
        parser.add_argument(
            "--verify",
            action="store_true",
            help="Compare the restored schemas and school count with the backup's manifest.",
        )
        parser.add_argument(
            "--into-live",
            action="store_true",
            help="Allow the target to be the live database (disaster recovery only).",
        )

    def handle(self, *args, key, latest, target_url, verify, into_live, **options):
        try:
            if latest:
                key = backups.latest_key(backups._bucket())
            backups.check_target(target_url, into_live=into_live)
            self.stdout.write(f"Restoring {key}...")
            backups.restore(key, target_url)
            self.stdout.write(self.style.SUCCESS(f"Restored {key}."))
            if not verify:
                return
            expected, actual = backups.verify(key, target_url)
        except backups.BackupError as error:
            raise CommandError(str(error))

        self.stdout.write(f"Manifest: {expected['schools']} schools, schemas {expected['schemas']}")
        self.stdout.write(f"Restored: {actual['schools']} schools, schemas {actual['schemas']}")
        if expected != actual:
            raise CommandError("The restored database doesn't match the manifest.")
        self.stdout.write(self.style.SUCCESS("The restored database matches the manifest."))

