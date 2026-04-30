from rest_framework import viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend

from .api.services.opportunities import build_opportunity_queryset
from .dataset_metrics import compute_pipeline_metrics
from .filters import OpportuniteFilterSet
from .models import SourceOpportunite
from .pagination import OpportunityPagination, SimilarityPagination
from .permissions import IsAdminOrReadOnly, IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly
from .serializers import OpportuniteSerializer, SimilarOpportunitySerializer, SourceOpportuniteSerializer
from .similarity import find_similar_opportunities_with_fallback
from .source_cleanup import removed_source_q


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def pipeline_metrics_view(request):
    return Response(compute_pipeline_metrics())


class OpportuniteViewSet(viewsets.ModelViewSet):
    serializer_class = OpportuniteSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = OpportuniteFilterSet
    search_fields = ["titre", "description", "organisation_nom", "ville"]
    pagination_class = OpportunityPagination

    ordering_fields = [
        "date_publication",
        "date_limite",
        "date_creation",
    ]

    ordering = ["-date_publication"]
    throttle_classes = [ScopedRateThrottle]

    def get_queryset(self):
        queryset, ordering = build_opportunity_queryset(
            request=self.request,
            action=self.action,
            base_ordering=self.ordering,
        )
        if ordering:
            self.ordering = ordering
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

        similar_items = find_similar_opportunities_with_fallback(
            opportunity=opportunity,
            top_k=top_k,
            queryset=self.get_queryset(),
        )

        # Backward compatibility: keep original list format unless pagination
        # params are explicitly requested.
        if "page" in request.query_params or "page_size" in request.query_params:
            paginator = SimilarityPagination()
            page = paginator.paginate_queryset(similar_items, request)
            serializer = SimilarOpportunitySerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        if not similar_items:
            return Response([])

        return Response(SimilarOpportunitySerializer(similar_items, many=True).data)


class SourceOpportuniteViewSet(viewsets.ModelViewSet):
    queryset = SourceOpportunite.objects.exclude(removed_source_q("nom")).order_by("id")
    serializer_class = SourceOpportuniteSerializer
    permission_classes = [IsAdminOrReadOnly]

class SourceOpportuniteView(APIView):
    authentication_classes = []
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self,request):
        sources = (
            SourceOpportunite.objects.exclude(removed_source_q("nom"))
            .values("id", "nom","type_source")
            .order_by("nom")
        )
        return Response(sources)
