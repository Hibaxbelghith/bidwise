from rest_framework.permissions import BasePermission


class IsOwnerProfile(BasePermission):
    """
    Un utilisateur ne peut accéder qu'à SON profil.
    """
    def has_object_permission(self, request, view, obj):
        return obj.utilisateur == request.user


class IsAdminUser(BasePermission):
    """
    Allow access to authenticated BidWise admin users.
    """
    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and getattr(user, "is_admin", False)
        )
