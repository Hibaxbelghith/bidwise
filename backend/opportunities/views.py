from rest_framework import viewsets
from rest_framework.filters import OrderingFilter, SearchFilter

from .filters import OpportuniteFilterSet
from .models import Opportunite, SourceOpportunite, StatutOpportunite
from .pagination import OpportunityPagination
from .permissions import IsAdminOrReadOnly, IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly
from .serializers import OpportuniteSerializer, SourceOpportuniteSerializer
from django_filters.rest_framework import DjangoFilterBackend


class OpportuniteViewSet(viewsets.ModelViewSet):
    serializer_class = OpportuniteSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = OpportuniteFilterSet
    search_fields = ["titre", "description"]
    pagination_class = OpportunityPagination

    ordering_fields = [
        "date_publication",
        "date_limite",
        "date_creation",
    ]

    ordering = ["-date_publication"]

    def get_queryset(self):
        queryset = Opportunite.objects.select_related("source", "organisation").all()

        if self.action == "list":
            statut_param = self.request.query_params.get("statut")
            status_param = self.request.query_params.get("status")
            if not statut_param and not status_param:
                queryset = queryset.filter(statut=StatutOpportunite.ACTIVE)

        return queryset

    def perform_create(self, serializer):
        # Ownership is enforced server-side and never trusted from payload.
        serializer.save(organisation=self.request.user)


class SourceOpportuniteViewSet(viewsets.ModelViewSet):
    queryset = SourceOpportunite.objects.all().order_by("id")
    serializer_class = SourceOpportuniteSerializer
    permission_classes = [IsAdminOrReadOnly]
