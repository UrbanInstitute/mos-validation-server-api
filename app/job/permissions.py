"""
Custom permissions.
"""
from rest_framework import permissions

class IsEngineOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        # Allow safe methods (GET, OPTIONS, HEAD) for any user
        if request.method in permissions.SAFE_METHODS:
            return True

        # Only allow the admin to modify the field
        return request.user.groups.filter(name='engine').exists()


class IsAdminUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.groups.filter(name='admin').exists()

class IsDeveloper(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.groups.filter(name='developer').exists()

class IsResearcher(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.groups.filter(name='researcher').exists()

class IsDataSteward(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.groups.filter(name='datasteward').exists()

class IsEngineUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.groups.filter(name='engine').exists()