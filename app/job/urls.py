"""
URL mappings for the job app.
"""
from django.urls import (
    path,
    include,
)

from rest_framework.routers import DefaultRouter
from rest_framework.routers import re_path
from rest_framework_nested import routers

from job import views


router = routers.DefaultRouter()
router.register('jobs', views.JobViewSet)

runs_router = routers.NestedSimpleRouter(router, 'jobs', lookup='jobs')
runs_router.register('runs', views.RunViewSet, basename='run')


app_name = 'job'

urlpatterns = [
    #path('job/jobs/<uuid:pk>/runs/<int:pk>/', views.RunViewSet.as_view({'patch': 'detail'})),
    path('', include(router.urls)),
    path('', include(runs_router.urls))
]