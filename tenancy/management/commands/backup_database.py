"""Back up the whole database to ``BACKUP_BUCKET`` (spec 0004, assumed).

    manage.py backup_database            # once, now
    manage.py backup_database --daemon   # now, then every day at BACKUP_TIME_UTC

The ``backup`` sidecar in ``deploy/compose.prod.yml`` runs the daemon. It
doesn't go through Celery, so a backup still runs when the workers are broken.
"""
import logging
import time
from datetime import datetime, timezone as dt_timezone

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from tenancy.backups import BackupError, back_up, next_run

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "pg_dump the whole database to BACKUP_BUCKET, verify it, then prune old backups."

    def add_arguments(self, parser):
        parser.add_argument(
            "--daemon",
            action="store_true",
            help="Back up now, then every day at BACKUP_TIME_UTC. Never exits.",
        )

    def handle(self, *args, daemon, **options):
        if not daemon:
            try:
                key = back_up()
            except BackupError as error:
                raise CommandError(str(error))
            self.stdout.write(self.style.SUCCESS(f"Backed up to {key}."))
            return

        while True:
            try:
                key = back_up()
                self.stdout.write(f"Backed up to {key}.")
            except Exception:
                # The heartbeat goes stale, so the container turns unhealthy.
                logger.exception("Database backup failed.")
            now = datetime.now(dt_timezone.utc)
            wake = next_run(now, settings.BACKUP_TIME_UTC)
            self.stdout.write(f"Next backup at {wake:%Y-%m-%d %H:%M} UTC.")
            time.sleep((wake - now).total_seconds())
