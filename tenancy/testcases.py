"""Test base for anything that touches school data.

Every ``ems`` table lives in a school's schema, so tests run inside one: the
``test`` school at ``test.localhost``, created once per run and reused by
every class (``FastTenantTestCase``). Each test still rolls back as usual.
"""
from django_tenants.test.cases import FastTenantTestCase, TenantTestCase
from rest_framework.test import APIClient

from tenancy.models import Plan, School

SCHOOL_TEST_HOST = "test.localhost"


class SchoolClient(APIClient):
    """``APIClient`` that calls the test school's host."""

    def __init__(self, *args, **defaults):
        defaults.setdefault("HTTP_HOST", SCHOOL_TEST_HOST)
        super().__init__(*args, **defaults)


class SchoolTestCase(FastTenantTestCase):
    client_class = SchoolClient

    @classmethod
    def get_test_schema_name(cls):
        return "school_test"

    @classmethod
    def get_test_tenant_domain(cls):
        return SCHOOL_TEST_HOST

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.slug = "test"
        tenant.name = "Test School"
        tenant.plan = Plan.objects.get(code="platform")
        tenant.status = School.Status.ACTIVE
        tenant.was_ever_active = True
        tenant.first_admin_name = "Test Admin"
        tenant.first_admin_email = "admin@test.localhost"

    @classmethod
    def setup_test_tenant_and_domain(cls):
        super().setup_test_tenant_and_domain()
        # School never creates its schema on save; provisioning does.
        cls.tenant.create_schema(check_if_exists=True, verbosity=0)

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # The tenant test cases skip TestCase.setUpClass, which would silently
        # drop setUpTestData, class level override_settings and the class
        # transaction. Run it now, inside the school's schema.
        super(TenantTestCase, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TenantTestCase, cls).tearDownClass()
        super().tearDownClass()

