#!/bin/bash

set -e

#echo "Running wait_for-db command..."
python manage.py wait_for_db
echo "Running collectstatic command...."
python manage.py collectstatic --noinput
#echo "Running makemigration command..."
#python manage.py makemigrations
echo "Running migrate command..."
python manage.py migrate
# python manage.py createsuperuser --noinput --username $DJANGO_SUPERUSER_USERNAME --email $DJANGO_SUPERUSER_EMAIL --password $DJANGO_SUPERUSER_PASSWORD


uwsgi --socket :9000 --workers 4 --master --enable-threads --module app.wsgi