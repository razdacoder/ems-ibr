from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
import os

User = get_user_model()


class Command(BaseCommand):
    help = 'Create superusers automatically'

    def handle(self, *args, **options):
        # Define 3 superusers with default credentials
        superusers = [
            {
                'email': os.environ.get('DJANGO_SUPERUSER_EMAIL_1', 'rasheed@ems.com'),
                'first_name': os.environ.get('DJANGO_SUPERUSER_FIRSTNAME_1', 'Rasheed'),
                'last_name': os.environ.get('DJANGO_SUPERUSER_LASTNAME_1', 'Ramon'),
                'password': os.environ.get('DJANGO_SUPERUSER_PASSWORD_1', 'Niniola12')
            },
            {
                'email': os.environ.get('DJANGO_SUPERUSER_EMAIL_2', 'dara@ems.com'),
                'first_name': os.environ.get('DJANGO_SUPERUSER_FIRSTNAME_2', 'Fortunatus'),
                'last_name': os.environ.get('DJANGO_SUPERUSER_LASTNAME_2', 'Adegoke'),
                'password': os.environ.get('DJANGO_SUPERUSER_PASSWORD_2', 'Dara12345')
            },
            {
                'email': os.environ.get('DJANGO_SUPERUSER_EMAIL_3', 'admin@ems.com'),
                'first_name': os.environ.get('DJANGO_SUPERUSER_FIRSTNAME_3', 'Esther'),
                'last_name': os.environ.get('DJANGO_SUPERUSER_LASTNAME_3', 'Oduntan'),
                'password': os.environ.get('DJANGO_SUPERUSER_PASSWORD_3', 'esther12345')
            }
        ]

        for i, superuser_data in enumerate(superusers, 1):
            email = superuser_data['email']
            
            # Check if superuser already exists
            if User.objects.filter(email=email).exists():
                self.stdout.write(
                    self.style.WARNING(f'Superuser {i} "{email}" already exists.')
                )
                continue

            # Create superuser
            try:
                User.objects.create_superuser(
                    email=email,
                    first_name=superuser_data['first_name'],
                    last_name=superuser_data['last_name'],
                    password=superuser_data['password']
                )
                self.stdout.write(
                    self.style.SUCCESS(f'Superuser {i} "{email}" created successfully.')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error creating superuser {i}: {e}')
                )
