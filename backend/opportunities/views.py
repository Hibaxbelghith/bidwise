from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from .filters import OpportuniteFilterSet
from .models import Opportunite, SourceOpportunite, StatutOpportunite
from .pagination import OpportunityPagination
from .permissions import IsAdminOrReadOnly, IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly
from .serializers import OpportuniteSerializer, SimilarOpportunitySerializer, SourceOpportuniteSerializer
from .similarity import find_similar_opportunities
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
    throttle_classes = [ScopedRateThrottle]

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

    def get_throttles(self):
        if self.action == "similar":
            self.throttle_scope = "opportunity_similar"
            return [ScopedRateThrottle()]
        return []

    @action(detail=True, methods=["get"], url_path="similar")
    def similar(self, request, pk=None):
        opportunity = self.get_object()
        top_k = request.query_params.get("k", request.query_params.get("top_k", 5))
        try:
            top_k = int(top_k)
        except (TypeError, ValueError):
            top_k = 5
        top_k = max(1, min(top_k, 50))

        similar_items = find_similar_opportunities(
            opportunity=opportunity,
            top_k=top_k,
            queryset=self.get_queryset(),
        )

        if not similar_items:
            return Response([])

        return Response(SimilarOpportunitySerializer(similar_items, many=True).data)


class SourceOpportuniteViewSet(viewsets.ModelViewSet):
    queryset = SourceOpportunite.objects.all().order_by("id")
    serializer_class = SourceOpportuniteSerializer
    permission_classes = [IsAdminOrReadOnly]
