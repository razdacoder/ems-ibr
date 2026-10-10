"""Joining a school by invite: staff invites and the accept link
(spec 0003, child 0004)."""
from datetime import timedelta
from unittest import mock

from django.utils import timezone

from ems import invites
from ems.models import Invite, User
from ems.tests.helpers import make_department
from tenancy.tasks import send_email
from tenancy.testcases import SchoolClient, SchoolTestCase

PASSWORD = "plum orchard 42"


class InviteTestCase(SchoolTestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="sa@test.localhost", first_name="Sade", last_name="Bello",
            password=PASSWORD, role=User.Role.SUPER_ADMIN, is_staff=True,
        )
        self.client.force_authenticate(self.admin)
        self.visitor = SchoolClient()
        self.department = make_department("csc")

    def invite(self, client=None, path="/api/invites/", **data):
        """POST with the email task captured; returns ``(response, raw token)``."""
        with mock.patch.object(send_email, "delay") as delay, \
                self.captureOnCommitCallbacks(execute=True):
            response = (client or self.client).post(path, data, format="json")
        token = None
        if delay.called:
            to, subject, template, context = delay.call_args.args
            self.sent = (to, subject, template, context)
            token = context["url"].rsplit("/invite/", 1)[1]
        return response, token

    def accept(self, token, **overrides):
        data = {"first_name": "Ngozi", "last_name": "Eze", "password": PASSWORD, **overrides}
        return self.visitor.post(f"/api/invites/{token}/accept/", data, format="json")


class StaffInviteTests(InviteTestCase):
    def test_a_super_admin_invites_staff_by_email(self):
        # covers: AC-23, AC-21
        response, token = self.invite(email="Ngozi@Test.localhost", role="DO")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["email"], "ngozi@test.localhost")
        self.assertEqual(response.data["invited_by"]["name"], "Sade Bello")
        to, subject, template, context = self.sent
        self.assertEqual((to, template), ("ngozi@test.localhost", "staff_invite"))
        self.assertEqual(context["school_name"], "Test School")
        self.assertEqual(context["role"], "Data Officer")
        self.assertTrue(context["url"].endswith(f"://test.localhost/invite/{token}"))
        self.assertEqual(Invite.objects.get().token_hash, invites.hash_token(token))

    def test_a_department_officer_needs_a_department(self):
        # covers: AC-23
        response, _ = self.invite(email="d@test.localhost", role=None)
        self.assertEqual(response.status_code, 400)
        self.assertIn("department_id", response.data["errors"])
        response, _ = self.invite(
            email="d@test.localhost", role=None, department_id=self.department.pk
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["department"]["slug"], "csc")

    def test_an_admin_role_drops_any_department(self):
        response, _ = self.invite(email="e@test.localhost", role="ECM", department_id=self.department.pk)
        self.assertIsNone(response.data["department"])

    def test_inviting_an_existing_user_is_a_conflict(self):
        # covers: AC-22
        response, _ = self.invite(email="SA@test.localhost", role="DO")
        self.assertEqual(response.status_code, 409)

    def test_only_super_admins_invite(self):
        officer = User.objects.create_user(
            email="do@test.localhost", password=PASSWORD, role=User.Role.DATA_OFFICER, is_staff=True
        )
        client = SchoolClient()
        client.force_authenticate(officer)
        response, _ = self.invite(client, email="x@test.localhost", role="DO")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(client.get("/api/invites/").status_code, 403)

    def test_a_new_invite_replaces_the_open_one_for_that_email(self):
        # covers: AC-22
        _, first = self.invite(email="n@test.localhost", role="DO")
        _, second = self.invite(email="n@test.localhost", role="FO")
        listed = self.client.get("/api/invites/").data["results"]
        self.assertEqual([(i["email"], i["role"]) for i in listed], [("n@test.localhost", "FO")])
        self.assertEqual(self.visitor.get(f"/api/invites/{first}/").status_code, 410)
        self.assertEqual(self.visitor.get(f"/api/invites/{second}/").status_code, 200)

    def test_revoke_kills_the_link(self):
        _, token = self.invite(email="n@test.localhost", role="DO")
        invite = Invite.objects.get()
        self.assertEqual(self.client.post(f"/api/invites/{invite.pk}/revoke/").status_code, 204)
        self.assertEqual(self.visitor.get(f"/api/invites/{token}/").status_code, 410)
        self.assertEqual(self.client.get("/api/invites/").data["count"], 0)
        self.assertEqual(self.client.post(f"/api/invites/{invite.pk}/revoke/").status_code, 404)

    def test_resend_sends_a_fresh_link(self):
        _, old = self.invite(email="n@test.localhost", role=None, department_id=self.department.pk)
        invite = Invite.objects.get()
        Invite.objects.filter(pk=invite.pk).update(expires_at=timezone.now() - timedelta(days=1))
        self.assertTrue(self.client.get("/api/invites/").data["results"][0]["is_expired"])
        response, new = self.invite(path=f"/api/invites/{invite.pk}/resend/")
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.data["department"]["slug"], "csc")
        self.assertNotEqual(old, new)
        self.assertEqual(self.visitor.get(f"/api/invites/{old}/").status_code, 410)
        self.assertEqual(self.visitor.get(f"/api/invites/{new}/").status_code, 200)

    def test_direct_user_creation_still_works(self):
        # covers: AC-23
        response = self.client.post(
            "/api/users/",
            {"email": "direct@test.localhost", "first_name": "D", "last_name": "U",
             "role": "DO", "password": PASSWORD},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)


