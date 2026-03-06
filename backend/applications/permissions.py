from rest_framework.permissions import BasePermission


class IsOwnerCandidature(BasePermission):
    """
    Un utilisateur ne peut accéder qu'à SES candidatures.
    """
    def has_object_permission(self, request, view, obj):
        return request.user.is_authenticated and obj.candidat == request.user