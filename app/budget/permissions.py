"""
Permissions for budget app.
"""

from rest_framework import permissions

class IsDataStewardOrReadOnly(permissions.BasePermission):
    """
    Custom permission to allow only data steward users to modify budgets.
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        if request.method in ['PATCH'] and request.user.groups.filter(name='datasteward').exists():
            return True
        return False
