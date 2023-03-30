"""
Tests for Run API.
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from django.conf import settings

from rest_framework import status
from rest_framework.test import APIClient

import boto3
from moto import mock_s3, mock_lambda
import os
import json

from core.models import Job, Run, Result, Budget
from job.serializers import RunSerializer, RunDetailSerializer, ResultSerializer
from .test_job_api import create_job, create_user


def list_url(job_id):
    """Create and return a list run URL."""
    return reverse('job:run-list', args=[job_id])

def detail_url(job_id, run_id):
    """Create and return a list run URL."""
    return reverse('job:run-detail', args=[job_id, run_id])

def result_url(job_id, run_id):
    """Create and return a result URL."""
    return reverse('job:result-list', args=[job_id, run_id])

def release_url(job_id, run_id):
    return reverse('job:result-batch-update', args=[job_id, run_id])

def create_run(job, **params):
    """Create and return a sample job."""
    defaults = {
        'status': {'ok': True, 'info': "submitted"},
    }
    defaults.update(params)

    run = Run.objects.create(job=job, **defaults)

    return run


class PrivateRunAPITests(TestCase):
    """Test authenticated Run API requests."""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user(email='user@example.com', password='test123')
        self.client.force_authenticate(self.user)
        self.job = create_job(user=self.user)

    def test_retrieve_runs(self):
        """Test retrieving a list of runs for a particular job."""
        create_run(job=self.job)
        create_run(job=self.job)

        res = self.client.get(list_url(self.job.id))
    
        runs = Run.objects.filter(job=self.job).order_by('-id')
        serializer = RunSerializer(runs, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_retrieve_runs_of_other_user(self):
        """Test retrieving a list of runs owned by other user fails."""
        other_user = create_user(email='other@example.com', password='test123')
        job = create_job(user=other_user)
        create_run(job=job)
        create_run(job=job)

        res = self.client.get(list_url(job.id))
    
        runs = Run.objects.filter(job=job, job__user=self.user)
        serializer = RunSerializer(runs, many=True)
        
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_get_run_detail(self):
        """Test get run detail."""
        run = create_run(job=self.job)

        url = detail_url(self.job.id, run.id)
        res = self.client.get(url)

        serializer = RunDetailSerializer(run)
        self.assertEqual(res.data, serializer.data)

    def test_update_run_returns_error(self):
        """Test changing the job a run is associated with results in an error."""
        other_job = create_job(user=self.user)
        run = create_run(job=self.job)

        payload = {
            'job': other_job.id, 
        }

        url = detail_url(run.job.id, run.id)
        self.client.patch(url, payload)

        run.refresh_from_db()
        self.assertEqual(run.job.id, self.job.id)

    def test_delete_run(self):
        """Test deleting a run successful."""
        run = create_run(job=self.job)

        url = detail_url(run.job.id, run.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Run.objects.filter(id=run.id).exists())

    def test_delete_other_users_run_error(self):
        """Test trying to delete other users job gives error."""
        new_user = create_user(email='user2@example.com', password='test123')
        job = create_job(user=new_user)
        run = create_run(job=job)

        url = detail_url(run.job.id, run.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Run.objects.filter(id=run.id).exists())


class EngineRunAPITests(TestCase):
    """Test authenticated API requests."""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user(email='user@example.com', password='test123')
        group, created = Group.objects.get_or_create(name='engine')
        group.save()
        self.user.groups.add(group)
        self.user.save()
 
        self.client.force_authenticate(self.user)

    def test_post_result_successful_for_engine(self):
        """Test posting result is successful for engine"""
        new_user = create_user(email='engine@example.com', password='test123')
        job = create_job(user=new_user)
        run = create_run(job=job)
        

        payload = [{
            'statistic_id': 0,
            'MARS': 1.0,
            'var': 'earned_income',
            'statistic': 'mean',
            'term': 1,
            'chi': 231.1666,
            'noise_90': 6438.63,
            'epsilon_value': 0.125,
            'epsilon_n': 0.125,
            'value_sanitized': 6074.14350,
            'n_sanitized': 624.74506,
            'analysis_type': 'table',
            'analysis_name': 'Example Table',
            'released': False,
        },
        {
            'statistic_id': 1,
            'MARS': 1.0,
            'var': 'earned_income',
            'statistic': 'mean',
            'term': 1,
            'chi': 231.1666,
            'noise_90': 6438.63,
            'epsilon_value': 0.125,
            'epsilon_n': 0.125,
            'value_sanitized': 6074.14350,
            'n_sanitized': 624.74506,
            'analysis_type': 'table',
            'analysis_name': 'Example Table',
            'released': False,
        },]
        

        url = result_url(run.job.id, run.id)

        res = self.client.post(url, json.dumps(payload), content_type='application/json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        

    def test_post_result_calculates_cost(self):
        new_user = create_user(email='user2@example.com', password='test123')
        job = create_job(user=new_user)
        run = create_run(job=job)
        review_budget_before = Budget.objects.filter(id=new_user.id)[0].review
        payload = [{
            'statistic_id': 0,
            'MARS': 1.0,
            'var': 'earned_income',
            'statistic': 'mean',
            'term': 1,
            'chi': 231.1666,
            'noise_90': 6438.63,
            'epsilon_value': 0.125,
            'epsilon_n': 0.125,
            'value_sanitized': 6074.14350,
            'n_sanitized': 624.74506,
            'analysis_type': 'table',
            'analysis_name': 'Example Table',
            'released': False,
        },
        {
            'statistic_id': 1,
            'MARS': 1.0,
            'var': 'earned_income',
            'statistic': 'mean',
            'term': 1,
            'chi': 231.1666,
            'noise_90': 6438.63,
            'epsilon_value': 0.125,
            'epsilon_n': 0.125,
            'value_sanitized': 6074.14350,
            'n_sanitized': 624.74506,
            'analysis_type': 'table',
            'analysis_name': 'Example Table',
            'released': False,
        },]

        url = result_url(run.job.id, run.id)
        print(url)
        res = self.client.post(url, json.dumps(payload), content_type='application/json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        review_budget_after = Budget.objects.filter(id=new_user.id)[0].review
        self.assertEqual(review_budget_after+0.5, review_budget_before)
        #self.assertEqual(float(Run.objects.filter(id=run.id)[0].cost), 0.8)


    def test_release_results_successful(self):
        new_user = create_user(email='user2@example.com', password='test123')
        job = create_job(user=new_user)
        run = create_run(job=job)
        release_budget_before = Budget.objects.filter(id=self.user.id)[0].release
        payload = [{
            'statistic_id': 0,
            'MARS': 1.0,
            'var': 'earned_income',
            'statistic': 'mean',
            'term': 1,
            'chi': 231.1666,
            'noise_90': 6438.63,
            'epsilon_value': 0.125,
            'epsilon_n': 0.125,
            'value_sanitized': 6074.14350,
            'n_sanitized': 624.74506,
            'analysis_type': 'table',
            'analysis_name': 'Example Table',
            'released': False,
        },
        {
            'statistic_id': 1,
            'MARS': 1.0,
            'var': 'earned_income',
            'statistic': 'mean',
            'term': 1,
            'chi': 231.1666,
            'noise_90': 6438.63,
            'epsilon_value': 0.125,
            'epsilon_n': 0.125,
            'value_sanitized': 6074.14350,
            'n_sanitized': 624.74506,
            'analysis_type': 'table',
            'analysis_name': 'Example Table',
            'released': False,
        },]

        url = result_url(run.job.id, run.id)
        res = self.client.post(url, json.dumps(payload), content_type='application/json')
        data = json.loads(res.content)
        payload = [{'id': data[0]['id'], 'released': True},]
        url = release_url(run.job.id, run.id)
        res = self.client.put(url, json.dumps(payload), content_type='application/json')
        print(res.content)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        release_budget_after = Budget.objects.filter(id=self.user.id)[0].release
        self.assertEqual(release_budget_after+0.25, release_budget_before)
        #self.assertEqual(float(Run.objects.filter(id=run.id)[0].cost), 0.8)
