import os
from django.core.management.base import BaseCommand
from accounts.models import User


class Command(BaseCommand):
    help = 'Create test users from environment variables'

    def handle(self, *args, **options):
        # Create test master
        master_email = os.environ.get('TEST_MASTER_EMAIL')
        master_password = os.environ.get('TEST_MASTER_PASSWORD')

        if master_email and master_password:
            if not User.objects.filter(email=master_email).exists():
                User.objects.create_user(
                    email=master_email,
                    username=master_email.split('@')[0],
                    password=master_password,
                    role=User.Role.MASTER
                )
                self.stdout.write(self.style.SUCCESS(f'Created test master: {master_email}'))
            else:
                self.stdout.write(f'Test master already exists: {master_email}')

        # Create test admin
        admin_email = os.environ.get('TEST_ADMIN_EMAIL')
        admin_password = os.environ.get('TEST_ADMIN_PASSWORD')

        if admin_email and admin_password:
            if not User.objects.filter(email=admin_email).exists():
                User.objects.create_superuser(
                    email=admin_email,
                    username=admin_email.split('@')[0],
                    password=admin_password,
                    role=User.Role.ADMIN
                )
                self.stdout.write(self.style.SUCCESS(f'Created test admin: {admin_email}'))
            else:
                self.stdout.write(f'Test admin already exists: {admin_email}')
