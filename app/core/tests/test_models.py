"""
Tests for models 
"""
from unittest.mock import patch

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.conf import settings

from core import models
import json


class ModelTests(TestCase):
    """Test models."""
    def setUp(self):
        pass

    def test_create_user_with_email_successful(self):
        """Test creating a user with an email is successful."""
        email = "test@example.com"
        password = "testpass123"
        user = get_user_model().objects.create_user(
            email=email,
            password=password,
        )

        self.assertEqual(user.email, email)
        self.assertTrue(user.check_password(password))

    def test_new_user_email_normalized(self):
        """Test email is normalized for new users."""
        sample_emails = [
            ['test1@EXAMPLE.com', 'test1@example.com'],
            ['Test2@Example.com', 'Test2@example.com'],
            ['TEST3@EXAMPLE.COM', 'TEST3@example.com'],
            ['test4@example.COM', 'test4@example.com'],
        ]
        for email, expected in sample_emails:
            user = get_user_model().objects.create_user(email, "sample123")
            self.assertEqual(user.email, expected)

    def test_new_user_without_email_raises_error(self):
        """Test that creating a user without email raises error."""
        with self.assertRaises(ValueError):
            get_user_model().objects.create_user('', 'test123')

    def test_create_superuser(self):
        """Test creating a superuser."""
        user = get_user_model().objects.create_superuser(
            'test@example.com',
            'test123',
        )
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)

    def test_create_job(self):
        """Test creating a job is successful."""
        user = get_user_model().objects.create_user(
            'test@example.com',
            'testpass123'
        )
        job = models.Job.objects.create(
            user=user,
            title="Job title",
            description="This is a job"
        )

        self.assertEqual(str(job), job.title)

    def test_job_script_file_path(self):
        """Test generating job path."""
        user = get_user_model().objects.create_user(
            'test@example.com',
            'testpass123'
        )
        job = models.Job.objects.create(
            user=user,
            title="Job title",
            description="This is a job"
        )

        file_path = models.job_script_file_path(job, 'example_script.R')

        self.assertEqual(file_path, f'{settings.BUCKET_PATH}/{job.id}/example_script.R')

    def test_create_run(self):
        """Test creating a run is successful."""
        user = get_user_model().objects.create_user(
            'test@example.com',
            'testpass123'
        )
        job = models.Job.objects.create(
            user=user,
            title="Job title",
            description="This is a job"     
        )
        run = models.Run.objects.create(
            job=job,
        )

        self.assertEqual(run.job, job)


    def test_create_user_creates_budget(self):
        """Creating a new user creates an associated budget instance."""
        email = "test@example.com"
        password = "testpass123"
        user = get_user_model().objects.create_user(
            email=email,
            password=password,
        )
        budget = models.Budget.objects.all().filter(user=user)
        self.assertNotEqual(budget.count(), 0)
        self.assertEqual(budget[0].review, models.Budget.DEFAULT_REVIEW)
        self.assertEqual(budget[0].release, models.Budget.DEFAULT_RELEASE)
