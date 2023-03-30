"""
Serializers for budget APIs.
"""

from rest_framework import serializers

from core.models import Budget
from .permissions import IsDataStewardOrReadOnly

class BudgetSerializer(serializers.ModelSerializer):
    """Serializer for jobs."""

    class Meta:
        model = Budget
        fields = ['id', 'review', 'release']
        read_only_fields = ['id']

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get('request', None)
        if request and not IsDataStewardOrReadOnly().has_permission(request, self):
            fields['review'].read_only = True
            fields['release'].read_only = True
        return fields



