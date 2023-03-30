"""
import environ
import os

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand


class Command(BaseCommand):

    def handle(self, *args, **options):
        env = environ.Env()
        environ.Env.read_env()
        username = env('DJANGO_SUPERUSER_USERNAME')
        email = env('DJANGO_SUPERUSER_EMAIL')
        password = env('DJANGO_SUPERUSER_PASSWORD')

        if not User.objects.filter(username=username).exists():
            print('Creating account for %s (%s)' % (username, email))
            admin = User.objects.create_superuser(
                email=email, username=username, password=password)
        else:
            print('Admin account has already been initialized.')
"""