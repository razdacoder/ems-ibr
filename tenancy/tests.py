"""Schools are kept apart by Postgres schemas, picked from the Host header
(spec 0003, child 0001)."""
from io import StringIO
from unittest import mock

from django.core.exceptions import ValidationError
from django.core.management import CommandError, call_command
from django.db import connection
from django.test import override_settings
from django.utils import timezone
from django_tenants.utils import get_public_schema_name, schema_context
from rest_framework.authtoken.models import Token

from ems.models import AuditLog, SystemSettings, User
from tenancy.features import KEYS
from tenancy.models import Domain, Plan, School, validate_feature_keys
from tenancy.slugs import RESERVED, SLUG_RE, schema_name_for
from tenancy.testcases import SchoolClient, SchoolTestCase

OTHER_HOST = "other.localhost"


class TwoSchoolsTestCase(SchoolTestCase):
    """The test school plus a second one, ``other``, made once per run."""

    @classmethod
    def setUpClass(cls):
        connection.set_schema_to_public()
        other = School.objects.filter(slug="other").first()
        if other is None:
            other = School.objects.create(
                schema_name="school_other", slug="other", name="Other School",
                plan=Plan.objects.get(code="platform"), status=School.Status.ACTIVE,
                first_admin_name="Other Admin", first_admin_email="admin@other.localhost",
            )
            Domain.objects.create(domain=OTHER_HOST, tenant=other, is_primary=True)
            other.create_schema(check_if_exists=True, verbosity=0)
        cls.other = other
        super().setUpClass()

    def tearDown(self):
        # A request to another host leaves the connection on that school.
        connection.set_tenant(self.tenant)
        super().tearDown()

    def make_user(self, email, password="pw-123456"):
        return User.objects.create_user(
            email=email, first_name="Ada", last_name="L", password=password
        )


class IsolationTests(TwoSchoolsTestCase):
    def test_each_school_sees_only_its_own_rows(self):
        # covers: AC-1
        self.make_user("a@x.com")
        SystemSettings.objects.create(institution_name="Test School")
        with schema_context("school_other"):
            self.make_user("a@x.com")
            SystemSettings.objects.create(institution_name="Other School")
            self.assertEqual(User.objects.count(), 1)
            self.assertEqual(
                list(SystemSettings.objects.values_list("institution_name", flat=True)),
                ["Other School"],
            )

        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(
            list(SystemSettings.objects.values_list("institution_name", flat=True)),
            ["Test School"],
        )

    def test_public_schema_holds_no_school_tables(self):
        # covers: AC-1
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT count(*) FROM information_schema.tables "
                "WHERE table_schema = %s AND table_name LIKE 'ems\\_%%'",
                [get_public_schema_name()],
            )
            self.assertEqual(cursor.fetchone()[0], 0)

    def test_a_token_only_works_on_its_own_school(self):
        # covers: AC-2
        user = self.make_user("a@x.com")
        token = Token.objects.get(user=user).key

        mine = SchoolClient(HTTP_AUTHORIZATION=f"Token {token}")
        self.assertEqual(mine.get("/api/auth/me/").status_code, 200)

        theirs = SchoolClient(HTTP_HOST=OTHER_HOST, HTTP_AUTHORIZATION=f"Token {token}")
        self.assertEqual(theirs.get("/api/auth/me/").status_code, 401)

    def test_login_reads_the_hosts_school(self):
        # covers: AC-1
        self.make_user("a@x.com", password="pw-test-123")
        body = {"email": "a@x.com", "password": "pw-test-123"}

        self.assertEqual(
            SchoolClient().post("/api/auth/login/", body, format="json").status_code, 200
        )
        self.assertEqual(
            SchoolClient(HTTP_HOST=OTHER_HOST)
            .post("/api/auth/login/", body, format="json").status_code,
            400,
        )


