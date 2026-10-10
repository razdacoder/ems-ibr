"""Give the public schema exactly ``admin.<base>`` and ``api.<base>``.

Idempotent. Runs on every deploy after migrations, so changing
``PLATFORM_BASE_DOMAIN`` moves the console and the public API with it.
"""
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django_tenants.utils import get_public_schema_name

from tenancy.models import Domain, School


class Command(BaseCommand):
    help = "Make the public schema's domains match PLATFORM_BASE_DOMAIN."

    @transaction.atomic
    def handle(self, *args, **options):
        base = settings.PLATFORM_BASE_DOMAIN
        wanted = {f"admin.{base}": True, f"api.{base}": False}
        public = School.objects.get(schema_name=get_public_schema_name())

        stale, _ = Domain.objects.filter(tenant=public).exclude(domain__in=wanted).delete()
        for domain, is_primary in wanted.items():
            Domain.objects.update_or_create(
                domain=domain, defaults={"tenant": public, "is_primary": is_primary}
            )
        self.stdout.write(
            f"Public domains: {', '.join(wanted)} ({stale} stale removed)."
        )
