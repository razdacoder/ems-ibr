"""Console roles (spec 0003, child 0003, role matrix).

Support may look after schools; only an Owner may create, delete, change
commercial terms or manage platform admins.
"""
from rest_framework.permissions import BasePermission

from tenancy.models import PlatformAdmin


class IsPlatformStaff(BasePermission):
    """Any active platform admin, Owner or Support."""

    def has_permission(self, request, view):
        user = request.user
        return isinstance(user, PlatformAdmin) and user.is_active


class IsPlatformOwner(IsPlatformStaff):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.is_owner
