"""
Test for job APIs.
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from django.conf import settings

from rest_framework import status
from rest_framework.test import APIClient

import boto3
from moto import mock_s3, mock_stepfunctions
import os
import json

import tempfile

from core.models import (
    Job, job_script_file_path, 
    default_job_status,
    Run
)

from job.serializers import (
    JobSerializer,
    JobDetailSerializer,
)



JOBS_URL = reverse('job:job-list')

def script_upload_url(job_id):
    """Return URL for script upload"""
    return reverse('job:job-upload-script', args=[job_id])


def script_submit_url(job_id):
    """Return URL for script upload"""
    return reverse('job:job-submit', args=[job_id])


def status_update_url(job_id):
    """Return URL for job status update"""
    return reverse('job:job-status-update', args=[job_id])


def detail_url(job_id):
    """Create and return a job detail URL."""
    return reverse('job:job-detail', args=[job_id])

@mock_s3
@mock_stepfunctions
def create_job(user, **params):
    """Create and return a sample job."""
    defaults = {
        'title': 'Sample job title',
        'description': 'Sample job description',
        'link': 'https://s3.us-east-1.amazonaws.com/test-bucket/test-key',
        'status': json.dumps(default_job_status()),
    }
    defaults.update(params)

    job = Job.objects.create(user=user, **defaults)
    return job


def create_user(**params):
    """Create and return new user."""
    return get_user_model().objects.create_user(**params)


class PublicJobAPITests(TestCase):
    """Test unauthenticated API requests."""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test auth is required to call API."""
        res = self.client.get(JOBS_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateJobAPITests(TestCase):
    """Test authenticated API requests."""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user(email='user@example.com', password='test123')
        self.client.force_authenticate(self.user)

    def test_retrieve_jobs(self):
        """Test retrieving a list of jobs."""
        create_job(user=self.user)
        create_job(user=self.user)

        res = self.client.get(JOBS_URL)

        jobs = Job.objects.all().order_by('-id')
        serializer = JobSerializer(jobs, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_job_list_limited_to_user(self):
        """Test list of jobs is limited to authenticated user."""
        other_user = create_user(email='other@example.com', password='password123')
        create_job(user=self.user)
        create_job(user=other_user)

        res = self.client.get(JOBS_URL)

        jobs = Job.objects.filter(user=self.user)
        serializer = JobSerializer(jobs, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_get_job_detail(self):
        """Test get job detail."""
        job = create_job(user=self.user)

        url = detail_url(job.id)
        res = self.client.get(url)

        serializer = JobDetailSerializer(job)
        self.assertEqual(res.data, serializer.data)

    def test_create_job(self):
        """Test creating a job."""
        payload = {
            'title': 'Sample job',
            'description': 'Sample description',
        }
        res = self.client.post(JOBS_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        job = Job.objects.get(id=res.data['id'])
        for k, v in payload.items():
            self.assertEqual(getattr(job, k), v)
        self.assertEqual(job.user, self.user)

    def test_create_job_creates_run(self):
        """Test creating a job creates a default run."""
        payload = {
            'title': 'Sample job',
            'description': 'Sample description',
        }
        res = self.client.post(JOBS_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        job = Job.objects.get(id=res.data['id'])
        self.assertTrue(Run.objects.filter(job=job.id).exists())

    def test_partial_update(self):
        """Test partial update of job."""
        original_link = 'https://s3.us-east-1.amazonaws.com/test-bucket/test-key'
        job = create_job(
            user=self.user,
            title='Sample job title',
            link=original_link,
        )

        payload = {'title': 'New job title'}
        url = detail_url(job.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        job.refresh_from_db()
        self.assertEqual(job.title, payload['title'])
        self.assertEqual(job.link, original_link)
        self.assertEqual(job.user, self.user)

    def test_full_update(self):
        """Test full update of job."""
        job = create_job(
            user=self.user,
            title='Sample job title',
            link='https://s3.us-east-1.amazonaws.com/test-bucket/test-key',
            description='Sample description',
        )

        payload = {
            'title': 'New job title',
            'description': 'New description',
        }

        url = detail_url(job.id)
        res = self.client.put(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        job.refresh_from_db()
        for k, v in payload.items():
            self.assertEqual(getattr(job, k), v)
        self.assertEqual(job.user, self.user)

    def test_update_user_returns_error(self):
        """Test changing the job user results in an error."""
        new_user = create_user(email='user2@example.com', password='test123')
        job = create_job(user=self.user)

        payload = {'user': new_user.id}
        url = detail_url(job.id)
        self.client.patch(url, payload)

        job.refresh_from_db()
        self.assertEqual(job.user, self.user)

    def test_delete_job(self):
        """Test deleting a job successful."""
        job = create_job(user=self.user)

        url = detail_url(job.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Job.objects.filter(id=job.id).exists())

    def test_job_other_users_job_error(self):
        """Test trying to delete other users job gives error."""
        new_user = create_user(email='user2@example.com', password='test123')
        job = create_job(user=new_user)

        url = detail_url(job.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Job.objects.filter(id=job.id).exists())

    def test_patch_status_does_not_change_status(self):
        """Test trying to update job status gives error for users in 
            group Researcher and DataSteward"""
        job = create_job(user=self.user)
        payload = {'status': json.dumps({'ok': False, 'info': 'info', 'errormsg': None})}

        url = detail_url(job.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(Job.objects.filter(id=job.id)[0].status, json.dumps(default_job_status()))



class JobScriptUploadTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = create_user(email='user@example.com', password='test123')
        self.client.force_authenticate(self.user)
        self.job = create_job(self.user)
        Group.objects.get_or_create(name='admin')
        Group.objects.get_or_create(name='researcher')
        Group.objects.get_or_create(name='engine')

    def tearDown(self):
        self.job.script.delete()

    @mock_s3
    def test_upload_script_to_job(self):
        """Test uploading a script to a job."""
        conn = boto3.client("s3", region_name=settings.AWS_S3_REGION_NAME)
        conn.create_bucket(Bucket=settings.AWS_STORAGE_BUCKET_NAME)

        url = script_upload_url(self.job.id)
        with tempfile.NamedTemporaryFile(suffix='.R') as ntf:
            content = b'# This is a mock R script'
            ntf.write(content)
            ntf.seek(0)
            res = self.client.post(url, {'script': ntf}, format='multipart')
        
        # Status code of POST request is 200
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # script is part of response data dictionary
        self.assertIn('script', res.data)
        # object exists in S3 and content length is the same as original
        res3 = conn.get_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=job_script_file_path(self.job, ntf.name))
        self.assertEqual(res3['ContentLength'], len(content))


class EngineJobAPITests(TestCase):
    """Test authenticated API requests."""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user(email='engine@example.com', password='test123')
        group, created = Group.objects.get_or_create(name='engine')
        group.save()
        self.user.groups.add(group)
        self.user.save()

        self.client.force_authenticate(self.user)

    def test_update_status_successful_for_engine(self):
        """Test trying to update job status is successful for engine"""
        new_user = create_user(email='user@example.com', password='test123')
        job = create_job(user=new_user)
        payload = {'status': json.dumps({'ok': False, 'info': 'info', 'errormsg': None})}

        url = detail_url(job.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(json.dumps(Job.objects.filter(id=job.id)[0].status), payload['status'])

"""
class JobSubmitTests(TestCase):

    def setUp(self):
        # Create a test client
        self.client = APIClient()
        self.user = create_user(email='user@example.com', password='test123')
        self.client.force_authenticate(self.user)
        Group.objects.get_or_create(name='admin')
        Group.objects.get_or_create(name='researcher')
        Group.objects.get_or_create(name='engine')

    def tearDown(self):
        pass
""" 
"""
    def test_api_can_call_dispatcher(self):
        #Test calling the dispatcher lambda function.
        payload = {
            "job_id": 1,
            "dataset_name": "cps_00008",
            "script_s3_uri": f's3://sdt-validation-server/scripts/test.R',
            "k": 10,
            "sample_frac": 0.1
        }
        payload = json.dumps(payload).encode()
        # invoke lambda function
        client = boto3.client(
            "lambda", 
            region_name=os.getenv('AWS_S3_REGION_NAME'),
            aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        )
        response = client.invoke(
            FunctionName="sdt-validation-server-dispatcher", 
            InvocationType="DryRun", 
            Payload=payload
        )

        self.assertEqual(response['StatusCode'], status.HTTP_204_NO_CONTENT)
"""
"""
    @mock_lambda
    @mock_s3
    @mock_iam
    def test_submit_job(self):
        conn = boto3.client("s3", region_name=settings.AWS_S3_REGION_NAME)
        conn.create_bucket(Bucket=settings.AWS_STORAGE_BUCKET_NAME)

        iam_client = boto3.client("iam")
        iam_client.create_role()

        lambda_client = boto3.client("lambda", region_name=settings.AWS_S3_REGION_NAME)
        lambda_client.create_function(
            FunctionName="sdt-validation-server-dispatcher",
            Role="arn:aws:iam::123456789012:role/doesnotexist",
            Code={"ZipFile": b"test"}
        )

        job = create_job(user=self.user)

        url = script_upload_url(job.id)
        with tempfile.NamedTemporaryFile(suffix='.R') as ntf:
            content = b'# This is a mock R script'
            ntf.write(content)
            ntf.seek(0)
            res = self.client.post(url, {'script': ntf}, format='multipart')

        url = script_submit_url(job.id)
        
        res = self.client.post(url)
        
        self.assertEqual(res.status_code, status.HTTP_200_OK)

"""
