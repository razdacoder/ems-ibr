"""Give the public schema exactly ``<console>.<base>`` and ``api.<base>``.

Idempotent. Runs on every deploy after migrations, so changing
``PLATFORM_BASE_DOMAIN`` or ``PLATFORM_CONSOLE_SUBDOMAIN`` moves the console and the public API with it.
"""
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django_tenants.utils import get_public_schema_name

from tenancy.models import Domain, School


class Command(BaseCommand):
    help = "Make the public schema's domains match the platform host settings."

    @transaction.atomic
    def handle(self, *args, **options):
        base = settings.PLATFORM_BASE_DOMAIN
        console = f"{settings.PLATFORM_CONSOLE_SUBDOMAIN}.{base}"
        wanted = {console: True, f"api.{base}": False}
        public = School.objects.get(schema_name=get_public_schema_name())

        stale, _ = Domain.objects.filter(tenant=public).exclude(domain__in=wanted).delete()
        for domain, is_primary in wanted.items():
            Domain.objects.update_or_create(
                domain=domain, defaults={"tenant": public, "is_primary": is_primary}
            )
        self.stdout.write(
            f"Public domains: {', '.join(wanted)} ({stale} stale removed)."
        )