class HostResolutionTests(TwoSchoolsTestCase):
    def test_an_unknown_school_is_a_generic_404(self):
        # covers: AC-7
        response = SchoolClient(HTTP_HOST="typo.localhost").get("/api/auth/me/")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "School not found."})

        page = SchoolClient(HTTP_HOST="typo.localhost").get("/timetable")
        self.assertEqual(page.status_code, 404)
        self.assertEqual(page.content, b"School not found.")

    def test_a_purged_school_looks_like_an_unknown_one(self):
        # covers: AC-7
        School.objects.filter(pk=self.other.pk).update(status=School.Status.PURGED)
        response = SchoolClient(HTTP_HOST=OTHER_HOST).get("/api/auth/me/")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "School not found."})

    def test_hosts_match_without_case_or_port(self):
        user = self.make_user("a@x.com")
        token = Token.objects.get(user=user).key
        client = SchoolClient(HTTP_HOST="TEST.localhost:3000", HTTP_AUTHORIZATION=f"Token {token}")
        self.assertEqual(client.get("/api/auth/me/").status_code, 200)

    def test_a_host_outside_allowed_hosts_is_a_400(self):
        response = SchoolClient(HTTP_HOST="test.evil.example").get("/api/auth/me/")
        self.assertEqual(response.status_code, 400)

    def test_healthz_answers_for_any_host(self):
        response = SchoolClient(HTTP_HOST="10.0.0.7:8000").get("/healthz")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"ok")

    def test_public_hosts_serve_only_the_public_urlconf(self):
        call_command("ensure_public_domains", stdout=StringIO())
        api = SchoolClient(HTTP_HOST="api.localhost")
        self.assertEqual(api.get("/api/public/features/").status_code, 200)
        self.assertEqual(api.get("/api/auth/me/").status_code, 404)
        self.assertEqual(
            SchoolClient(HTTP_HOST="admin.localhost").get("/api/auth/me/").status_code, 404
        )


class TimezoneTests(TwoSchoolsTestCase):
    def test_a_request_runs_in_the_schools_zone_then_resets(self):
        # covers: AC-6
        School.objects.filter(pk=self.tenant.pk).update(timezone="Asia/Tokyo")
        user = self.make_user("a@x.com")
        token = Token.objects.get(user=user).key

        data = SchoolClient(HTTP_AUTHORIZATION=f"Token {token}").get("/api/auth/me/").json()

        self.assertTrue(data["created_at"].endswith("+09:00"), data["created_at"])
        self.assertEqual(timezone.get_current_timezone_name(), "UTC")


@override_settings(PLATFORM_BASE_DOMAIN="staging.ordo.app")
class PublicDomainsTests(SchoolTestCase):
    def test_public_domains_follow_the_base_domain(self):
        public = School.objects.get(schema_name=get_public_schema_name())
        Domain.objects.create(domain="old.example", tenant=public)

        call_command("ensure_public_domains", stdout=StringIO())
        call_command("ensure_public_domains", stdout=StringIO())

        self.assertEqual(
            dict(Domain.objects.filter(tenant=public).values_list("domain", "is_primary")),
            {"admin.staging.ordo.app": True, "api.staging.ordo.app": False},
        )


class HealthzTests(SchoolTestCase):
    def test_healthz_reports_unavailable_when_the_database_is_down(self):
        with mock.patch(
            "tenancy.middleware.connection.cursor", side_effect=Exception("db down")
        ):
            response = SchoolClient(HTTP_HOST="10.0.0.7").get("/healthz")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.content, b"unavailable")


class AuditOnPublicHostsTests(TwoSchoolsTestCase):
    def test_a_sign_in_attempt_on_a_public_host_writes_no_audit_row(self):
        call_command("ensure_public_domains", stdout=StringIO())
        with mock.patch.object(AuditLog.objects, "create") as create:
            response = SchoolClient(HTTP_HOST="api.localhost").post(
                "/api/auth/login/", {"email": "a@x.com", "password": "x"}, format="json"
            )
        self.assertEqual(response.status_code, 404)
        create.assert_not_called()

    def test_a_sign_in_attempt_is_audited_in_the_hosts_school_only(self):
        # covers: AC-1
        SchoolClient(HTTP_HOST=OTHER_HOST).post(
            "/api/auth/login/", {"email": "a@x.com", "password": "x"}, format="json"
        )
        connection.set_tenant(self.tenant)

        self.assertFalse(AuditLog.objects.exists())
        with schema_context("school_other"):
            self.assertEqual(
                list(AuditLog.objects.values_list("action", flat=True)),
                ["Failed sign-in attempt"],
            )


class SlugTests(SchoolTestCase):
    def test_slugs_follow_the_format_rule(self):
        for slug in ("abc", "a1b", "uni-lagos", "a" * 30):
            with self.subTest(slug=slug):
                self.assertTrue(SLUG_RE.match(slug))

    def test_slugs_outside_the_format_rule_are_refused(self):
        for slug in ("ab", "a" * 31, "-abc", "abc-", "Abc", "a_b", "a.b", "", "ünî"):
            with self.subTest(slug=slug):
                self.assertIsNone(SLUG_RE.match(slug))

    def test_the_schema_name_swaps_hyphens_for_underscores(self):
        self.assertEqual(schema_name_for("uni-lagos"), "school_uni_lagos")
        self.assertEqual(schema_name_for("acme"), "school_acme")

    def test_platform_hostnames_are_reserved(self):
        for slug in ("admin", "api", "www", "test", "demo", "localhost", "staging"):
            with self.subTest(slug=slug):
                self.assertIn(slug, RESERVED)


