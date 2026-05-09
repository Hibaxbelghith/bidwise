import logging

from django.db.models import Count
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from applications.models import Candidature, StatutSuiviCandidature
from opportunities.models import Opportunite, StatutOpportunite, TypeOpportunite
from users.models import Profil
from .crossencoder import rerank_ranked_opportunities
from .embeddings import get_cached_profile_embedding_or_enqueue
from .explainability import build_recommendation_explanation
from .profile_strength import compute_profile_strength, recommendation_mode_for_profile
from .quality_gates import (
    build_recommendation_evidence,
    evidence_summary,
    fallback_limit_for_profile,
    filter_ranked_recommendations,
    sanitize_recommendation_gaps,
    sanitize_recommendation_reasons,
)
from .recommendation_service import get_score_label, rank_opportunities
from .retrieval import MAX_SEMANTIC_CANDIDATES, retrieve_recommendation_candidates
from .user_features import build_user_features


logger = logging.getLogger(__name__)

MAX_RECOMMENDATIONS = 50
DEFAULT_RECOMMENDATIONS = 10
MIN_MATCH_SCORE = 0.1
BUSINESS_RERANK_CANDIDATES = 50
POSITIVE_APPLICATION_STATUSES = (
    StatutSuiviCandidature.INTERESSEE,
    StatutSuiviCandidature.POSTULEE_EXTERNEMENT,
)

OPPORTUNITY_TYPE_MAP = {
    "JOB": TypeOpportunite.EMPLOI,
    "EMPLOI": TypeOpportunite.EMPLOI,
    "INTERNSHIP": TypeOpportunite.STAGE,
    "STAGE": TypeOpportunite.STAGE,
    "RESEARCH": TypeOpportunite.RECHERCHE,
    "RECHERCHE": TypeOpportunite.RECHERCHE,
    "FUNDING": TypeOpportunite.FINANCEMENT,
    "FINANCEMENT": TypeOpportunite.FINANCEMENT,
    "PROJECT": TypeOpportunite.PROJET,
    "PROJET": TypeOpportunite.PROJET,
}


def _parse_limit(value):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = DEFAULT_RECOMMENDATIONS
    return max(1, min(parsed, MAX_RECOMMENDATIONS))


def _profile_opportunity_types(profile):
    selected = getattr(profile, "opportunity_types", []) or []
    normalized = []
    for item in selected:
        mapped = OPPORTUNITY_TYPE_MAP.get(str(item).strip().upper())
        if mapped and mapped not in normalized:
            normalized.append(mapped)
    return normalized


def _serialize_recommendation(opportunity, *, features=None, profile_strength=None):
    score = getattr(opportunity, "match_score", None)
    semantic_score = getattr(opportunity, "semantic_score", None)
    business_score = getattr(opportunity, "business_score", None)
    feedback_score = getattr(opportunity, "feedback_score", None)
    base_reasons = getattr(opportunity, "reason", []) or []
    explanation = build_recommendation_explanation(features or {}, opportunity)
    evidence = getattr(opportunity, "recommendation_evidence", None) or build_recommendation_evidence(
        features or {},
        opportunity,
        profile_strength,
    )
    reasons = []
    for reason in list(explanation["reasons"]) + list(base_reasons):
        if reason and reason not in reasons:
            reasons.append(reason)
    reasons = sanitize_recommendation_reasons(reasons, evidence)
    gaps = sanitize_recommendation_gaps(explanation["gaps"])
    profile_strength_level = (profile_strength or {}).get("level", "LOW")
    return {
        "id": opportunity.id,
        "title": opportunity.titre,
        "score": round(float(score or 0.0), 4),
        "match_score": round(float(score or 0.0), 4),
        "semantic_score": round(float(semantic_score or 0.0), 4),
        "business_score": round(float(business_score or 0.0), 4),
        "feedback_score": round(float(feedback_score or 0.0), 4),
        "score_label": getattr(opportunity, "score_label", None) or get_score_label(score or 0.0),
        "score_level": getattr(opportunity, "score_level", None) or "LOW",
        "reason": reasons,
        "reasons": reasons,
        "gaps": gaps,
        "recommendation_confidence": getattr(opportunity, "recommendation_confidence", "LOW"),
        "profile_strength": profile_strength_level,
        "recommendation_mode": getattr(
            opportunity,
            "recommendation_mode",
            recommendation_mode_for_profile(profile_strength),
        ),
        "evidence_summary": evidence_summary(evidence),
        "location": opportunity.ville or "",
        "company": opportunity.organisation_nom or "",
        "type": opportunity.type_opportunite,
    }


