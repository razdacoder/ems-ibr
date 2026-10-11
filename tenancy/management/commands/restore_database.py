"""Restore a whole database backup into an empty database (spec 0004, assumed).

    manage.py restore_database db/daily/ordo-20261011T010000Z.dump \\
        --target-url postgres://ordo:...@postgres:5432/ordo_restore

Meant for the restore drill (into a scratch database) and for disaster
recovery (into a fresh server). It refuses the live ``DATABASE_URL`` unless
``--into-live`` is passed.
"""
from django.core.management.base import BaseCommand, CommandError

from tenancy.backups import BackupError, is_live, restore


class Command(BaseCommand):
    help = "Download a backup from BACKUP_BUCKET and pg_restore it into an empty database."

    def add_arguments(self, parser):
        parser.add_argument("key", help="Bucket key, e.g. db/daily/ordo-20261011T010000Z.dump")
        parser.add_argument("--target-url", required=True, help="An empty Postgres database.")
        parser.add_argument(
            "--into-live",
            action="store_true",
            help="Allow the target to be the live DATABASE_URL.",
        )

    def handle(self, *args, key, target_url, into_live, **options):
        if is_live(target_url) and not into_live:
            raise CommandError(
                "The target is the live database. Restore into a scratch database, "
                "or pass --into-live if you really mean it."
            )
        try:
            restore(key, target_url)
        except BackupError as error:
            raise CommandError(str(error))
        self.stdout.write(self.style.SUCCESS(f"Restored {key}."))
