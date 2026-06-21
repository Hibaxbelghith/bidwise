import logging
import secrets
import time
from copy import deepcopy
from datetime import date, datetime
from pathlib import Path

from django.conf import settings
from django.db import connection, transaction
from django.db.models import Count, Q
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
from .organization_description_draft import (
    DescriptionDraftError,
    DescriptionDraftValidationError,
    generate_organization_description_draft,
)
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
from .throttles import OrganizationDescriptionDraftThrottle, OrganizationOpportunityPostThrottle
from .turnstile import verify_turnstile_token
from .tasks import send_organization_automatic_approval_email_task
from ai.tender_recommendation_service import get_tender_opportunities
from users.models import AuditLog, OrganizationProfile, Utilisateur
from users.storage import ProfileResumeStorage


logger = logging.getLogger(__name__)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def pipeline_metrics_view(request):
    return Response(compute_pipeline_metrics())


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def tender_recommendations_view(request):
    try:
        limit = int(request.query_params.get("limit", 50))
    except (TypeError, ValueError):
        limit = 50
    limit = max(1, min(limit, 50))

    items = get_tender_opportunities(user=request.user, limit=limit)
    serializer = OpportuniteSerializer(
        [item["opportunity"] for item in items],
        many=True,
        context={"request": request},
    )

    results = []
    for item, opportunity_data in zip(items, serializer.data):
        results.append(
            {
                "opportunity": opportunity_data,
                "score": item["score"],
                "priority": item["priority"],
                "reasons": item["reasons"],
                "components": item["components"],
            }
        )

    return Response(
        {
            "count": len(results),
            "results": results,
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([OrganizationDescriptionDraftThrottle])
def organization_description_draft_view(request):
    _organization_profile, error_response = _require_organization_profile(request)
    if error_response:
        return error_response

    try:
        draft = generate_organization_description_draft(request.data)
    except DescriptionDraftValidationError as exc:
        return Response(exc.fields, status=status.HTTP_400_BAD_REQUEST)
    except DescriptionDraftError:
        return Response(
            {"detail": "AI description generation is temporarily unavailable. You can continue writing manually."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    return Response(draft)


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


ORGANIZATION_OPPORTUNITY_MUTABLE_FIELDS = {
    "title",
    "location",
    "description",
    "contract",
    "availability",
    "experience_min",
    "experience_max",
    "education_level",
    "salary",
    "skills",
    "deadline",
    "internship_details",
    "seasonal_details",
    "project_details",
}

ORGANIZATION_OPPORTUNITY_IMMUTABLE_FIELDS = {
    "id",
    "type",
    "status",
    "statut",
    "source",
    "organisation",
    "organization",
    "organisation_nom",
    "extra_data",
    "published_at",
    "date_publication",
    "applications_count",
    "new_applications_count",
}


def _organization_opportunity_write_payload(opportunity):
    extra_data = opportunity.extra_data if isinstance(opportunity.extra_data, dict) else {}
    payload = {
        "title": opportunity.titre,
        "type": opportunity.type_opportunite,
        "location": opportunity.ville,
        "description": opportunity.description,
        "contract": opportunity.contract_type,
        "availability": opportunity.availability,
        "experience_min": opportunity.experience_min,
        "experience_max": opportunity.experience_max,
        "education_level": opportunity.education_level,
        "salary": opportunity.salary,
        "skills": opportunity.skills if isinstance(opportunity.skills, list) else [],
        "deadline": opportunity.date_limite,
    }
    if opportunity.type_opportunite == "STAGE":
        payload["internship_details"] = extra_data.get("internship_details") or {}
    elif opportunity.type_opportunite == "SAISONNIER":
        payload["seasonal_details"] = extra_data.get("seasonal_details") or {}
    elif opportunity.type_opportunite == "PROJET":
        payload["project_details"] = extra_data.get("project_details") or {}
    return payload


def _updated_organization_opportunity_extra_data(opportunity, data):
    extra_data = dict(opportunity.extra_data) if isinstance(opportunity.extra_data, dict) else {}
    extra_data["published_by"] = "organization"
    for key in ("internship_details", "seasonal_details", "project_details"):
        extra_data.pop(key, None)

    if data.get("internship_details"):
        extra_data["internship_details"] = data["internship_details"]
    if data.get("seasonal_details"):
        extra_data["seasonal_details"] = data["seasonal_details"]
    if data.get("project_details"):
        project_details = data["project_details"]
        extra_data.update(project_details)
        extra_data["project_details"] = project_details

    moderation = extra_data.get("moderation")
    if not isinstance(moderation, dict):
        moderation = {}
    moderation["final_status"] = StatutOpportunite.PENDING_REVIEW
    moderation["requires_remoderation"] = True
    moderation["content_updated_at"] = timezone.now().isoformat()
    extra_data["moderation"] = moderation
    return extra_data


def _json_safe_value(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _json_safe_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe_value(item) for item in value]
    return value


def _changed_opportunity_fields(before_payload, after_payload):
    return sorted(
        field
        for field in ORGANIZATION_OPPORTUNITY_MUTABLE_FIELDS
        if _json_safe_value(before_payload.get(field)) != _json_safe_value(after_payload.get(field))
    )


def _moderated_update_extra_data(opportunity, data, llm_result, *, changed_fields, previous_status):
    extra_data = _updated_organization_opportunity_extra_data(opportunity, data)
    previous_moderation = deepcopy(extra_data.get("moderation"))
    if not isinstance(previous_moderation, dict):
        previous_moderation = {}

    history = previous_moderation.get("history")
    if not isinstance(history, list):
        history = []
    previous_snapshot = {
        key: value
        for key, value in previous_moderation.items()
        if key not in {"history", "requires_remoderation", "content_updated_at"}
    }
    if previous_snapshot:
        history.append({
            "superseded_at": timezone.now().isoformat(),
            "reason": "organization_update",
            "moderation": previous_snapshot,
        })

    moderated_status = (
        StatutOpportunite.ACTIVE
        if llm_result.decision == DECISION_APPROVED
        else StatutOpportunite.PENDING_REVIEW
    )
    final_status = moderated_status
    if previous_status == StatutOpportunite.SUSPENDUE:
        final_status = StatutOpportunite.SUSPENDUE
        organization_status = extra_data.get("organization_status")
        if not isinstance(organization_status, dict):
            organization_status = {}
        organization_status["suspended_from"] = moderated_status
        organization_status["moderated_while_suspended_at"] = timezone.now().isoformat()
        extra_data["organization_status"] = organization_status
    elif previous_status == StatutOpportunite.REJECTED:
        final_status = StatutOpportunite.PENDING_REVIEW

    extra_data["moderation"] = {
        "llm": llm_result.to_dict(),
        "final_decision": llm_result.decision,
        "final_status": final_status,
        "activation_status": moderated_status,
        "history": history[-20:],
        "last_update": {
            "changed_fields": changed_fields,
            "previous_status": previous_status,
            "requires_admin_review": previous_status == StatutOpportunite.REJECTED,
            "moderated_at": timezone.now().isoformat(),
        },
    }
    return extra_data, final_status


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
        automatic_decision_id = timezone.now().isoformat()
        extra_data["moderation"] = {
            "llm": llm_moderation_result.to_dict(),
            "final_decision": llm_moderation_result.decision,
            "final_status": opportunity_status,
            "automatic_decision_id": automatic_decision_id,
        }

        with transaction.atomic():
            opportunity = Opportunite.objects.create(
                titre=data["title"],
                description=data["description"],
                description_html="",
                organisation_nom=(
                    data.get("project_details", {}).get("public_buyer")
                    or organization_profile.organization_name
                ),
                company_logo=organization_profile.logo or "",
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
            if opportunity_status == StatutOpportunite.ACTIVE:
                transaction.on_commit(
                    lambda: send_organization_automatic_approval_email_task.delay(
                        opportunity.pk,
                        automatic_decision_id,
                    )
                )
        opportunity = (
            Opportunite.objects
            .filter(pk=opportunity.pk)
            .annotate(
                applications_count=Count("candidatures"),
                new_applications_count=Count(
                    "candidatures",
                    filter=Q(candidatures__statut="SUBMITTED"),
                ),
            )
            .get()
        )
        return Response(
            OrganizationOpportunitySerializer(opportunity).data,
            status=status.HTTP_201_CREATED,
        )

    opportunities = (
        Opportunite.objects
        .filter(organisation=request.user)
        .annotate(
            applications_count=Count("candidatures"),
            new_applications_count=Count(
                "candidatures",
                filter=Q(candidatures__statut="SUBMITTED"),
            ),
        )
        .order_by("-date_creation", "-id")
    )
    serializer = OrganizationOpportunitySerializer(opportunities, many=True)
    return Response(serializer.data)


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def organization_opportunity_detail_view(request, pk):
    organization_profile, error_response = _require_organization_profile(request)
    if error_response:
        return error_response

    if request.method == "GET":
        opportunity = (
            Opportunite.objects
            .filter(pk=pk, organisation=request.user)
            .annotate(
                applications_count=Count("candidatures"),
                new_applications_count=Count(
                    "candidatures",
                    filter=Q(candidatures__statut="SUBMITTED"),
                ),
            )
            .first()
        )
        if opportunity is None:
            return Response(
                {"detail": "Opportunity not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(OrganizationOpportunitySerializer(opportunity).data)

    submitted_fields = set(request.data.keys())
    immutable_fields = sorted(submitted_fields & ORGANIZATION_OPPORTUNITY_IMMUTABLE_FIELDS)
    unknown_fields = sorted(
        submitted_fields
        - ORGANIZATION_OPPORTUNITY_MUTABLE_FIELDS
        - ORGANIZATION_OPPORTUNITY_IMMUTABLE_FIELDS
        - {"turnstile_token"}
    )
    errors = {}
    if immutable_fields:
        errors["immutable_fields"] = [
            f"These fields cannot be modified: {', '.join(immutable_fields)}."
        ]
    if unknown_fields:
        errors["unknown_fields"] = [
            f"Unsupported fields: {', '.join(unknown_fields)}."
        ]
    if errors:
        return Response(errors, status=status.HTTP_400_BAD_REQUEST)
    if not (submitted_fields & ORGANIZATION_OPPORTUNITY_MUTABLE_FIELDS):
        return Response(
            {"detail": "Provide at least one editable opportunity field."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    turnstile = verify_turnstile_token(
        request.data.get("turnstile_token"),
        remote_ip=_client_ip(request),
    )
    if not turnstile.success:
        return Response(
            {"turnstile_token": [turnstile.reason]},
            status=status.HTTP_400_BAD_REQUEST,
        )

    opportunity = Opportunite.objects.filter(pk=pk, organisation=request.user).first()
    if opportunity is None:
        return Response(
            {"detail": "Opportunity not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    if opportunity.statut in {
        StatutOpportunite.ARCHIVEE,
        StatutOpportunite.EXPIREE,
        StatutOpportunite.FERMEE,
    }:
        return Response(
            {"detail": "Closed, archived, or expired opportunities cannot be modified."},
            status=status.HTTP_409_CONFLICT,
        )

    original_modified_at = opportunity.date_modification
    previous_status = opportunity.statut
    before_payload = _organization_opportunity_write_payload(opportunity)
    merged_payload = deepcopy(before_payload)
    for field in ORGANIZATION_OPPORTUNITY_MUTABLE_FIELDS:
        if field in request.data:
            merged_payload[field] = request.data.get(field)

    serializer = OrganizationOpportunityWriteSerializer(data=merged_payload)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    changed_fields = _changed_opportunity_fields(before_payload, data)
    if not changed_fields:
        return Response(
            {
                "detail": "No changes were needed.",
                "opportunity": OrganizationOpportunitySerializer(
                    Opportunite.objects
                    .filter(pk=opportunity.pk)
                    .annotate(
                        applications_count=Count("candidatures"),
                        new_applications_count=Count(
                            "candidatures",
                            filter=Q(candidatures__statut="SUBMITTED"),
                        ),
                    )
                    .get()
                ).data,
            },
            status=status.HTTP_200_OK,
        )

    moderation_payload = _moderation_payload(data, merged_payload)
    try:
        llm_moderation_result = classify_opportunity_with_gemini(moderation_payload)
    except Exception:  # pragma: no cover - defensive guard for provider integration failures.
        logger.exception("Unexpected LLM moderation failure after organization opportunity update.")
        llm_moderation_result = failed_llm_result(
            "LLM moderation failed unexpectedly; kept for admin review.",
        )

    with transaction.atomic():
        opportunity = (
            Opportunite.objects
            .select_for_update()
            .filter(pk=pk, organisation=request.user)
            .first()
        )
        if opportunity is None:
            return Response(
                {"detail": "Opportunity not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if opportunity.date_modification != original_modified_at:
            return Response(
                {"detail": "This opportunity was modified in another session. Refresh and try again."},
                status=status.HTTP_409_CONFLICT,
            )
        if opportunity.statut in {
            StatutOpportunite.ARCHIVEE,
            StatutOpportunite.EXPIREE,
            StatutOpportunite.FERMEE,
        }:
            return Response(
                {"detail": "Closed, archived, or expired opportunities cannot be modified."},
                status=status.HTTP_409_CONFLICT,
            )

        opportunity.titre = data["title"]
        opportunity.description = data["description"]
        opportunity.description_html = ""
        opportunity.organisation_nom = (
            data.get("project_details", {}).get("public_buyer")
            or organization_profile.organization_name
        )
        opportunity.company_logo = organization_profile.logo or ""
        opportunity.ville = data["location"]
        opportunity.contract_type = data.get("contract", "")
        opportunity.normalized_contract_types = normalize_contract_types(opportunity.contract_type)
        opportunity.availability = data.get("availability", "")
        opportunity.normalized_work_mode = normalize_work_mode(opportunity.availability)
        opportunity.normalized_schedule = normalize_schedule(
            [opportunity.availability, opportunity.contract_type]
        )
        opportunity.experience_min = data.get("experience_min")
        opportunity.experience_max = data.get("experience_max")
        opportunity.education_level = data.get("education_level", "")
        opportunity.salary = data.get("salary", "")
        opportunity.skills = data.get("skills", [])
        opportunity.raw_skills = data.get("skills", [])
        opportunity.date_limite = data.get("deadline")
        opportunity.extra_data, opportunity.statut = _moderated_update_extra_data(
            opportunity,
            data,
            llm_moderation_result,
            changed_fields=changed_fields,
            previous_status=previous_status,
        )
        opportunity.save()
        organization_profile = request.user.organization_profile
        AuditLog.objects.create(
            actor=request.user,
            target=request.user,
            action=AuditLog.Action.UPDATE_ORG_OPPORTUNITY,
            metadata={
                "message": "Organization opportunity updated and re-moderated.",
                "opportunity_id": opportunity.pk,
                "opportunity_title": opportunity.titre,
                "organization_email": request.user.email,
                "organization_name": organization_profile.organization_name,
                "organization_phone": organization_profile.phone or "",
                "organization_type": organization_profile.organization_type or "",
                "organization_website": organization_profile.website or "",
                "organization_contact_name": " ".join(
                    part
                    for part in [organization_profile.first_name, organization_profile.last_name]
                    if part
                ),
                "changed_fields": changed_fields,
                "before_status": previous_status,
                "after_status": opportunity.statut,
                "decision": llm_moderation_result.decision,
                "ai_category": llm_moderation_result.category,
                "ai_decision": llm_moderation_result.decision,
                "ai_confidence": llm_moderation_result.confidence,
                "ai_explanation": llm_moderation_result.reason,
            },
        )

    opportunity = (
        Opportunite.objects
        .filter(pk=opportunity.pk)
        .annotate(
            applications_count=Count("candidatures"),
            new_applications_count=Count(
                "candidatures",
                filter=Q(candidatures__statut="SUBMITTED"),
            ),
        )
        .get()
    )
    return Response(
        {
            "detail": (
                "Opportunity updated and remains suspended."
                if opportunity.statut == StatutOpportunite.SUSPENDUE
                else (
                    "Opportunity updated and published."
                    if opportunity.statut == StatutOpportunite.ACTIVE
                    else "Opportunity updated and submitted for review."
                )
            ),
            "opportunity": OrganizationOpportunitySerializer(opportunity).data,
        },
        status=status.HTTP_200_OK,
    )


ORGANIZATION_STATUS_ACTIONS = {
    "suspend": {
        "allowed": {
            StatutOpportunite.ACTIVE,
            StatutOpportunite.PENDING_REVIEW,
            StatutOpportunite.FERMEE,
        },
        "target": StatutOpportunite.SUSPENDUE,
        "audit_action": AuditLog.Action.SUSPEND_ORG_OPPORTUNITY,
        "message": "Organization opportunity suspended.",
    },
    "activate": {
        "allowed": {
            StatutOpportunite.SUSPENDUE,
            StatutOpportunite.PENDING_REVIEW,
            StatutOpportunite.FERMEE,
        },
        "target": StatutOpportunite.ACTIVE,
        "audit_action": AuditLog.Action.ACTIVATE_ORG_OPPORTUNITY,
        "message": "Organization opportunity activated.",
    },
    "close": {
        "allowed": {
            StatutOpportunite.ACTIVE,
            StatutOpportunite.SUSPENDUE,
            StatutOpportunite.PENDING_REVIEW,
            StatutOpportunite.REJECTED,
        },
        "target": StatutOpportunite.FERMEE,
        "audit_action": AuditLog.Action.CLOSE_ORG_OPPORTUNITY,
        "message": "Organization opportunity closed.",
    },
}


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def organization_opportunity_status_action_view(request, pk, action):
    organization_profile, error_response = _require_organization_profile(request)
    if error_response:
        return error_response
    action_config = ORGANIZATION_STATUS_ACTIONS.get(action)
    if action_config is None:
        return Response({"detail": "Unsupported status action."}, status=status.HTTP_404_NOT_FOUND)

    with transaction.atomic():
        opportunity = (
            Opportunite.objects
            .select_for_update()
            .filter(pk=pk, organisation=request.user)
            .first()
        )
        if opportunity is None:
            return Response({"detail": "Opportunity not found."}, status=status.HTTP_404_NOT_FOUND)

        before_status = opportunity.statut
        opportunity.applications_count = opportunity.candidatures.count()
        opportunity.new_applications_count = opportunity.candidatures.filter(
            statut="SUBMITTED",
        ).count()
        target_status = action_config["target"]
        extra_data = dict(opportunity.extra_data) if isinstance(opportunity.extra_data, dict) else {}
        organization_status = extra_data.get("organization_status")
        if not isinstance(organization_status, dict):
            organization_status = {}
        if action == "activate":
            if before_status == StatutOpportunite.PENDING_REVIEW:
                target_status = StatutOpportunite.PENDING_REVIEW
            elif before_status == StatutOpportunite.SUSPENDUE:
                suspended_from = organization_status.get("suspended_from")
                target_status = (
                    StatutOpportunite.PENDING_REVIEW
                    if suspended_from == StatutOpportunite.PENDING_REVIEW
                    else StatutOpportunite.ACTIVE
                )
            elif before_status == StatutOpportunite.FERMEE:
                closed_from = organization_status.get("closed_from")
                target_status = (
                    StatutOpportunite.PENDING_REVIEW
                    if closed_from in {
                        StatutOpportunite.PENDING_REVIEW,
                        StatutOpportunite.REJECTED,
                    }
                    else StatutOpportunite.ACTIVE
                )
        if before_status == target_status:
            return Response(
                {
                    "detail": f"Opportunity is already {target_status.lower()}.",
                    "opportunity": OrganizationOpportunitySerializer(opportunity).data,
                },
                status=status.HTTP_200_OK,
            )
        if before_status in {StatutOpportunite.ARCHIVEE, StatutOpportunite.EXPIREE}:
            return Response(
                {"detail": "Archived or expired opportunities cannot change organization status."},
                status=status.HTTP_409_CONFLICT,
            )
        if before_status not in action_config["allowed"]:
            return Response(
                {"detail": f"Cannot {action} an opportunity with status {before_status}."},
                status=status.HTTP_409_CONFLICT,
            )

        opportunity.statut = target_status
        if action == "suspend":
            suspended_from = before_status
            if before_status == StatutOpportunite.FERMEE:
                suspended_from = organization_status.get("closed_from", StatutOpportunite.ACTIVE)
            organization_status["suspended_from"] = suspended_from
        elif action == "close":
            closed_from = before_status
            if before_status == StatutOpportunite.SUSPENDUE:
                closed_from = organization_status.get(
                    "suspended_from",
                    StatutOpportunite.ACTIVE,
                )
            organization_status["closed_from"] = closed_from
        organization_status.update({
            "last_action": action,
            "before_status": before_status,
            "after_status": target_status,
            "changed_at": timezone.now().isoformat(),
        })
        extra_data["organization_status"] = organization_status
        opportunity.extra_data = extra_data
        opportunity.save(update_fields=["statut", "extra_data", "date_modification"])

        AuditLog.objects.create(
            actor=request.user,
            target=request.user,
            action=action_config["audit_action"],
            metadata={
                "message": action_config["message"],
                "opportunity_id": opportunity.pk,
                "opportunity_title": opportunity.titre,
                "organization_email": request.user.email,
                "organization_name": organization_profile.organization_name,
                "before_status": before_status,
                "after_status": target_status,
                "decision": action,
                "applications_count": opportunity.applications_count,
            },
        )

    return Response(
        {
            "detail": action_config["message"],
            "opportunity": OrganizationOpportunitySerializer(opportunity).data,
        },
        status=status.HTTP_200_OK,
    )


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
