"""A platform admin's own account: password, authenticator and sessions."""
import pyotp

from tenancy.auth import issue_token
from tenancy.models import PlatformAdmin, PlatformAuditLog, PlatformToken
from tenancy.test_platform_auth import CONSOLE, PASSWORD, PlatformTestCase, current_code
from tenancy.testcases import SchoolClient

NEW_PASSWORD = "a much longer passphrase 42"


class AccountTestCase(PlatformTestCase):
    def setUp(self):
        super().setUp()
        self.admin = self.make_admin()
        self.me = self.sign_in(self.admin)

    def second_session(self):
        """Another signed in device. Signing in again in the same 30 seconds
        would replay the code, so the token is issued directly."""
        key, _ = issue_token(self.admin)
        return SchoolClient(HTTP_HOST=CONSOLE, HTTP_AUTHORIZATION=f"Bearer {key}")


class PasswordTests(AccountTestCase):
    def test_changing_the_password_signs_out_other_sessions_only(self):
        other = self.second_session()

        response = self.me.post(
            "/api/platform/me/password/",
            {"current_password": PASSWORD, "new_password": NEW_PASSWORD},
            format="json",
        )

        self.assertEqual(response.status_code, 204, response.data)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.check_password(NEW_PASSWORD))
        self.assertEqual(self.me.get("/api/platform/me/").status_code, 200)
        self.assertEqual(other.get("/api/platform/me/").status_code, 401)

    def test_a_wrong_current_password_is_refused_and_counts_toward_lockout(self):
        for _ in range(5):
            response = self.me.post(
                "/api/platform/me/password/",
                {"current_password": "nope", "new_password": NEW_PASSWORD},
                format="json",
            )
            self.assertEqual(response.status_code, 400)
            self.assertIn("current_password", response.data["errors"])
        locked = self.me.post(
            "/api/platform/me/password/",
            {"current_password": PASSWORD, "new_password": NEW_PASSWORD},
            format="json",
        )
        self.assertEqual(locked.status_code, 429)

    def test_a_weak_new_password_is_refused(self):
        response = self.me.post(
            "/api/platform/me/password/",
            {"current_password": PASSWORD, "new_password": "short"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)


class ReenrolTests(AccountTestCase):
    def start(self):
        self.admin.refresh_from_db()
        return self.me.post(
            "/api/platform/me/2fa/",
            {"current_password": PASSWORD, "code": current_code(self.admin, offset=1)},
            format="json",
        )

    def test_a_new_authenticator_replaces_the_old_one_once_confirmed(self):
        old_secret = self.admin.totp_secret
        started = self.start()
        self.assertEqual(started.status_code, 200, started.data)
        self.admin.refresh_from_db()
        # Nothing changes until the new code is confirmed.
        self.assertEqual(self.admin.totp_secret, old_secret)

        secret = pyotp.parse_uri(started.data["otpauth_uri"]).secret
        response = self.me.post(
            "/api/platform/me/2fa/confirm/",
            {"challenge": started.data["challenge"], "code": pyotp.TOTP(secret).now()},
            format="json",
        )

        self.assertEqual(response.status_code, 204, response.data)
        self.admin.refresh_from_db()
        self.assertNotEqual(self.admin.totp_secret, old_secret)
        self.assertTrue(PlatformAuditLog.objects.filter(action="totp_reenrolled").exists())

    def test_a_wrong_code_for_the_new_authenticator_changes_nothing(self):
        old_secret = self.admin.totp_secret
        started = self.start()
        response = self.me.post(
            "/api/platform/me/2fa/confirm/",
            {"challenge": started.data["challenge"], "code": "000000"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.totp_secret, old_secret)

    def test_starting_needs_a_current_code(self):
        response = self.me.post(
            "/api/platform/me/2fa/",
            {"current_password": PASSWORD, "code": "000000"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("code", response.data["errors"])

    def test_another_admins_challenge_is_refused(self):
        started = self.start()
        other = self.sign_in(self.make_admin("two@ordo.app"))
        response = other.post(
            "/api/platform/me/2fa/confirm/",
            {"challenge": started.data["challenge"], "code": "123456"},
            format="json",
        )
        self.assertEqual(response.status_code, 410)


class SessionTests(AccountTestCase):
    def test_lists_and_revokes_ones_own_sessions(self):
        other = self.second_session()

        sessions = self.me.get("/api/platform/me/sessions/").data
        self.assertEqual(len(sessions), 2)
        self.assertEqual(sum(s["current"] for s in sessions), 1)
        other_id = next(s["id"] for s in sessions if not s["current"])

        self.assertEqual(self.me.delete(f"/api/platform/me/sessions/{other_id}/").status_code, 204)
        self.assertEqual(other.get("/api/platform/me/").status_code, 401)
        self.assertEqual(self.me.get("/api/platform/me/").status_code, 200)

    def test_cannot_revoke_someone_elses_session(self):
        stranger = self.make_admin("two@ordo.app")
        self.sign_in(stranger)
        theirs = PlatformToken.objects.filter(admin=stranger).first().public_id
        self.assertEqual(self.me.delete(f"/api/platform/me/sessions/{theirs}/").status_code, 404)

    def test_sign_out_everywhere_else(self):
        other = self.second_session()
        response = self.me.post("/api/platform/me/sessions/revoke-others/")
        self.assertEqual(response.data, {"ended": 1})
        self.assertEqual(other.get("/api/platform/me/").status_code, 401)

    def test_an_owner_can_sign_another_admin_out_everywhere(self):
        support_admin = self.make_admin("support@ordo.app", role=PlatformAdmin.Role.SUPPORT)
        support = self.sign_in(support_admin)

        # Support can't do it to anyone.
        self.assertEqual(
            support.post(f"/api/platform/admins/{self.admin.pk}/sign-out/").status_code, 403
        )
        response = self.me.post(f"/api/platform/admins/{support_admin.pk}/sign-out/")

        self.assertEqual(response.data, {"ended": 1})
        self.assertEqual(support.get("/api/platform/me/").status_code, 401)
