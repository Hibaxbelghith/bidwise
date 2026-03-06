from rest_framework import viewsets
from .models import Opportunite, SourceOpportunite
from .serializers import OpportuniteSerializer, SourceOpportuniteSerializer
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from .permissions import IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly

class OpportuniteViewSet(viewsets.ModelViewSet):
    queryset = Opportunite.objects.filter(statut='ACTIVE')
    serializer_class = OpportuniteSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
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
