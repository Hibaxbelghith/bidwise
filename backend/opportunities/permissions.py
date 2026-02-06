from rest_framework.permissions import BasePermission, SAFE_METHODS
from users.utils import user_in_group

class IsOrganisationOrReadOnly(BasePermission):
    """
    Une ORGANISATION peut créer/modifier des opportunités.
    Les autres ne peuvent que les voir (READ).
    """
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return request.user.is_authenticated

        return (
            request.user.is_authenticated and (
                user_in_group(request.user, "ORGANISATION") or
                user_in_group(request.user, "ADMIN")
            )
        )


class IsOrganisationOwner(BasePermission):
    """
    Seule l'ORGANISATION qui a créé l'opportunité peut la modifier.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return (
            obj.organisation == request.user or 
            user_in_group(request.user, "ADMIN")
        )

