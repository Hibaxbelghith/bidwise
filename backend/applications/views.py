from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Candidature
from .serializers import CandidatureSerializer
from .permissions import IsOwnerCandidature


class CandidatureViewSet(viewsets.ModelViewSet):
    serializer_class = CandidatureSerializer
    permission_classes = [IsAuthenticated, IsOwnerCandidature]

    def get_queryset(self):
        """
        Un utilisateur ne voit que SES candidatures
        """
        return Candidature.objects.filter(
            candidat=self.request.user
        ).order_by("-date_creation", "-id")

    def perform_create(self, serializer):
        """
        Le candidat est automatiquement l'utilisateur connecté
        """
        serializer.save(candidat=self.request.user)
