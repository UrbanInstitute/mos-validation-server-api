# Generated by Django 4.0.6 on 2023-03-12 05:27

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='run',
            old_name='refined_epsilons',
            new_name='epsilons',
        ),
    ]
