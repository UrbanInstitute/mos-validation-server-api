"""
Django command to create the user groups in the database.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group


class Command(BaseCommand):
    help = 'Create User Groups'

    def handle(self, *args, **options):
        self.create_user_group('admin')
        self.create_user_group('researcher')
        self.create_user_group('datasteward')
        self.create_user_group('developer')
        self.create_user_group('engine')

    def create_user_group(self, name):
        group, created = Group.objects.get_or_create(name=name)
        if created:
            self.stdout.write(self.style.SUCCESS(f'Successfully created group "{group}"!'))
        else:
            self.stdout.write(self.style.WARNING(f'Group "{group}" already exists.'))
