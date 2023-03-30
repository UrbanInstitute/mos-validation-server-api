"""
Database models.
"""
import uuid
import os
import json
import boto3

from django.db.models.signals import post_save, pre_save
from django.db.models import Sum
from django.dispatch import receiver
from django.db import models
from django.shortcuts import get_object_or_404

from django.contrib.auth.models import (
    AbstractBaseUser, 
    BaseUserManager, 
    PermissionsMixin,
    Group
)
from django.conf import settings

from rest_framework.response import Response
from rest_framework import status

from botocore import exceptions

def trigger_engine(instance):
    run = instance

    event = {
        "job_id": str(run.job.id),
        "run_id": run.run_id,
        "user_email": run.job.user.email,
        "dataset_id": run.job.dataset_id,
        "script_path": f's3://{settings.AWS_STORAGE_BUCKET_NAME}/{run.job.script}',
        "k": 10,
        "sample_frac": 0.1,
    }
            
    try:
        # invoke engine
        client = boto3.client(
            "stepfunctions", 
            region_name = os.getenv('AWS_S3_REGION_NAME'),
            aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        )

        response = client.start_execution(
            stateMachineArn = settings.AWS_STEPFUNCTION,
            name = str(event['job_id']),
            input = json.dumps(event),
            #InvocationType="DryRun"
        )
        return Response(response, status=status.HTTP_200_OK)
    except exceptions.ClientError as e:
        error_response = e.response
        #error_code = error_response['Error']['Code']
        error_message = error_response['Error']['Message']
        return Response({'error': error_message}, status=status.HTTP_400_BAD_REQUEST)


def job_script_file_path(instance, filename):
    """Generate s3 path for new job script."""
    foldername = f'{instance.id}'
    print(filename)
    path = os.path.join(settings.BUCKET_PATH, foldername, 'script', os.path.basename(filename))
    print(path)
    return path
    #return os.path.basename(filename)

def default_job_status():
    return {'ok': True, 'info': 'job created', 'errormsg': None}

def default_run_name(instance):
    index = models.Run.objects.filter(id=instance.job.id).count()
    return f'{instance.job.title}_{index}'


class Epsilon:
    def __init__(self, statistic_id, epsilon):
        self.statistic_id = statistic_id
        self.epsilon = epsilon


class UserManager(BaseUserManager):
    """Manager for users."""

    def create_user(self, email, password=None, **extra_fields):
        """Creates, saves and return a new user"""
        default_group, created = Group.objects.get_or_create(name='researcher')
        if not email:
            raise ValueError('Users must have an email address')
        user = self.model(email=self.normalize_email(email), **extra_fields)
        user.set_password(password)
        user.save()
        user.groups.add(default_group)
        user.save()


        return user

    def create_superuser(self, email, password):
        """Creates and saves a new super user"""
        user = self.create_user(email, password)
        user.is_staff = True
        user.is_superuser = True
        user.save()

        return user
    



class User(AbstractBaseUser, PermissionsMixin):
    """Custom user model that supports using email instead of username"""
    email = models.EmailField(max_length=255, unique=True)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(blank=True, null=True, verbose_name='date joined')
    groups = models.ManyToManyField('auth.Group', related_name='users', blank=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'


    def save(self, *args, **kwargs):
        created = not self.id
        super(User, self).save(*args, **kwargs)
        if created:
            self.refresh_from_db()
            Budget.objects.create(user=self)



class Job(models.Model):
    """Job object."""
    DATASET_CHOICES = [
        ("cps_00008", "CPS2008"),
        ("puf_2012", "PUF2012"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.JSONField(default=default_job_status)
    created_at = models.DateTimeField(auto_now=True)
    script = models.FileField(null=True, upload_to=job_script_file_path)
    dataset_id = models.CharField(max_length=32, choices=DATASET_CHOICES, blank=False)
    max_epsilon = models.JSONField(default=None, null=True)

    def save(self, *args, **kwargs):
        create_run = self._state.adding
        if create_run:
            # Object is new, so set the upload_to path after saving
            saved_script = self.script
            self.script = None
            super().save(*args, **kwargs)
            self.script = saved_script
            if 'force_insert' in kwargs:
                kwargs.pop('force_insert')

        super().save(*args, **kwargs)

        if create_run:
            Run.objects.create(job=self)

    def get_epsilon_for_index(self, array, index):
        for i in range(len(array)):
            if array[i]['statistic_id'] == index:
                return array[i]['epsilon_value']
        return None

    def __str__(self):
        return self.title




class Run(models.Model):
    """Run object."""
    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE
    )
    run_id = models.PositiveIntegerField()

    compute_sensitivities = models.BooleanField(default=True)
    epsilons = models.JSONField(default=dict) #not needed
    status = models.JSONField(default=dict)
    released_ids = models.TextField()
    created_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('job', 'run_id')
        ordering = ('job', 'run_id')

    def __str__(self):
        return self.name
    
    def get_released_ids(self):
        return json.loads(self.released_ids)

    def add_released_ids(self, values):
        existing_set = set(self.released_ids)
        for item in values:
            if item not in existing_set:
                self.released_ids.append(item)
                existing_set.add(item)

    def compute_release_cost(self, epsilons):
        cost = 0
        for item in epsilons:
            if item['statistic_id'] not in self.release_ids:
                cost = cost + item['epsilon']
        return cost


    def save(self, *args, **kwargs):
        if self.id is None: # object is being created
            print("creating new run")
            last_id = Run.objects.filter(job=self.job).order_by('-run_id').values_list('run_id', flat=True).first()
            self.run_id = 1 if last_id is None else last_id + 1
            # determine if sensitivities need to be computed
            if self.run_id > 1:
                self.compute_sensitivities = False
            else:
                # charge default epsilon for first run
                budget = Budget.objects.filter(user=self.job.user)[0]
                budget.charge_review_budget(1)
        super(Run, self).save(*args, **kwargs)

@receiver(post_save, sender=Run)
def submit_run(sender, instance, created, **kwargs):
    if created:
        trigger_engine(instance)


class Budget(models.Model):
    DEFAULT_REVIEW = 100
    DEFAULT_RELEASE = 100
    """Budget object."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    review = models.FloatField(null=False, default=DEFAULT_REVIEW)
    release = models.FloatField(null=False, default=DEFAULT_RELEASE)

    def charge_review_budget(self, cost):
        """Update the user's budget."""
        self.review = self.review - cost
        self.save()

    def charge_release_budget(self, cost):
        """Update the user's release budget."""
        self.release = self.release - cost
        self.save()

