"""Back up the whole database to ``BACKUP_BUCKET`` (spec 0003, child 0007).

    manage.py backup_database            # one attempt, now
    manage.py backup_database --daemon   # now, then every day at BACKUP_TIME_UTC

The ``backup`` sidecar in ``deploy/compose.prod.yml`` runs the daemon. It
doesn't go through Celery, so a backup still runs when the workers are broken.
The daemon retries a failed run up to 3 times, an hour apart.
"""
from django.core.management.base import BaseCommand, CommandError

from tenancy.backups import attempt, run_forever


class Command(BaseCommand):
    help = "pg_dump the whole database to BACKUP_BUCKET with its manifest, and verify it."

    def add_arguments(self, parser):
        parser.add_argument(
            "--daemon",
            action="store_true",
            help="Back up now, then every day at BACKUP_TIME_UTC, with retries. Never exits.",
        )

    def handle(self, *args, daemon, **options):
        if daemon:
            run_forever()
            return
        try:
            key = attempt()
        except Exception as error:
            raise CommandError(f"Backup failed: {error}")
        self.stdout.write(self.style.SUCCESS(f"Backed up to {key}."))
