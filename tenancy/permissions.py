"""Console roles (spec 0003, child 0003, role matrix), and plan features
on school hosts (child 0005).

Support may look after schools; only an Owner may create, delete, change
commercial terms or manage platform admins.
"""
from rest_framework.permissions import BasePermission

from tenancy import limits
from tenancy.models import PlatformAdmin


class IsPlatformStaff(BasePermission):
    """Any active platform admin, Owner or Support."""

    def has_permission(self, request, view):
        user = request.user
        return isinstance(user, PlatformAdmin) and user.is_active


class IsPlatformOwner(IsPlatformStaff):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.is_owner


def requires_feature(key):
    """A permission that refuses with 403 ``feature_disabled`` when the
    school's plan leaves ``key`` off. Append it to a view's own
    ``permission_classes``, after the role checks."""

    class RequiresFeature(BasePermission):
        def has_permission(self, request, view):
            limits.assert_feature(key)
            return True

    RequiresFeature.__name__ = f"Requires_{key}"
    return RequiresFeature
