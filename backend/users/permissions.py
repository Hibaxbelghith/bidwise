from rest_framework.permissions import BasePermission


class IsOwnerProfile(BasePermission):
    """
    Un utilisateur ne peut accéder qu'à SON profil.
    """
    def has_object_permission(self, request, view, obj):
        return obj.utilisateur == request.user