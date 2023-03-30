"""
Serializers for job APIs.
"""
from rest_framework import serializers

from django.conf import settings

from core.models import Job, Run, Budget
from .permissions import IsEngineOrReadOnly


import uuid
from botocore.exceptions import ClientError

from django.db.models import Sum


class JobSerializer(serializers.ModelSerializer):
    """Serializer for jobs."""
    id = serializers.UUIDField(format='hex', default=uuid.uuid4, read_only=True) 

    class Meta:
        model = Job
        fields = ['id', 'title', 'status']
        read_only_fields = ['id']

#    def get_fields(self):
#        fields = super().get_fields()
#        request = self.context.get('request', None)
#        if request and not IsEngineOrReadOnly().has_permission(request, self):
#            fields['status'].read_only = True
#        return fields


class JobDetailSerializer(JobSerializer):
    """Serializer for job detail view."""

    class Meta(JobSerializer.Meta):
        fields = JobSerializer.Meta.fields + ['description', 'dataset_id', 'script', 'created_at']

#class JobUpdateSerializer(JobSerializer):
#    """Serializer for update run"""
#    class Meta:
#        fields = ['id', 'status' ]
#        read_only = ['id']
""" 
    def __init__(self, instance=None, data=serializers.empty, **kwargs):
        kwargs['partial'] = True
        super().__init__(instance, data, **kwargs)
        self.status_changed = False

        if self.initial_data.get('status') and self.initial_data['status'] != instance.status:
            self.status_changed = True

    def update(self, instance, validated_data):
        # Update fields here
        instance.status = validated_data.get('status', instance.status)

        if self.status_changed:
            # Could notify the front-end somehow?
            pass

        instance.save()
        return instance """
    

class JobScriptSerializer(serializers.ModelSerializer):
    """Serializer for uploading R script to job"""
    script = serializers.FileField()
    id = serializers.UUIDField(format='hex', default=uuid.uuid4, read_only=True) 

    class Meta:
        model = Job
        fields = ['id', 'script']
        read_only_fields = ['id']


class JobSubmitSerializer(serializers.ModelSerializer):
    """Serializer for uploading R script to job"""
    id = serializers.UUIDField(format='hex', default=uuid.uuid4, read_only=True) 

    class Meta:
        model = Job
        fields = ['id']
        read_only_fields = ['id']


class RunSerializer(serializers.ModelSerializer):
    """Serializer for runs."""
    job = JobSerializer(read_only=True)

    class Meta:
        model = Run
        fields = ['job', 'run_id']
        read_only_fields = ['job', 'run_id']


    
class RunDetailSerializer(RunSerializer):
    """Serializer for run detail view."""

    class Meta(RunSerializer.Meta):
        fields = RunSerializer.Meta.fields + ['status','created_at']



class RefineReleaseStatisticSerializer(serializers.Serializer):
    statistic_id = serializers.IntegerField()
    epsilon = serializers.FloatField()


class RefineSerializer(serializers.Serializer):
    refined = RefineReleaseStatisticSerializer(many=True)

    def validate_refined(self, value):
        for refined_statistic in value:
            # TODO: Add more validation
            if refined_statistic['epsilon'] <= 0:
                raise serializers.ValidationError('Epsilon value must be a positive number.')
        return value


class ReleaseSerializer(serializers.Serializer):
    released = RefineReleaseStatisticSerializer(many=True)

    def validate_released(self, value):
        for released_statistic in value:
            # TODO: Add more validation
            if released_statistic['epsilon'] <= 0:
                raise serializers.ValidationError('Epsilon value must be a positive number.')
        return value
