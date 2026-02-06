from rest_framework import viewsets
from .models import Opportunite, SourceOpportunite
from .serializers import OpportuniteSerializer, SourceOpportuniteSerializer
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from .permissions import IsOrganisationOrReadOnly, IsOrganisationOwner

class OpportuniteViewSet(viewsets.ModelViewSet):
    queryset = Opportunite.objects.filter(statut='ACTIVE')
    serializer_class = OpportuniteSerializer
    #Lecture pour tous les utilisateurs authentifiés, écriture uniquement pour les organisations
    permission_classes = [IsOrganisationOrReadOnly, IsOrganisationOwner]
    filter_backends = [DjangoFilterBackend, OrderingFilter]

    filterset_fields = [
        'type_opportunite',
        'statut',
        'source',
    ]

    ordering_fields = [
        'date_publication',
        'date_limite',
        'date_creation',
    ]

    ordering = ['-date_publication']



class SourceOpportuniteViewSet(viewsets.ModelViewSet):
    queryset = SourceOpportunite.objects.all()
    serializer_class = SourceOpportuniteSerializer
