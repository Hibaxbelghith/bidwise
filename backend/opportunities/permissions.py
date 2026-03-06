from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsAuthenticatedOrReadOnly(BasePermission):
    """
    Any authenticated user can create/modify opportunities.
    Read access requires authentication too.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated


class IsOwnerOrReadOnly(BasePermission):
    """
    Object-level: only the creator can modify an opportunity.
    Everyone else gets read-only access.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return obj.organisation == request.user

