import logging
import secrets
import time
from pathlib import Path

from django.conf import settings
from django.db import connection
from django.db.models import Count
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action, api_view, parser_classes, permission_classes, throttle_classes
from rest_framework.filters import OrderingFilter
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.throttling import ScopedRateThrottle
from django_filters.rest_framework import DjangoFilterBackend

from .api.services.facets import get_cached_opportunity_facets
from .api.services.opportunities import build_opportunity_queryset
from .dataset_metrics import compute_pipeline_metrics
from .filters import OpportuniteFilterSet
from .models import DateConfidence, Opportunite, SourceOpportunite, StatutOpportunite
from .moderation_llm import DECISION_APPROVED, classify_opportunity_with_gemini, failed_llm_result
from .normalization.employment import normalize_contract_types, normalize_schedule, normalize_work_mode
from .pagination import OpportunityPagination, SimilarityPagination
from .permissions import IsAdminOrReadOnly, IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly
from .serializers import (
    OpportuniteSerializer,
    OrganizationOpportunitySerializer,
    OrganizationTenderDocumentUploadSerializer,
    OrganizationOpportunityWriteSerializer,
    SimilarOpportunitySerializer,
    SourceOpportuniteSerializer,
)
from .similarity import find_similar_opportunities_with_fallback
from .source_cleanup import removed_source_q
from .throttles import OrganizationOpportunityPostThrottle
from .turnstile import verify_turnstile_token
from users.models import OrganizationProfile, Utilisateur
from users.storage import ProfileResumeStorage


logger = logging.getLogger(__name__)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def pipeline_metrics_view(request):
    return Response(compute_pipeline_metrics())


ORGANIZATION_SOURCE_NAME = "BidWise Organizations"
ORGANIZATION_SOURCE_URL = "https://bidwise.local/organizations"


def _require_organization_profile(request):
    if request.user.account_type != Utilisateur.AccountType.ORGANIZATION:
        return None, Response(
            {"detail": "Organization account required."},
            status=status.HTTP_403_FORBIDDEN,
        )

    try:
        return request.user.organization_profile, None
    except OrganizationProfile.DoesNotExist:
        return None, Response(
            {"detail": "Complete your organization profile before managing opportunities."},
            status=status.HTTP_403_FORBIDDEN,
        )


def _moderation_payload(validated_data, submitted_data):
    payload = dict(validated_data)
    for key in ("contract", "availability", "salary", "experience_min", "experience_max", "skills", "deadline"):
        if key in submitted_data:
            payload[key] = submitted_data.get(key)
    return payload


def _client_ip(request):
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    return request.META.get("REMOTE_ADDR")


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([OrganizationOpportunityPostThrottle])
def organization_opportunities_view(request):
    organization_profile, error_response = _require_organization_profile(request)
    if error_response:
        return error_response

    if request.method == "POST":
        serializer = OrganizationOpportunityWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        turnstile = verify_turnstile_token(
            request.data.get("turnstile_token"),
            remote_ip=_client_ip(request),
        )
        if not turnstile.success:
            return Response(
                {"turnstile_token": [turnstile.reason]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        source, _created = SourceOpportunite.objects.get_or_create(
            nom=ORGANIZATION_SOURCE_NAME,
            defaults={
                "url": ORGANIZATION_SOURCE_URL,
                "type_source": "AUTRE",
            },
        )

        contract = data.get("contract", "")
        availability = data.get("availability", "")
        moderation_payload = _moderation_payload(data, request.data)
        try:
            llm_moderation_result = classify_opportunity_with_gemini(moderation_payload)
        except Exception:  # pragma: no cover - defensive guard for provider integration failures.
            logger.exception("Unexpected LLM moderation failure; keeping opportunity for admin review.")
            llm_moderation_result = failed_llm_result(
                "LLM moderation failed unexpectedly; kept for admin review.",
            )
        extra_data = {"published_by": "organization"}
        if data.get("internship_details"):
            extra_data["internship_details"] = data["internship_details"]
        if data.get("seasonal_details"):
            extra_data["seasonal_details"] = data["seasonal_details"]
        if data.get("project_details"):
            extra_data.update(data["project_details"])
            extra_data["project_details"] = data["project_details"]
        opportunity_status = (
            StatutOpportunite.ACTIVE
            if llm_moderation_result.decision == DECISION_APPROVED
            else StatutOpportunite.PENDING_REVIEW
        )
        extra_data["moderation"] = {
            "llm": llm_moderation_result.to_dict(),
            "final_decision": llm_moderation_result.decision,
            "final_status": opportunity_status,
        }

        opportunity = Opportunite.objects.create(
            titre=data["title"],
            description=data["description"],
            description_html="",
            organisation_nom=(
                data.get("project_details", {}).get("public_buyer")
                or organization_profile.organization_name
            ),
            ville=data["location"],
            contract_type=contract,
            normalized_contract_types=normalize_contract_types(contract),
            availability=availability,
            normalized_work_mode=normalize_work_mode(availability),
            normalized_schedule=normalize_schedule([availability, contract]),
            experience_min=data.get("experience_min"),
            experience_max=data.get("experience_max"),
            education_level=data.get("education_level", ""),
            salary=data.get("salary", ""),
            skills=data.get("skills", []),
            raw_skills=data.get("skills", []),
            type_opportunite=data["type"],
            statut=opportunity_status,
            date_publication=timezone.localdate(),
            date_limite=data.get("deadline"),
            date_confidence=DateConfidence.EXACT,
            source=source,
            organisation=request.user,
            extra_data=extra_data,
        )
        opportunity = (
            Opportunite.objects
            .filter(pk=opportunity.pk)
            .annotate(applications_count=Count("candidatures"))
            .get()
        )
        return Response(
            OrganizationOpportunitySerializer(opportunity).data,
            status=status.HTTP_201_CREATED,
        )

    opportunities = (
        Opportunite.objects
        .filter(organisation=request.user)
        .annotate(applications_count=Count("candidatures"))
        .order_by("-date_creation", "-id")
    )
    serializer = OrganizationOpportunitySerializer(opportunities, many=True)
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def organization_tender_document_upload_view(request):
    _organization_profile, error_response = _require_organization_profile(request)
    if error_response:
        return error_response

    serializer = OrganizationTenderDocumentUploadSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    uploaded_file = serializer.validated_data["file"]
    doc_type = serializer.validated_data["type"]
    label = serializer.validated_data.get("label") or Path(uploaded_file.name or "Document").stem
    extension = Path(uploaded_file.name or "").suffix.lower()
    storage = ProfileResumeStorage()
    storage_name = (
        f"organization_tender_documents/"
        f"{request.user.pk}/"
        f"{secrets.token_hex(16)}{extension}"
    )
    saved_name = storage.save(storage_name, uploaded_file)

    return Response(
        {
            "type": doc_type,
            "label": label,
            "url": storage.url(saved_name),
            "filename": Path(uploaded_file.name or saved_name).name,
            "size": getattr(uploaded_file, "size", 0),
        },
        status=status.HTTP_201_CREATED,
    )


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
