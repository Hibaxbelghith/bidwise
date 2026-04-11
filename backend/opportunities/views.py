from rest_framework import viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from django.db import connection
from django.db.models import Case, F, IntegerField, Value, When, Window
from django.db.models.functions import RowNumber

from .dataset_metrics import compute_pipeline_metrics
from .filters import OpportuniteFilterSet
from .models import Opportunite, SourceOpportunite, StatutOpportunite, TypeOpportunite
from .pagination import OpportunityPagination, SimilarityPagination
from .permissions import IsAdminOrReadOnly, IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly
from .serializers import OpportuniteSerializer, SimilarOpportunitySerializer, SourceOpportuniteSerializer
from .similarity import find_similar_opportunities_with_fallback
from django_filters.rest_framework import DjangoFilterBackend


DEFAULT_LIST_PER_SOURCE_CAP = 250
HIINTERNS_STAGE_MIN_QUALITY_SCORE = 0.85


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def pipeline_metrics_view(request):
    return Response(compute_pipeline_metrics())


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
            effective_status = str(statut_param or status_param or "").strip().upper()
            if not statut_param and not status_param:
                queryset = queryset.filter(statut=StatutOpportunite.ACTIVE)

            # Keep HiInterns in feed, but only with strict quality for internships.
            if not effective_status or effective_status == StatutOpportunite.ACTIVE:
                queryset = queryset.exclude(
                    source__nom="HiInterns",
                    type_opportunite=TypeOpportunite.STAGE,
                    quality_score__lte=HIINTERNS_STAGE_MIN_QUALITY_SCORE,
                )

            source_param = self.request.query_params.get("source")
            diversify_param = str(self.request.query_params.get("diversify_sources", "1")).strip().lower()
            source_cap_param = self.request.query_params.get("source_cap")
            diversify_enabled = diversify_param not in {"0", "false", "no", "off"}
            type_param = str(self.request.query_params.get("type_opportunite", "")).strip().upper()
            stage_requested = type_param == TypeOpportunite.STAGE

            if stage_requested and not source_param:
                queryset = queryset.annotate(
                    _stage_source_priority=Case(
                        When(source__nom="Keejob", then=Value(0)),
                        When(source__nom="HiInterns", then=Value(2)),
                        default=Value(1),
                        output_field=IntegerField(),
                    )
                )

            try:
                source_cap = int(source_cap_param) if source_cap_param is not None else DEFAULT_LIST_PER_SOURCE_CAP
            except (TypeError, ValueError):
                source_cap = DEFAULT_LIST_PER_SOURCE_CAP

            if (
                diversify_enabled
                and not source_param
                and source_cap > 0
                and connection.features.supports_over_clause
            ):
                queryset = queryset.annotate(
                    _source_rank=Window(
                        expression=RowNumber(),
                        partition_by=[F("source_id")],
                        order_by=[F("date_publication").desc(), F("id").desc()],
                    )
                ).filter(_source_rank__lte=source_cap)
                if not self.request.query_params.get("ordering"):
                    if stage_requested and not source_param:
                        self.ordering = ["_stage_source_priority", "_source_rank", "-date_publication", "-id"]
                    else:
                        self.ordering = ["_source_rank", "-date_publication", "-id"]
            elif stage_requested and not source_param and not self.request.query_params.get("ordering"):
                self.ordering = ["_stage_source_priority", "-date_publication", "-id"]

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
    queryset = SourceOpportunite.objects.all().order_by("id")
    serializer_class = SourceOpportuniteSerializer
    permission_classes = [IsAdminOrReadOnly]
