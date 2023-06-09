"""
Django command to wait for the database to be available.
"""


import time
from django.db import connection
from django.db.utils import OperationalError
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """ Django command to wait for database"""

    def handle(self, *args, **options):
        """ Entrypoint for command"""
        self.stdout.write('Waiting for database...')
        db_up = False
        error = []
        while db_up is False:
            try:
                connection.ensure_connection()
                db_up = True
            except OperationalError as e:
                self.stdout.write(f'{e} Database unavailable, waiting 1 second...')
                time.sleep(1)

        self.stdout.write(self.style.SUCCESS('Database available!'))
