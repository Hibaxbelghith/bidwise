from rest_framework.permissions import BasePermission


class IsSuspensionNotBlocked(BasePermission):
    """
    Prevent suspended users from accessing authenticated endpoints.
    Applies to all authenticated endpoints (user-facing and admin).
    Returns 403 Forbidden for suspended users.
    """
    def has_permission(self, request, view):
        user = request.user
        # Let unauthenticated through (other permissions handle auth)
        if not user or not user.is_authenticated:
            return True
        # Block suspended users
        if getattr(user, "is_suspended", False):
            return False
        return True


class IsOwnerProfile(BasePermission):
    """
    Un utilisateur ne peut accéder qu'à SON profil.
    """
    def has_object_permission(self, request, view, obj):
        return obj.utilisateur == request.user


class IsAdminUser(BasePermission):
    """
    Allow access to authenticated BidWise admin users.
    Note: Suspension check is applied via IsSuspensionNotBlocked permission.
    """
    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and getattr(user, "is_admin", False)
        )
