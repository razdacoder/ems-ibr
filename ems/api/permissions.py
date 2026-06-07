from rest_framework import permissions

from ems.models import SystemSettings


class IsAdminStaff(permissions.BasePermission):
    """Mirror the existing @admin_required decorator: requires user.is_staff."""

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_staff)


class IsSuperAdmin(permissions.BasePermission):
    """Super-admin-only: users/roles, generation, settings, constraints, reset."""

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_super_admin)


class IsDataOfficer(permissions.BasePermission):
    """Super admins and data officers: validate/upload and manage data entities."""

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.can_manage_data)


class IsFacultyOfficer(permissions.BasePermission):
    """Super admins and faculty officers: manage faculties."""

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.can_manage_faculties)


class CanManageDepartmentScoped(permissions.BasePermission):
    """Data managers (super admin / data officer) always pass. Department
    officers with a department may write only to objects whose
    ``department_id`` matches their own. Read-only methods are open to any
    authenticated user (queryset filtering happens in the viewset)."""

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        if user.can_manage_data:
            return True
        return bool(user.department_id)

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        if user.can_manage_data:
            return True
        return getattr(obj, "department_id", None) == user.department_id


class IsJobOwnerOrAdmin(permissions.BasePermission):
    """Admins see every BackgroundJob; everyone else sees only what they created."""

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        return user.is_staff or obj.created_by_id == user.id


class UploadsUnlocked(permissions.BasePermission):
    """Block uploads once a timetable has been generated (matches existing logic)."""

    message = (
        "Uploads are locked because a timetable already exists. "
        "Reset the system or enable bulk upload to continue."
    )

    def has_permission(self, request, view):
        if request.method.upper() in ("GET", "HEAD", "OPTIONS"):
            return True
        settings_row = SystemSettings.objects.first()
        if settings_row and settings_row.has_timetable:
            return False
        return True
