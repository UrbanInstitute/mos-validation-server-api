"""
Views for the job APIs.
"""
from rest_framework import viewsets, status, parsers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.shortcuts import get_object_or_404


import boto3
from botocore.exceptions import ClientError

from django.conf import settings
from django.db.models import Sum, Q

from knox.auth import TokenAuthentication

from app.schema import KnoxTokenScheme # needed, do not delete

from core.models import Job, Run, Budget
from job import serializers
from job.util import *
from .permissions import IsAdminUser, IsResearcher, IsEngineUser

import json
import os
import csv
import io
from django.http import HttpResponse



class JobViewSet(viewsets.ModelViewSet):
    """View for manage job APIs."""
    serializer_class = serializers.JobDetailSerializer
    queryset = Job.objects.all()
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Retrieve jobs for authenticated user."""
        if self.request.user.groups.filter(name='engine').exists():
            return self.queryset
        else:
            return self.queryset.filter(user=self.request.user).order_by('-id')

    def get_serializer_class(self):
        """Return the serializer class for request."""
        if self.action == 'list':
            return serializers.JobSerializer
        elif self.action == 'upload_script':
            return serializers.JobScriptSerializer
        elif self.action == "submit":
            return serializers.JobSubmitSerializer
        
        return self.serializer_class

    def perform_create(self, serializer):
        """Create a new job."""
        serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        # Check if the condition is true
        budget = Budget.objects.filter(user=request.user)[0]
        if not budget.review >= 1:
            return Response({'error': 'Insufficient budget'}, status=status.HTTP_400_BAD_REQUEST)

        # Condition is true, proceed with object creation
        return super().create(request, *args, **kwargs)

    def list(self, request):
        queryset = self.get_queryset()
        serializer = serializers.JobSerializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        item = get_object_or_404(self.queryset, pk=pk)
        serializer = serializers.JobDetailSerializer(item)
        return Response(serializer.data)

    @action(methods=['POST'], detail=True, url_path='upload-script')
    def upload_script(self, request, pk=None):
        """Upload a script to a job"""
        job = self.get_object()
        serializer = self.get_serializer(
            job,
            data=request.data
        )

        if serializer.is_valid():
            serializer.save()
            return Response(
                serializer.data,
                status=status.HTTP_200_OK
            )
        
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )
        

class RunViewSet(viewsets.ModelViewSet):
    """View for manage run APIs."""
    serializer_class = serializers.RunDetailSerializer
    queryset = Run.objects.all()
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    lookup_field = ('run_id')

    def get_queryset(self):
        """Retrieve jobs for authenticated user."""
        if self.request.user.groups.filter(name='engine').exists():
            return self.queryset.filter(job=self.kwargs['jobs_pk']).order_by('-id')
        else:
            return Run.objects.filter(job=self.kwargs['jobs_pk'], job__user=self.request.user).order_by('-id')

    def get_serializer_class(self):
        """Return the serializer class for request."""
        if self.action == 'list':
            return serializers.RunSerializer
        
        return self.serializer_class
    
    def partial_update(self, request, *args, **kwargs):
        instance = self.queryset.get(job=kwargs.get('jobs_pk'),run_id=kwargs.get('run_id'))
        serializer = self.serializer_class(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        #serializer.validated_data['cost'] = compute_cost(request.data['epsilon'], instance.job.max_epsilon)
        # send signal to update_review_budget

        serializer.save()
        return Response(serializer.data)

    def retrieve(self, request, jobs_pk=None, run_id=None)   :
        job = get_object_or_404(Job, id=jobs_pk)
        item = get_object_or_404(self.queryset, job=job, run_id=run_id)
        serializer = serializers.RunDetailSerializer(item)
        return Response(serializer.data) 
    
    @action(methods=['GET'], detail=True, url_path='get-csv-results')
    def get_csv_results(self, request, jobs_pk=None, run_id=None):
        # Set up S3 client
        s3 = boto3.client('s3', aws_access_key_id=settings.AWS_ACCESS_KEY_ID, aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)

        # Set up S3 bucket and file details
        bucket_name = settings.AWS_STORAGE_BUCKET_NAME
        file_key = os.path.join('submissions',jobs_pk,f'sanitized_output_{run_id}.csv')

        print(file_key)
        # Retrieve the file from S3
        try:
            response = s3.get_object(Bucket=bucket_name, Key=file_key)
            file_content = response['Body'].read().decode('utf-8')  # Decode the CSV file content
        except ClientError as e:
            return HttpResponse(f"Error retrieving file: {str(e)}", status=500)

        # Set the response headers to indicate a CSV file download
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_key)}"'

        # Write the CSV file content to the response
        writer = csv.writer(response)
        for line in file_content.splitlines():
            writer.writerow(line.split(','))

        return response


    @action(methods=['POST'], detail=True, url_path='refine')
    def refine(self, request, jobs_pk=None, run_id=None):
        """Endpoint that accepts refined epsilon values for statistics"""
        job = get_object_or_404(Job, id=jobs_pk)
    
        # Validate payload
        serializer = serializers.RefineSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        refined_statistics = serializer.validated_data['refined']

        # Compute cost
        cost = compute_cost(refined_statistics)
        print(f"cost={cost}")


        # Check budget
        budget = Budget.objects.filter(user=request.user)[0]
        if budget.review < cost:
            return Response({'error': 'Insufficient budget'}, status=status.HTTP_403_FORBIDDEN)
        print(f"review_budget = {budget.review}")
        
        # Create new run
        run = Run.objects.create(job=job)

        # Trigger sanitizer
        response = trigger_sanitizer(run, refined_statistics)
        print(response)
        # Charge user
        if response.status_code == status.HTTP_200_OK:
            Budget.objects.filter(user=request.user)[0].charge_review_budget(cost)

        return response

    
    @action(methods=['POST'], detail=True, url_path='release')
    def release(self, request, jobs_pk=None, run_id=None):
        # Validate payload
        serializer = serializers.ReleaseSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        released_statistics = serializer.validated_data['released']
        release_id_list = [item["statistic_id"] for item in released_statistics]

        # enough release budget?
        budget = get_object_or_404(Budget, user=request.user)
        run = get_object_or_404(Run, job=jobs_pk, run_id=run_id)
        cost = run.compute_release_cost(released_statistics)
        #pre_calc_cost = sum([item["epsilon"] for item in released_statistics])
        print(cost)
        if budget.release < cost:
            return Response({'error': 'Insufficient budget'}, status=status.HTTP_403_FORBIDDEN)

        # Set up S3 client
        s3 = boto3.client('s3', aws_access_key_id=settings.AWS_ACCESS_KEY_ID, aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)

        # Set up S3 bucket and file details
        bucket_name = settings.AWS_STORAGE_BUCKET_NAME
        file_key = os.path.join('output',jobs_pk,f'sanitized_output_{run_id}.csv')

        print(file_key)
        # Retrieve the file from S3
        try:
            response = s3.get_object(Bucket=bucket_name, Key=file_key)
            file_content = response['Body'].read().decode('utf-8')  # Decode the CSV file content
        except ClientError as e:
            return HttpResponse(f"Error retrieving file: {str(e)}", status=500)

        # Set the response headers to indicate a CSV file download
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_key)}"'

        # Write the CSV file content to the release folder
        output_buffer = io.StringIO()
        writer = csv.writer(output_buffer)
        line_num = 1
        for csv_line in file_content.splitlines():
            # Header
            if line_num == 1:
                col_list = csv_line.split(',')
                statistic_id_index = col_list.index("statistic_id")
                epsilon_index = col_list.index("epsilon")
                writer.writerow(csv_line)
            else:
                value_list = csv_line.split(',')
                statistic_id = int(value_list[statistic_id_index])
                if statistic_id in release_id_list:
                    writer.writerow(csv_line)
            line_num = line_num + 1


        now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_file_key = os.path.join('output',jobs_pk,f'release_{run_id}_{now}.csv')
        upload_csv_to_s3(output_buffer, output_file_key)

        presigned_url = create_presigned_url(output_file_key)
        print(presigned_url)

        send_email_to_user(presigned_url, request.user)

        # charge user
        budget.charge_release_budget(cost)
        run.add_released_ids(release_id_list)
        
        return response