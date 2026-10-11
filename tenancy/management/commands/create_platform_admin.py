"""Create the first Owner, or recover one who lost their authenticator.

    manage.py create_platform_admin --email you@ordo.app --name "Your Name"
    manage.py create_platform_admin --reset-2fa --email you@ordo.app

Later admins are invited from the console. Resetting 2FA is also the way back
in after ``PLATFORM_TOTP_KEY`` is rotated: the admin enrols again at their
next sign in (spec 0003, child 0003).
"""
import getpass

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from tenancy import totp
from tenancy.models import PlatformAdmin


class Command(BaseCommand):
    help = "Create a platform Owner (prompts for the password), or reset an admin's 2FA."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True)
        parser.add_argument("--name", help="Required when creating an admin.")
        parser.add_argument(
            "--reset-2fa",
            action="store_true",
            help="Clear the admin's authenticator so they enrol again at next sign in.",
        )

    def handle(self, *args, email, name, reset_2fa, **options):
        email = email.strip().lower()
        if reset_2fa:
            return self.reset_2fa(email)
        if not name:
            raise CommandError("--name is required when creating an admin.")
        if PlatformAdmin.objects.filter(email__iexact=email).exists():
            raise CommandError(f"A platform admin with email {email} already exists.")

        admin = PlatformAdmin(email=email, name=name, role=PlatformAdmin.Role.OWNER)
        admin.set_password(self.prompt_password(admin))
        admin.save()
        self.stdout.write(
            self.style.SUCCESS(
                f"Created Owner {email}. Sign in at the console to set up two factor sign in."
            )
        )

    def prompt_password(self, admin):
        while True:
            password = getpass.getpass("Password: ")
            if password != getpass.getpass("Password (again): "):
                self.stderr.write("The passwords don't match. Try again.")
                continue
            try:
                validate_password(password, user=admin)
            except ValidationError as exc:
                self.stderr.write("\n".join(exc.messages))
                continue
            return password

    def reset_2fa(self, email):
        admin = PlatformAdmin.objects.filter(email__iexact=email).first()
        if admin is None:
            raise CommandError(f"No platform admin with email {email}.")
        with transaction.atomic():
            totp.clear(admin)
            admin.tokens.all().delete()
        self.stdout.write(
            self.style.SUCCESS(f"Cleared 2FA for {email}. They enrol again at next sign in.")
        )
