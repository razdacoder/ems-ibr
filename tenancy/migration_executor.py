"""``migrate_schemas --tenant`` migrates live schools only.

Wired in through ``GET_EXECUTOR_FUNCTION``. A school in ``provisioning`` or
``failed`` is skipped: provisioning migrates its own schema, and retry drops
and rebuilds a failed one, so neither can drift (spec 0003, 0001).
"""
from django_tenants.migration_executors import StandardExecutor
from django_tenants.utils import get_public_schema_name


class LiveSchoolsExecutor(StandardExecutor):
    codename = "live_schools"

    def run_migrations(self, tenants=None):
        tenants = list(tenants or [])
        # An explicit --schema (provisioning's create_schema) always runs.
        if not self.options.get("schema_name"):
            tenants = self._live(tenants)
        super().run_migrations(tenants=tenants)

    def _live(self, tenants):
        from tenancy.models import School

        public = get_public_schema_name()
        if tenants == [public]:
            # The shared run, possibly before tenancy_school exists.
            return tenants
        live = set(
            School.objects.filter(
                schema_name__in=tenants, status__in=School.LIVE_STATUSES
            ).values_list("schema_name", flat=True)
        )
        return [s for s in tenants if s == public or s in live]


def get_executor(codename=None):
    return LiveSchoolsExecutor
