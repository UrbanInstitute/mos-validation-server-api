"""
Tests for Budget API.
"""
from django.urls import reverse
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from rest_framework import status
from rest_framework.test import APIClient

import json
from moto import mock_s3, mock_stepfunctions

from core.models import Job, default_job_status, Budget
from budget.serializers import BudgetSerializer


BUDGET_URL = reverse('budget:budget-list')

def detail_url(user_id):
    """Create and return a budget detail URL."""
    return reverse('budget:budget-detail', args=[user_id])



@mock_stepfunctions
@mock_s3
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



class PublicBudgetAPITests(TestCase):
    """Test unauthenticated API requests."""
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test auth is required to call API."""
        res = self.client.get(BUDGET_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
   


class PrivateBudgetAPITests(TestCase):
    """Test authenticated API requests."""
    def setUp(self):
        self.client = APIClient()
        self.user = create_user(email='user@example.com', password='test123')
        self.client.force_authenticate(self.user)
        self.job = create_job(self.user)


    def test_retrieve_budget(self):
        """Test retrieving a user's budget."""
        
        res = self.client.get(BUDGET_URL)

        budget = Budget.objects.all().filter(user=self.user)
        serializer = BudgetSerializer(budget, many=True)
        print(serializer.data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_retrieve_list_limited_to_user(self):
        """Test retrieving budget is limited to authenticated user."""
        create_user(email='other@example.com', password='password123')
    
        res = self.client.get(BUDGET_URL)

        budget = Budget.objects.filter(user=self.user)
        serializer = BudgetSerializer(budget, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_user_cannot_write_to_budget(self):
        """Test that user cannot change the budget"""
        payload = {'review': 150, 'release': 200}

        url = detail_url(self.user.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class DataStewardBudgetAPITests(TestCase):
    """Test authenticated API requests."""
    def setUp(self):
        self.client = APIClient()
        self.user = create_user(email='user@example.com', password='test123')
        group, created = Group.objects.get_or_create(name='datasteward')
        group.save()
        group.refresh_from_db()
        self.user.groups.add(group)
        self.user.save()
        self.user.refresh_from_db()
        print(f'groups = {self.user.groups.all()}')
        print(group)
        print(self.user)

        self.client.force_authenticate(self.user)


    def test_datasteward_can_patch_budget(self):
        """Test that datasteward can change other users budget"""
        other_user = create_user(email='other_user@example.com', password='test125')

        payload = {'review': 150, 'release': 200}

        url = detail_url(other_user.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        budgets = Budget.objects.all()
        print(f"{budgets[0].user.id}, {budgets[0].review}, {budgets[0].release}")
        print(f"{budgets[1].user.id}, {budgets[1].review}, {budgets[1].release}")
        
        self.assertEqual(Budget.objects.filter(id=other_user.id)[0].review, 150)
        self.assertEqual(Budget.objects.filter(id=other_user.id)[0].release, 200)