def _serialize_fallback(opportunity, *, profile_strength=None, recommendation_mode="FALLBACK"):
    application_count = int(getattr(opportunity, "application_count", 0) or 0)
    reason = "Popular opportunity" if application_count else "Recent opportunity"
    profile_strength_level = (profile_strength or {}).get("level", "LOW")
    return {
        "id": opportunity.id,
        "title": opportunity.titre,
        "score": 0.0,
        "match_score": 0.0,
        "semantic_score": 0.0,
        "business_score": 0.0,
        "feedback_score": 0.0,
        "score_label": get_score_label(0.0, is_fallback=True),
        "score_level": "TRENDING",
        "reason": [reason],
        "reasons": [reason],
        "gaps": [],
        "recommendation_confidence": "LOW",
        "profile_strength": profile_strength_level,
        "recommendation_mode": recommendation_mode,
        "evidence_summary": {
            "skill_overlap": 0,
            "role_match": False,
            "title_overlap": False,
            "industry_match": False,
            "semantic_strength": "WEAK",
            "resume_signal": False,
        },
        "location": opportunity.ville or "",
        "company": opportunity.organisation_nom or "",
        "type": opportunity.type_opportunite,
    }


def _followed_opportunity_ids(user):
    return list(
        Candidature.objects
        .filter(candidat=user)
        .values_list("opportunite_id", flat=True)
    )


def _feedback_context(user):
    applications = (
        Candidature.objects
        .filter(candidat=user, statut__in=POSITIVE_APPLICATION_STATUSES)
        .select_related("opportunite")
        .order_by("-date_creation", "-id")[:20]
    )

    applied_embeddings = []
    applied_skills = []
    for application in applications:
        opportunity = application.opportunite
        if isinstance(opportunity.embedding_vector, list) and opportunity.embedding_vector:
            applied_embeddings.append(opportunity.embedding_vector)
        if isinstance(opportunity.skills, list):
            applied_skills.extend(opportunity.skills)

    return {
        "applied_embeddings": applied_embeddings,
        "applied_skills": applied_skills,
    }


def _fallback_recommendations(
    limit,
    exclude_ids=None,
    opportunity_types=None,
    profile_strength=None,
    recommendation_mode="FALLBACK",
):
    def fetch(exclusions=None):
        queryset = (
            Opportunite.objects
            .filter(statut=StatutOpportunite.ACTIVE)
            .annotate(application_count=Count("candidatures"))
            .order_by("-application_count", "-date_publication", "-id")
        )
        if opportunity_types:
            queryset = queryset.filter(type_opportunite__in=opportunity_types)
        if exclusions:
            queryset = queryset.exclude(id__in=exclusions)

        fallback_items = queryset.only(
            "id",
            "titre",
            "organisation_nom",
            "ville",
            "type_opportunite",
            "date_publication",
        )[:limit]
        return [
            _serialize_fallback(
                item,
                profile_strength=profile_strength,
                recommendation_mode=recommendation_mode,
            )
            for item in fallback_items
        ]

    results = fetch(exclude_ids)
    if results or not exclude_ids:
        return results

    logger.info("Recommendation fallback empty after exclusions; retrying without exclusions.")
    return fetch()


def _safe_followed_opportunity_ids(user):
    try:
        return _followed_opportunity_ids(user)
    except Exception:
        logger.exception(
            "Failed to load followed opportunity ids for user_id=%s",
            getattr(user, "pk", None),
        )
        return []


def _safe_user_opportunity_types(user):
    try:
        return _profile_opportunity_types(user.profil)
    except Profil.DoesNotExist:
        return []
    except Exception:
        logger.exception(
            "Failed to load recommendation opportunity types for user_id=%s",
            getattr(user, "pk", None),
        )
        return []


def _safe_user_profile_strength(user):
    try:
        profile = user.profil
    except Profil.DoesNotExist:
        return None
    except Exception:
        logger.exception(
            "Failed to load recommendation profile strength for user_id=%s",
            getattr(user, "pk", None),
        )
        return None

    try:
        return compute_profile_strength(profile, build_user_features(profile))
    except Exception:
        logger.exception(
            "Failed to compute recommendation profile strength for user_id=%s",
            getattr(user, "pk", None),
        )
        return None


def _safe_fallback_recommendations(
    limit,
    exclude_ids=None,
    opportunity_types=None,
    profile_strength=None,
    recommendation_mode="FALLBACK",
):
    try:
        return _fallback_recommendations(
            limit,
            exclude_ids=exclude_ids,
            opportunity_types=opportunity_types,
            profile_strength=profile_strength,
            recommendation_mode=recommendation_mode,
        )
    except Exception:
        logger.exception("Recommendation fallback failed.")
        return []


