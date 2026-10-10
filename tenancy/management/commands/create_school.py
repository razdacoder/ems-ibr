"""Create and provision a school in one go, for development and the test
environment (``manage.py create_school demo``).

Temporary: the console's create form and the background provisioning task
replace it (spec 0003, build slice 7). Reserved slugs such as ``demo`` are
allowed here on purpose, since dev schools only ever come from code.
"""
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django_tenants.utils import schema_context

from tenancy.models import Domain, Plan, School
from tenancy.slugs import SLUG_RE, schema_name_for


class Command(BaseCommand):
    help = "Create a school schema at <slug>.<PLATFORM_BASE_DOMAIN> (dev only)."

    def add_arguments(self, parser):
        parser.add_argument("slug")
        parser.add_argument("--plan", default="platform", help="Plan code.")

    def handle(self, *args, slug, plan, **options):
        if not SLUG_RE.match(slug):
            raise CommandError(
                "Slug must be 3 to 30 lowercase letters, digits or inner hyphens."
            )
        if School.objects.filter(slug=slug).exists():
            raise CommandError(f"A school with slug '{slug}' already exists.")
        try:
            plan_obj = Plan.objects.get(code=plan)
        except Plan.DoesNotExist:
            raise CommandError(f"No plan with code '{plan}'.")

        domain = f"{slug}.{settings.PLATFORM_BASE_DOMAIN}"
        name = slug.replace("-", " ").title()
        with transaction.atomic():
            school = School.objects.create(
                schema_name=schema_name_for(slug),
                slug=slug,
                name=name,
                plan=plan_obj,
                status=School.Status.PROVISIONING,
                provisioning_started_at=timezone.now(),
                first_admin_name="",
                first_admin_email="",
            )
            Domain.objects.create(domain=domain, tenant=school, is_primary=True)

        try:
            school.create_schema(check_if_exists=True, verbosity=options["verbosity"])
            with schema_context(school.schema_name):
                from ems.models import SystemSettings

                SystemSettings.objects.create(institution_name=name)
        except Exception as exc:
            school.status = School.Status.FAILED
            school.provisioning_error = str(exc)[:2000]
            school.save(update_fields=["status", "provisioning_error"])
            raise CommandError(f"Provisioning failed: {exc}") from exc

        school.status = School.Status.ACTIVE
        school.was_ever_active = True
        school.save(update_fields=["status", "was_ever_active"])
        self.stdout.write(self.style.SUCCESS(
            f"School '{name}' is live at {domain} (schema {school.schema_name})."
        ))
