import logging
import time

from django.conf import settings
from django.db import connection
from rest_framework import viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from django_filters.rest_framework import DjangoFilterBackend

from .api.services.facets import get_cached_opportunity_facets
from .api.services.opportunities import build_opportunity_queryset
from .dataset_metrics import compute_pipeline_metrics
from .filters import OpportuniteFilterSet
from .models import SourceOpportunite
from .pagination import OpportunityPagination, SimilarityPagination
from .permissions import IsAdminOrReadOnly, IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly
from .serializers import OpportuniteSerializer, SimilarOpportunitySerializer, SourceOpportuniteSerializer
from .similarity import find_similar_opportunities_with_fallback
from .source_cleanup import removed_source_q


logger = logging.getLogger(__name__)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def pipeline_metrics_view(request):
    return Response(compute_pipeline_metrics())


class OpportuniteViewSet(viewsets.ModelViewSet):
    serializer_class = OpportuniteSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = OpportuniteFilterSet
    pagination_class = OpportunityPagination

    ordering_fields = [
        "quality_score",
        "date_publication",
        "date_limite",
        "date_creation",
    ]

    ordering = ["-quality_score", "-date_publication", "-id"]
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

    def _attach_performance_headers(self, response, *, started_at, initial_query_count):
        elapsed_ms = (time.perf_counter() - started_at) * 1000
        query_count = max(0, len(connection.queries) - initial_query_count)
        response["X-BidWise-Query-Time-Ms"] = f"{elapsed_ms:.1f}"
        if query_count:
            response["X-BidWise-Query-Count"] = str(query_count)

        slow_threshold_ms = float(getattr(settings, "OPPORTUNITY_SLOW_QUERY_MS", 250))
        log_payload = {
            "path": self.request.path,
            "query_params": dict(self.request.query_params),
            "elapsed_ms": round(elapsed_ms, 1),
            "query_count": query_count,
        }
        if elapsed_ms >= slow_threshold_ms:
            logger.warning("Slow opportunity API query", extra=log_payload)
        else:
            logger.debug("Opportunity API query", extra=log_payload)
        return response

    def list(self, request, *args, **kwargs):
        started_at = time.perf_counter()
        initial_query_count = len(connection.queries)

        queryset = self.filter_queryset(self.get_queryset())
        facets = get_cached_opportunity_facets(queryset, request.query_params)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            response.data["facets"] = facets
            return self._attach_performance_headers(
                response,
                started_at=started_at,
                initial_query_count=initial_query_count,
            )

        serializer = self.get_serializer(queryset, many=True)
        response = Response({"count": len(serializer.data), "results": serializer.data, "facets": facets})
        return self._attach_performance_headers(
            response,
            started_at=started_at,
            initial_query_count=initial_query_count,
        )

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

    @action(detail=False, methods=["get"], url_path="facets")
    def facets(self, request):
        started_at = time.perf_counter()
        initial_query_count = len(connection.queries)
        queryset = self.filter_queryset(self.get_queryset())
        facets = get_cached_opportunity_facets(queryset, request.query_params)
        response = Response({"count": queryset.order_by().count(), "facets": facets})
        return self._attach_performance_headers(
            response,
            started_at=started_at,
            initial_query_count=initial_query_count,
        )


class SourceOpportuniteViewSet(viewsets.ModelViewSet):
    queryset = SourceOpportunite.objects.exclude(removed_source_q("nom")).order_by("id")
    serializer_class = SourceOpportuniteSerializer
    permission_classes = [IsAdminOrReadOnly]
