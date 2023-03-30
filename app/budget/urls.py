"""
URL mappings for the budget app.
"""
from django.urls import (
    path,
    include,
)

from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers

from budget import views


router = routers.DefaultRouter()
router.register('budget', views.BudgetViewSet)

app_name = 'budget'

urlpatterns = [
    path('', include(router.urls)),
]