def _build_recommendations(request, limit):
    try:
        profile = request.user.profil
    except Profil.DoesNotExist:
        return _fallback_recommendations(limit)

    features = build_user_features(profile)
    profile_state = _profile_completion_state(profile)
    profile_strength = compute_profile_strength(profile, features)
    recommendation_mode = recommendation_mode_for_profile(profile_strength)
    opportunity_types = _profile_opportunity_types(profile)

    try:
        user_embedding = get_cached_profile_embedding_or_enqueue(profile)
    except Exception:
        logger.exception("Failed to load or enqueue user embedding for profile_id=%s", profile.pk)
        return _fallback_recommendations(
            fallback_limit_for_profile(limit, profile_strength),
            exclude_ids=_safe_followed_opportunity_ids(request.user),
            opportunity_types=opportunity_types,
            profile_strength=profile_strength,
            recommendation_mode=recommendation_mode,
        )

    followed_ids = _safe_followed_opportunity_ids(request.user)
    queryset = (
        Opportunite.objects
        .filter(statut=StatutOpportunite.ACTIVE)
        .annotate(application_count=Count("candidatures"))
        .order_by("-date_publication", "-id")
    )
    if followed_ids:
        queryset = queryset.exclude(id__in=followed_ids)

    if opportunity_types:
        queryset = queryset.filter(type_opportunite__in=opportunity_types)

    candidate_limit = MAX_SEMANTIC_CANDIDATES
    candidates = retrieve_recommendation_candidates(
        user_embedding,
        queryset,
        candidate_limit,
        embedding_model=getattr(profile, "embedding_model", ""),
    )
    ranked = rank_opportunities(
        user_embedding,
        candidates,
        features=features,
        feedback=_feedback_context(request.user),
        mode=profile_state,
        top_k=min(candidate_limit, max(limit, BUSINESS_RERANK_CANDIDATES)),
        min_score=MIN_MATCH_SCORE,
    )
    ranked = rerank_ranked_opportunities(ranked, features=features)
    ranked = filter_ranked_recommendations(
        ranked,
        features=features,
        profile_strength=profile_strength,
        limit=limit,
    )
    if not ranked:
        return _fallback_recommendations(
            fallback_limit_for_profile(limit, profile_strength),
            exclude_ids=followed_ids,
            opportunity_types=opportunity_types,
            profile_strength=profile_strength,
            recommendation_mode=recommendation_mode,
        )

    recommendations = [
        _serialize_recommendation(item, features=features, profile_strength=profile_strength)
        for item in ranked
    ]
    if recommendations:
        return recommendations
    return _fallback_recommendations(
        fallback_limit_for_profile(limit, profile_strength),
        exclude_ids=followed_ids,
        opportunity_types=opportunity_types,
        profile_strength=profile_strength,
        recommendation_mode=recommendation_mode,
    )


def _profile_completion_state(profile):
    features = build_user_features(profile)
    required = (
        bool(features.get("skills")),
        bool(features.get("roles")),
        bool(features.get("experience_level")),
        bool(features.get("location")),
        bool(features.get("remote")),
        bool(features.get("employment_types")),
    )
    return "complete" if all(required) else "partial"


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def recommendations_view(request):
    """
    Example API endpoint for user recommendations.

    GET /api/recommendations/?limit=10
    Returns active opportunities ranked against the cached user profile embedding.
    """
    limit = _parse_limit(request.query_params.get("limit"))
    try:
        recommendations = _build_recommendations(request, limit)
    except Exception:
        logger.exception(
            "Recommendation error for user_id=%s",
            getattr(request.user, "pk", None),
        )
        profile_strength = _safe_user_profile_strength(request.user)
        recommendations = _safe_fallback_recommendations(
            fallback_limit_for_profile(limit, profile_strength),
            exclude_ids=_safe_followed_opportunity_ids(request.user),
            opportunity_types=_safe_user_opportunity_types(request.user),
            profile_strength=profile_strength,
            recommendation_mode=recommendation_mode_for_profile(profile_strength),
        )

    if not recommendations:
        profile_strength = _safe_user_profile_strength(request.user)
        recommendations = _safe_fallback_recommendations(
            fallback_limit_for_profile(limit, profile_strength),
            exclude_ids=_safe_followed_opportunity_ids(request.user),
            opportunity_types=_safe_user_opportunity_types(request.user),
            profile_strength=profile_strength,
            recommendation_mode=recommendation_mode_for_profile(profile_strength),
        )

    return Response(recommendations, status=status.HTTP_200_OK)