class AcceptInviteTests(InviteTestCase):
    def setUp(self):
        super().setUp()
        _, self.token = self.invite(
            email="ngozi@test.localhost", role=None, department_id=self.department.pk
        )

    def test_the_link_shows_who_is_invited_where(self):
        # covers: AC-22
        response = self.visitor.get(f"/api/invites/{self.token}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["school_name"], "Test School")
        self.assertEqual(response.data["email"], "ngozi@test.localhost")
        self.assertIsNone(response.data["role"])
        self.assertEqual(response.data["department"]["slug"], "csc")

    def test_accepting_creates_the_user_and_signs_them_in(self):
        # covers: AC-22
        response = self.accept(self.token)
        self.assertEqual(response.status_code, 200, response.data)
        user = User.objects.get(email="ngozi@test.localhost")
        self.assertEqual(user.department, self.department)
        self.assertFalse(user.is_staff)
        self.assertTrue(user.check_password(PASSWORD))
        me = SchoolClient(HTTP_AUTHORIZATION=f"Token {response.data['token']}")
        self.assertEqual(me.get("/api/auth/me/").data["email"], "ngozi@test.localhost")
        self.assertIsNotNone(Invite.objects.get().accepted_at)

    def test_a_link_works_once(self):
        # covers: AC-22
        self.assertEqual(self.accept(self.token).status_code, 200)
        self.assertEqual(self.accept(self.token).status_code, 410)
        self.assertEqual(self.visitor.get(f"/api/invites/{self.token}/").status_code, 410)

    def test_an_expired_or_unknown_link_is_gone(self):
        # covers: AC-22
        Invite.objects.update(expires_at=timezone.now())
        self.assertEqual(self.accept(self.token).status_code, 410)
        self.assertEqual(self.visitor.get("/api/invites/not-a-token/").status_code, 410)

    def test_a_weak_password_is_refused_and_the_link_still_works(self):
        response = self.accept(self.token, password="12345678")
        self.assertEqual(response.status_code, 400)
        self.assertIn("password", response.data["errors"])
        self.assertEqual(self.accept(self.token).status_code, 200)

    def test_an_email_that_already_has_a_user_is_a_conflict(self):
        # covers: AC-22
        User.objects.create_user(email="ngozi@test.localhost", password=PASSWORD)
        self.assertEqual(self.accept(self.token).status_code, 409)

    def test_an_admin_role_invite_makes_a_staff_user(self):
        _, token = self.invite(email="sa2@test.localhost", role="SA")
        self.assertEqual(self.accept(token).status_code, 200)
        user = User.objects.get(email="sa2@test.localhost")
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_super_admin)