class FeatureKeyTests(SchoolTestCase):
    def test_known_keys_and_null_are_accepted(self):
        validate_feature_keys(None)
        validate_feature_keys([])
        validate_feature_keys(sorted(KEYS))

    def test_an_unknown_key_is_refused_by_name(self):
        with self.assertRaisesMessage(ValidationError, "Unknown feature keys: sso."):
            validate_feature_keys(["exports", "sso"])

    def test_anything_but_a_list_of_strings_is_refused(self):
        for value in ("exports", {"exports": True}, [1]):
            with self.subTest(value=value):
                with self.assertRaises(ValidationError):
                    validate_feature_keys(value)


class SeedTests(SchoolTestCase):
    def test_the_platform_plan_is_internal_and_unlimited(self):
        plan = Plan.objects.get(code="platform")
        self.assertFalse(plan.is_active)
        self.assertIsNone(plan.max_students)
        self.assertIsNone(plan.max_staff_users)
        self.assertEqual(set(plan.features), KEYS)

    def test_the_public_schema_is_an_active_school_on_the_platform_plan(self):
        public = School.objects.get(schema_name=get_public_schema_name())
        self.assertEqual(public.status, School.Status.ACTIVE)
        self.assertEqual(public.plan.code, "platform")


class CreateSchoolCommandTests(SchoolTestCase):
    def setUp(self):
        super().setUp()
        # Schools are only created from the public schema.
        connection.set_schema_to_public()

    def tearDown(self):
        connection.set_tenant(self.tenant)
        super().tearDown()

    def create(self, *args):
        call_command("create_school", *args, stdout=StringIO(), verbosity=0)

    def test_it_provisions_a_live_school_at_its_subdomain(self):
        # covers: AC-1
        self.create("uni-lagos")

        school = School.objects.get(slug="uni-lagos")
        self.assertEqual(school.schema_name, "school_uni_lagos")
        self.assertEqual(school.status, School.Status.ACTIVE)
        self.assertTrue(school.was_ever_active)
        self.assertEqual(school.plan.code, "platform")
        self.assertEqual(
            list(school.domains.values_list("domain", "is_primary")),
            [("uni-lagos.localhost", True)],
        )
        with schema_context("school_uni_lagos"):
            self.assertEqual(
                list(SystemSettings.objects.values_list("institution_name", flat=True)),
                ["Uni Lagos"],
            )

    def test_it_uses_the_named_plan(self):
        Plan.objects.create(code="basic", name="Basic")
        self.create("acme", "--plan", "basic")
        self.assertEqual(School.objects.get(slug="acme").plan.code, "basic")

    def test_a_bad_slug_is_refused_and_nothing_is_saved(self):
        with self.assertRaisesMessage(CommandError, "Slug must be"):
            self.create("Bad_Slug")
        self.assertFalse(School.objects.filter(slug="Bad_Slug").exists())

    def test_a_taken_slug_is_refused(self):
        with self.assertRaisesMessage(CommandError, "already exists"):
            self.create("test")

    def test_an_unknown_plan_is_refused(self):
        with self.assertRaisesMessage(CommandError, "No plan with code 'gold'"):
            self.create("acme", "--plan", "gold")
        self.assertFalse(School.objects.filter(slug="acme").exists())

    def test_a_provisioning_error_marks_the_school_failed(self):
        with mock.patch.object(School, "create_schema", side_effect=RuntimeError("boom")):
            with self.assertRaisesMessage(CommandError, "Provisioning failed: boom"):
                self.create("acme")

        school = School.objects.get(slug="acme")
        self.assertEqual(school.status, School.Status.FAILED)
        self.assertEqual(school.provisioning_error, "boom")
        self.assertFalse(school.was_ever_active)


@override_settings(PLATFORM_BASE_DOMAIN="class-level.example")
class SchoolTestCaseTests(SchoolTestCase):
    """The base keeps TestCase's class hooks that the tenant cases skip."""

    @classmethod
    def setUpTestData(cls):
        cls.settings_row = SystemSettings.objects.create(institution_name="From setUpTestData")

    def test_class_setup_runs_inside_the_test_school(self):
        self.assertEqual(connection.schema_name, "school_test")
        self.assertTrue(SystemSettings.objects.filter(pk=self.settings_row.pk).exists())

    def test_class_level_settings_overrides_apply(self):
        from django.conf import settings

        self.assertEqual(settings.PLATFORM_BASE_DOMAIN, "class-level.example")

    def test_the_default_client_calls_the_test_school(self):
        user = User.objects.create_user(
            email="a@x.com", first_name="Ada", last_name="L", password="pw-123456"
        )
        self.client.force_authenticate(user)
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 200)
