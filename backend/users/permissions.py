from rest_framework.permissions import BasePermission
from users.utils import user_in_group

class IsAdmin(BasePermission):
    """
    Autorise uniquement les administrateurs de la plateforme
    """
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            user_in_group(request.user, "ADMIN")
        )


class IsOwnerProfile(BasePermission):
    """
    Un utilisateur ne peut accéder qu'à SON profil.
    """
    def has_object_permission(self, request, view, obj):
        # obj est un Profil, on compare avec request.user
        return obj.utilisateur == request.user

class IsAnonyme(BasePermission):
    def has_permission(self, request, view):
        return False