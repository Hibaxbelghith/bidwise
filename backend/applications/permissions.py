from rest_framework.permissions import BasePermission
from users.utils import user_in_group

class IsCandidat(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            user_in_group(request.user, "CANDIDAT")
        )

class IsOwnerCandidature(BasePermission):
    """
    Un utilisateur ne peut accéder qu'à SES candidatures
    """
    def has_object_permission(self, request, view, obj):
        return ( 
            request.user.is_authenticated and  obj.candidat == request.user )