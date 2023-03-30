"""
Views for the budget APIs.
"""
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from knox.auth import TokenAuthentication

from budget import serializers
from core.models import Run, Budget
from .permissions import IsDataStewardOrReadOnly


class BudgetViewSet(viewsets.ModelViewSet):
    """View for manage budget APIs."""
    serializer_class = serializers.BudgetSerializer
    queryset = Budget.objects.all()
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated, IsDataStewardOrReadOnly]

    def get_queryset(self):
        """Retrieve budget for authenticated user."""
        if self.request.user.groups.filter(name='datasteward').exists():
            return self.queryset
        else:
            return self.queryset.filter(user=self.request.user)



