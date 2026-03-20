from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsAuthenticatedOrReadOnly(BasePermission):
    """
    Read-only requests are public.
    Write operations require authentication.
    """
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated)


class IsOwnerOrReadOnly(BasePermission):
    """
    Object-level: only the creator can modify an opportunity.
    Everyone else gets read-only access.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return obj.organisation == request.user


class IsAdminOrReadOnly(BasePermission):
    """
    Public read access, write access reserved to admin/staff users.
    """

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)

