import logging
import hashlib
import json

from django.conf import settings
from django.core.cache import cache
from django.db.models import Count, Max, Q
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from applications.models import Candidature, StatutSuiviCandidature
from opportunities.models import Opportunite, StatutOpportunite, TypeOpportunite
from users.models import Profil
from .crossencoder import rerank_ranked_opportunities
from .embeddings import build_user_embedding_text, get_cached_profile_embedding_or_enqueue
from .explainability import build_recommendation_explanation
from .jobbert import (
    build_precomputed_jobbert_scores,
    get_or_build_profile_jobbert_embedding,
    jobbert_enabled,
    jobbert_model_name,
)
from .profile_strength import compute_profile_strength, recommendation_mode_for_profile
from .quality_gates import (
    annotate_recommendation_quality,
    build_recommendation_evidence,
    evidence_summary,
    fallback_limit_for_profile,
    filter_ranked_recommendations,
    passes_recommendation_quality_gate,
    sanitize_recommendation_gaps,
    sanitize_recommendation_reasons,
)
from .recommendation_service import get_score_label, rank_opportunities
from .recommendation_llm import apply_llm_hierarchy_validation_to_ranked
from .resume_match.evidence import READY_STATUS, build_resume_match_evidence
from .resume_match.llm import (
    ResumeMatchLLMError,
    generate_cover_letter,
    generate_interview_prep,
    generate_resume_match_analysis,
    generate_resume_optimization,
    generate_summary_rewrite,
)
from .retrieval import (
    MAX_SEMANTIC_CANDIDATES,
    RECOMMENDATION_CANDIDATE_FIELDS,
    retrieve_recommendation_candidates,
)
from .user_features import build_user_features


logger = logging.getLogger(__name__)

MAX_RECOMMENDATIONS = 50
DEFAULT_RECOMMENDATIONS = 10
MIN_MATCH_SCORE = 0.1
RECOMMENDATIONS_CACHE_TTL_SECONDS = 15 * 60
RESUME_MATCH_LLM_CACHE_TTL_SECONDS = 24 * 60 * 60
RESUME_MATCH_LLM_PROMPT_VERSION = 16
SHOW_RECENT_FALLBACK_SETTING = "RECOMMENDATION_SHOW_RECENT_FALLBACK"
BUSINESS_RERANK_CANDIDATES = 50
JOBBERT_RETRIEVAL_CANDIDATES = 2500
JOBBERT_RETRIEVAL_RERANK_CANDIDATES = 80
INTERNSHIP_FALLBACK_MIN_RESULTS = 3
CONTRACT_ALTERNATIVE_SCORE_LABEL = "Alternative match"
CONTRACT_ALTERNATIVE_REASON = "Outside preferred contract type"
CONTRACT_ALTERNATIVE_MODE = "CONTRACT_ALTERNATIVE"
POSITIVE_APPLICATION_STATUSES = (
    StatutSuiviCandidature.INTERESSEE,
    StatutSuiviCandidature.POSTULEE_EXTERNEMENT,
)

FAMILY_RETRIEVAL_TERMS = {
    "administration": (
        "assistante administrative",
        "assistant administratif",
        "administrative",
        "administratif",
        "secretaire",
        "secrétaire",
        "bureau",
        "archivage",
        "classement",
    ),
    "hr_administration": (
        "ressources humaines",
        "rh",
        "recrutement",
        "talent acquisition",
        "assistante administrative",
    ),
    "it_network_support": (
        "support informatique",
        "helpdesk",
        "technicien support",
        "systemes et reseaux",
        "systèmes et réseaux",
        "reseau",
        "réseau",
    ),
    "devops_cloud_infrastructure": (
        "devops",
        "cloud engineer",
        "cloud infrastructure",
        "docker",
        "kubernetes",
        "terraform",
        "ci/cd",
        "cicd",
        "github actions",
        "jenkins",
        "prometheus",
        "grafana",
    ),
    "it_support_network": (
        "support informatique",
        "helpdesk",
        "technicien support",
        "systemes et reseaux",
        "systèmes et réseaux",
        "reseau",
        "réseau",
    ),
    "accounting_finance_audit": (
        "comptable",
        "comptabilité",
        "comptabilite",
        "audit",
        "finance",
        "facturation",
    ),
    "accounting_finance": (
        "comptable",
        "comptabilité",
        "comptabilite",
        "audit",
        "finance",
        "facturation",
    ),
    "customer_support": (
        "service client",
        "customer support",
        "call center",
        "centre d'appel",
        "chargé clientèle",
    ),
}

OPPORTUNITY_TYPE_MAP = {
    "JOB": TypeOpportunite.EMPLOI,
    "EMPLOI": TypeOpportunite.EMPLOI,
    "INTERNSHIP": TypeOpportunite.STAGE,
    "STAGE": TypeOpportunite.STAGE,
    "CALLS_FOR_TENDER": TypeOpportunite.PROJET,
    "CALL_FOR_TENDER": TypeOpportunite.PROJET,
    "PROJECT": TypeOpportunite.PROJET,
    "PROJET": TypeOpportunite.PROJET,
}


def _exclude_internal_benchmark_opportunities(queryset):
    return queryset.exclude(source_item_url__icontains="benchmark.bidwise.local").exclude(
        source__nom__icontains="BidWise Recommendation Benchmark"
    )


def _parse_limit(value):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = DEFAULT_RECOMMENDATIONS
    return max(1, min(parsed, MAX_RECOMMENDATIONS))


def _stable_hash(payload):
    try:
        raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    except TypeError:
        raw = str(payload)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _active_opportunities_cache_marker():
    queryset = _exclude_internal_benchmark_opportunities(
        Opportunite.objects.filter(statut=StatutOpportunite.ACTIVE)
    )
    marker = queryset.aggregate(
        count=Count("id"),
        latest_modified=Max("date_modification"),
    )
    return {
        "count": int(marker.get("count") or 0),
        "latest_modified": marker.get("latest_modified"),
    }


def _followed_opportunities_cache_marker(user):
    values = _safe_followed_opportunity_ids(user)
    return _stable_hash(sorted(int(item) for item in values if item))


def _recommendations_cache_key(request, limit):
    try:
        profile = request.user.profil
    except Profil.DoesNotExist:
        return None

    features = build_user_features(profile)
    profile_marker = {
        "features": features,
        "embedding_content_hash": getattr(profile, "embedding_content_hash", ""),
        "embedding_updated_at": getattr(profile, "embedding_updated_at", None),
        "jobbert_embedding_content_hash": getattr(profile, "jobbert_embedding_content_hash", ""),
        "jobbert_embedding_updated_at": getattr(profile, "jobbert_embedding_updated_at", None),
    }
    key_payload = {
        "version": 1,
        "user_id": getattr(request.user, "pk", None),
        "profile_id": getattr(profile, "pk", None),
        "limit": int(limit),
        "profile": profile_marker,
        "opportunities": _active_opportunities_cache_marker(),
        "followed": _followed_opportunities_cache_marker(request.user),
    }
    return f"ai:recommendations:{_stable_hash(key_payload)}"


def _profile_opportunity_types(profile):
    selected = getattr(profile, "opportunity_types", []) or []
    normalized = []
    for item in selected:
        mapped = OPPORTUNITY_TYPE_MAP.get(str(item).strip().upper())
        if mapped and mapped not in normalized:
            normalized.append(mapped)
    return normalized


def _source_payload(opportunity):
    source = getattr(opportunity, "source", None)
    if not source:
        return None
    return {
        "id": source.id,
        "nom": source.nom,
        "url": source.url,
        "type_source": source.type_source,
    }


def _as_list(value):
    return value if isinstance(value, list) else []


def _opportunity_payload(opportunity):
    date_publication = getattr(opportunity, "date_publication", None)
    date_limite = getattr(opportunity, "date_limite", None)
    date_creation = getattr(opportunity, "date_creation", None)
    date_modification = getattr(opportunity, "date_modification", None)
    return {
        "id": opportunity.id,
        "titre": opportunity.titre,
        "title": opportunity.titre,
        "description": opportunity.description or "",
        "description_html": opportunity.description_html or "",
        "organisation_nom": opportunity.organisation_nom or "",
        "company": opportunity.organisation_nom or "",
        "company_logo": opportunity.company_logo or "",
        "ville": opportunity.ville or "",
        "location": opportunity.ville or "",
        "type_opportunite": opportunity.type_opportunite,
        "type": opportunity.type_opportunite,
        "statut": opportunity.statut,
        "date_publication": date_publication.isoformat() if date_publication else None,
        "date_limite": date_limite.isoformat() if date_limite else None,
        "date_creation": date_creation.isoformat() if date_creation else None,
        "date_modification": date_modification.isoformat() if date_modification else None,
        "source_item_url": opportunity.source_item_url or "",
        "source": _source_payload(opportunity),
        "salary": opportunity.salary or "",
        "contract_type": opportunity.contract_type or "",
        "availability": opportunity.availability or "",
        "education_level": opportunity.education_level or "",
        "experience_min": opportunity.experience_min,
        "experience_max": opportunity.experience_max,
        "experience_years": opportunity.experience_years,
        "normalized_contract_types": _as_list(opportunity.normalized_contract_types),
        "normalized_work_mode": opportunity.normalized_work_mode or "",
        "normalized_schedule": opportunity.normalized_schedule or "",
        "normalized_industries": _as_list(opportunity.normalized_industries),
        "skills": _as_list(opportunity.skills),
        "raw_skills": _as_list(opportunity.raw_skills),
        "normalized_skills": _as_list(opportunity.normalized_skills),
        "languages": _as_list(opportunity.languages),
        "languages_fallback": _as_list(opportunity.languages_fallback),
        "extra_data": opportunity.extra_data if isinstance(opportunity.extra_data, dict) else {},
    }


def _serialize_recommendation(opportunity, *, features=None, profile_strength=None):
    score = getattr(opportunity, "match_score", None)
    semantic_score = getattr(opportunity, "semantic_score", None)
    business_score = getattr(opportunity, "business_score", None)
    feedback_score = getattr(opportunity, "feedback_score", None)
    base_reasons = getattr(opportunity, "reason", []) or []
    contract_alternative_reason = getattr(opportunity, "contract_alternative_reason", "")
    explanation = build_recommendation_explanation(features or {}, opportunity)
    evidence = getattr(opportunity, "recommendation_evidence", None) or build_recommendation_evidence(
        features or {},
        opportunity,
        profile_strength,
    )
    recommendation_debug = getattr(opportunity, "recommendation_debug", {}) or {}
    jobbert_score = float(recommendation_debug.get("jobbert_score") or 0.0)
    jobbert_adjustment = float(recommendation_debug.get("jobbert_adjustment") or 0.0)
    reason_sources = list(explanation["reasons"]) + list(base_reasons)
    if contract_alternative_reason:
        reason_sources = [contract_alternative_reason, *reason_sources]
    reasons = []
    for reason in reason_sources:
        if reason and reason not in reasons:
            reasons.append(reason)
    reasons = sanitize_recommendation_reasons(reasons, evidence)
    gaps = sanitize_recommendation_gaps(explanation["gaps"])
    profile_strength_level = (profile_strength or {}).get("level", "LOW")
    payload = _opportunity_payload(opportunity)
    payload.update({
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
        "recommendation_bucket": getattr(opportunity, "recommendation_bucket", "RELATED_REVIEW"),
        "recommendation_bucket_reason": getattr(opportunity, "recommendation_bucket_reason", ""),
        "llm_hierarchy_validation": recommendation_debug.get("llm_hierarchy_validation", {}),
        "llm_hierarchy_policy": recommendation_debug.get("llm_hierarchy_policy", {}),
        "llm_hierarchy_cache_hit": bool(recommendation_debug.get("llm_hierarchy_cache_hit")),
        "evidence_summary": evidence_summary(evidence),
        "ai_semantic_score": round(jobbert_score, 4),
        "ai_semantic_adjustment": round(jobbert_adjustment, 6),
        "ai_semantic_model": "JobBERT" if jobbert_score else "",
    })
    return payload


def _serialize_fallback(opportunity, *, profile_strength=None, recommendation_mode="FALLBACK"):
    application_count = int(getattr(opportunity, "application_count", 0) or 0)
    reason = "Popular opportunity" if application_count else "Recent opportunity"
    profile_strength_level = (profile_strength or {}).get("level", "LOW")
    payload = _opportunity_payload(opportunity)
    payload.update({
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
    })
    return payload


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
    if not getattr(settings, SHOW_RECENT_FALLBACK_SETTING, False):
        logger.info(
            "Recommendation recent fallback suppressed; no personalized metier evidence passed quality gates."
        )
        return []

    def fetch(exclusions=None):
        queryset = (
            Opportunite.objects
            .filter(statut=StatutOpportunite.ACTIVE)
            .select_related("source")
            .annotate(application_count=Count("candidatures"))
            .order_by("-application_count", "-date_publication", "-id")
        )
        queryset = _exclude_internal_benchmark_opportunities(queryset)
        if opportunity_types:
            queryset = queryset.filter(type_opportunite__in=opportunity_types)
        if exclusions:
            queryset = queryset.exclude(id__in=exclusions)

        fallback_items = queryset[:limit]
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


def _normalized_feature_set(features, key):
    return {
        str(item or "").strip().upper()
        for item in (features or {}).get(key, []) or []
        if str(item or "").strip()
    }


def _is_strict_internship_context(features, opportunity_types):
    employment_types = _normalized_feature_set(features, "employment_types")
    selected_types = set(opportunity_types or [])
    stage_only_or_unspecified = not selected_types or selected_types == {TypeOpportunite.STAGE}
    return employment_types == {"INTERNSHIP"} and stage_only_or_unspecified


def _features_without_contract_preference(features):
    expanded = dict(features or {})
    expanded["employment_types"] = []
    return expanded


def _has_direct_metier_evidence(evidence):
    evidence = evidence if isinstance(evidence, dict) else {}
    return bool(
        evidence.get("skill_overlap")
        or evidence.get("role_match")
        or evidence.get("title_overlap")
    )


def _compact_terms(values, *, max_terms=16):
    terms = []
    seen = set()
    for value in values or []:
        term = str(value or "").strip()
        if len(term) < 3:
            continue
        key = term.casefold()
        if key in seen:
            continue
        seen.add(key)
        terms.append(term)
        if len(terms) >= max_terms:
            break
    return terms


def _lexical_retrieval_terms(features):
    terms = []
    for key in ("target_roles", "roles"):
        terms.extend(features.get(key) or [])
    for family in features.get("profile_business_families") or []:
        terms.extend(FAMILY_RETRIEVAL_TERMS.get(str(family or "").strip(), ()))
    return _compact_terms(terms)


def _lexical_metier_candidates(queryset, features, limit):
    terms = _lexical_retrieval_terms(features or {})
    if not terms:
        return []

    query = Q()
    for term in terms:
        query |= Q(titre__icontains=term)
        if len(term.split()) >= 2:
            query |= Q(description__icontains=term)

    if not query:
        return []

    return list(
        queryset
        .filter(query)
        .only(*RECOMMENDATION_CANDIDATE_FIELDS)
        .order_by("-date_publication", "-id")[: max(1, int(limit or 1))]
    )


def _merge_candidates(*candidate_groups):
    merged = []
    seen = set()
    for group in candidate_groups:
        for item in group or []:
            item_id = getattr(item, "id", None)
            if item_id in seen:
                continue
            seen.add(item_id)
            merged.append(item)
    return merged


def _rank_recommendation_queryset(
    *,
    user,
    profile,
    user_embedding,
    queryset,
    features,
    profile_state,
    limit,
):
    candidate_limit = MAX_SEMANTIC_CANDIDATES
    ranking_features = dict(features or {})
    ranking_features["_profile"] = profile
    candidates = retrieve_recommendation_candidates(
        user_embedding,
        queryset,
        candidate_limit,
        embedding_model=getattr(profile, "embedding_model", ""),
    )
    lexical_candidates = _lexical_metier_candidates(
        queryset,
        ranking_features,
        max(BUSINESS_RERANK_CANDIDATES * 2, limit * 2),
    )
    candidates = _merge_candidates(candidates, lexical_candidates)
    ranked = rank_opportunities(
        user_embedding,
        candidates,
        features=ranking_features,
        feedback=_feedback_context(user),
        mode=profile_state,
        top_k=min(candidate_limit, max(limit, BUSINESS_RERANK_CANDIDATES)),
        min_score=MIN_MATCH_SCORE,
    )
    return rerank_ranked_opportunities(ranked, features=features)


def _rank_jobbert_recommendation_queryset(
    *,
    profile,
    queryset,
    features,
    feedback,
    profile_state,
    limit,
):
    if not jobbert_enabled():
        return []

    profile_vector = get_or_build_profile_jobbert_embedding(profile, features or {})
    if not profile_vector:
        return []

    model_name = jobbert_model_name()
    candidates = list(
        queryset
        .filter(jobbert_embedding_model=model_name)
        .exclude(jobbert_embedding_vector__isnull=True)
        .only(*RECOMMENDATION_CANDIDATE_FIELDS)
        .order_by("-date_publication", "-id")[:JOBBERT_RETRIEVAL_CANDIDATES]
    )
    if not candidates:
        return []

    jobbert_scores = build_precomputed_jobbert_scores(profile_vector, candidates)
    if not jobbert_scores:
        return []

    selected = sorted(
        candidates,
        key=lambda item: jobbert_scores.get(int(getattr(item, "id", 0) or 0), 0.0),
        reverse=True,
    )[: max(limit, JOBBERT_RETRIEVAL_RERANK_CANDIDATES)]

    ranking_features = dict(features or {})
    ranking_features["_jobbert_profile_vector"] = profile_vector
    ranked = rank_opportunities(
        [],
        selected,
        features=ranking_features,
        feedback=feedback,
        mode="partial" if profile_state != "complete" else "partial",
        top_k=max(limit, BUSINESS_RERANK_CANDIDATES),
        min_score=MIN_MATCH_SCORE,
    )
    return rerank_ranked_opportunities(ranked, features=features)


def _filter_contract_alternatives(ranked, *, features, profile_strength, limit):
    accepted = []
    for opportunity in ranked:
        evidence = build_recommendation_evidence(features, opportunity, profile_strength)
        if not passes_recommendation_quality_gate(
            features=features,
            opportunity=opportunity,
            profile_strength=profile_strength,
            evidence=evidence,
        ):
            continue
        if not _has_direct_metier_evidence(evidence):
            continue
        annotate_recommendation_quality(
            opportunity,
            features=features,
            profile_strength=profile_strength,
        )
        setattr(opportunity, "score_label", CONTRACT_ALTERNATIVE_SCORE_LABEL)
        setattr(opportunity, "recommendation_mode", CONTRACT_ALTERNATIVE_MODE)
        setattr(opportunity, "contract_alternative_reason", CONTRACT_ALTERNATIVE_REASON)
        accepted.append(opportunity)
        if len(accepted) >= limit:
            break
    return accepted


def _contract_alternative_queryset(base_queryset, exclude_ids):
    queryset = base_queryset.filter(type_opportunite__in=[TypeOpportunite.EMPLOI, TypeOpportunite.STAGE])
    if exclude_ids:
        queryset = queryset.exclude(id__in=exclude_ids)
    return queryset


def _maybe_expand_internship_recommendations(
    *,
    ranked,
    base_queryset,
    user,
    profile,
    user_embedding,
    features,
    profile_state,
    profile_strength,
    opportunity_types,
    limit,
):
    if len(ranked) >= min(limit, INTERNSHIP_FALLBACK_MIN_RESULTS):
        return ranked
    if not _is_strict_internship_context(features, opportunity_types):
        return ranked

    remaining = max(0, limit - len(ranked))
    if remaining <= 0:
        return ranked

    fallback_features = _features_without_contract_preference(features)
    exclude_ids = {getattr(item, "id", None) for item in ranked}
    queryset = _contract_alternative_queryset(base_queryset, exclude_ids)
    ranked_alternatives = _rank_recommendation_queryset(
        user=user,
        profile=profile,
        user_embedding=user_embedding,
        queryset=queryset,
        features=fallback_features,
        profile_state=profile_state,
        limit=max(remaining, BUSINESS_RERANK_CANDIDATES),
    )
    alternatives = _filter_contract_alternatives(
        ranked_alternatives,
        features=fallback_features,
        profile_strength=profile_strength,
        limit=remaining,
    )
    return [*ranked, *alternatives]


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
    base_queryset = (
        Opportunite.objects
        .filter(statut=StatutOpportunite.ACTIVE)
        .annotate(application_count=Count("candidatures"))
        .order_by("-date_publication", "-id")
    )
    base_queryset = _exclude_internal_benchmark_opportunities(base_queryset)
    if followed_ids:
        base_queryset = base_queryset.exclude(id__in=followed_ids)

    queryset = base_queryset
    if opportunity_types:
        queryset = queryset.filter(type_opportunite__in=opportunity_types)

    ranked = _rank_recommendation_queryset(
        user=request.user,
        profile=profile,
        user_embedding=user_embedding,
        queryset=queryset,
        features=features,
        profile_state=profile_state,
        limit=limit,
    )
    ranked = filter_ranked_recommendations(
        ranked,
        features=features,
        profile_strength=profile_strength,
        limit=limit,
    )
    if len(ranked) < min(limit, 3):
        jobbert_features = dict(features or {})
        jobbert_features["_profile"] = profile
        jobbert_ranked = _rank_jobbert_recommendation_queryset(
            profile=profile,
            queryset=queryset,
            features=jobbert_features,
            feedback=_feedback_context(request.user),
            profile_state=profile_state,
            limit=limit,
        )
        jobbert_ranked = filter_ranked_recommendations(
            jobbert_ranked,
            features=features,
            profile_strength=profile_strength,
            limit=limit,
        )
        if jobbert_ranked:
            existing_ids = {getattr(item, "id", None) for item in ranked}
            ranked = [
                *ranked,
                *[item for item in jobbert_ranked if getattr(item, "id", None) not in existing_ids],
            ][:limit]
    ranked = _maybe_expand_internship_recommendations(
        ranked=ranked,
        base_queryset=base_queryset,
        user=request.user,
        profile=profile,
        user_embedding=user_embedding,
        features=features,
        profile_state=profile_state,
        profile_strength=profile_strength,
        opportunity_types=opportunity_types,
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

    try:
        apply_llm_hierarchy_validation_to_ranked(
            ranked,
            features=features,
            profile_text=build_user_embedding_text(features) or "",
            profile_strength=profile_strength,
            top_n=limit,
            cache_only=True,
        )
    except Exception:
        logger.exception(
            "Recommendation LLM hierarchy validation failed softly for user_id=%s",
            getattr(request.user, "pk", None),
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
    cache_key = _recommendations_cache_key(request, limit)
    if cache_key:
        cached_recommendations = cache.get(cache_key)
        if cached_recommendations is not None:
            response = Response(cached_recommendations, status=status.HTTP_200_OK)
            response["X-BidWise-Recommendations-Cache"] = "hit"
            return response

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

    if cache_key and recommendations:
        cache.set(cache_key, recommendations, timeout=RECOMMENDATIONS_CACHE_TTL_SECONDS)

    response = Response(recommendations, status=status.HTTP_200_OK)
    response["X-BidWise-Recommendations-Cache"] = "miss" if cache_key else "skip"
    return response


def _resume_match_cache_key(request, opportunity, evidence, action):
    profile = getattr(request.user, "profil", None)
    resume = evidence.get("resume") if isinstance(evidence, dict) else {}
    if not profile or not isinstance(resume, dict) or not resume.get("id"):
        return ""

    provider_signature = {
        "provider": str(getattr(settings, "LLM_PROVIDER", "") or ""),
        "ollama_model": str(getattr(settings, "OLLAMA_MODEL", "") or ""),
        "gemini_model": str(getattr(settings, "GEMINI_MODEL", "") or ""),
    }
    payload = {
        "prompt_version": RESUME_MATCH_LLM_PROMPT_VERSION,
        "user_id": getattr(request.user, "id", None),
        "profile_id": getattr(profile, "id", None),
        "resume_id": resume.get("id"),
        "resume_updated_at": resume.get("updated_at", ""),
        "opportunity_id": getattr(opportunity, "id", None),
        "opportunity_updated_at": getattr(opportunity, "date_modification", None).isoformat()
        if getattr(opportunity, "date_modification", None)
        else "",
        "action": action,
        "provider": provider_signature,
    }
    return f"ai:resume-match:{_stable_hash(payload)}"


def _deterministic_resume_match_analysis(evidence):
    match = evidence.get("match") if isinstance(evidence, dict) else {}
    opportunity = evidence.get("opportunity") if isinstance(evidence, dict) else {}
    if not isinstance(match, dict):
        match = {}
    if not isinstance(opportunity, dict):
        opportunity = {}

    status_value = str(evidence.get("status") or "") if isinstance(evidence, dict) else ""
    if status_value != READY_STATUS:
        return {
            "status": "not_ready",
            "source": "deterministic",
            "analysis_markdown": (
                "## 1. Verdict global\n"
                "Votre CV n'est pas encore pret pour une analyse complete. "
                "BidWise pourra comparer votre CV avec cette offre lorsque l'analyse du resume sera terminee.\n\n"
                "## 5. Prochaine etape\n"
                "Attendez la fin de l'analyse du CV ou importez un resume valide."
            ),
        }

    strong_items = match.get("where_strong_fit") if isinstance(match.get("where_strong_fit"), list) else []
    watch_items = match.get("what_to_watch_out_for") if isinstance(match.get("what_to_watch_out_for"), list) else []
    ats = match.get("ats") if isinstance(match.get("ats"), dict) else {}
    covered = ats.get("covered_keywords") if isinstance(ats.get("covered_keywords"), list) else []
    missing = ats.get("missing_or_weak_keywords") if isinstance(ats.get("missing_or_weak_keywords"), list) else []
    score = int(match.get("fit_score") or 0)
    verdict = str(match.get("verdict") or "unclear")
    title = str(opportunity.get("title") or "this role").strip()

    if score >= 78:
        verdict_sentence = f"Votre CV presente un bon alignement avec {title}."
    elif score >= 62:
        verdict_sentence = f"Votre CV presente un match encourageant avec {title}, avec quelques points a renforcer."
    elif score >= 45:
        verdict_sentence = f"Votre CV presente un match partiel avec {title}."
    else:
        verdict_sentence = f"Votre CV presente un alignement limite avec {title}."

    strong_lines = [
        f"- **{str(item.get('title') or 'Signal fort').strip()}** — {str(item.get('evidence') or '').strip()}"
        for item in strong_items[:4]
        if isinstance(item, dict)
    ]
    if not strong_lines:
        strong_lines = ["- **Signaux disponibles** — BidWise a detecte quelques elements exploitables, mais les preuves fortes restent limitees."]

    watch_lines = [
        f"- **{str(item.get('title') or 'Point a verifier').strip()}** — {str(item.get('evidence') or '').strip()}"
        for item in watch_items[:4]
        if isinstance(item, dict)
    ]
    if not watch_lines:
        watch_lines = ["- **A verifier** — Aucun gap critique n'est clairement detecte, mais adaptez le CV aux mots-cles de l'offre."]

    coverage = int(ats.get("keyword_coverage_percent") or 0)
    ats_level = "Bon" if coverage >= 70 else "Moyen" if coverage >= 40 else "Faible"
    next_steps = match.get("next_step_hints") if isinstance(match.get("next_step_hints"), list) else []
    next_step = str(next_steps[0]).strip() if next_steps else "Adaptez votre resume professionnel aux exigences principales de l'offre."

    markdown = "\n\n".join(
        [
            "## 1. Verdict global\n"
            f"{verdict_sentence} Score CV vs offre BidWise: {score}%. "
            "Cette analyse rapide utilise les signaux deja extraits de votre CV et de l'offre.",
            "## 2. Points forts — Ou vous etes un candidat solide\n" + "\n".join(strong_lines),
            "## 3. Points a surveiller — Gaps identifies\n" + "\n".join(watch_lines),
            "## 4. Analyse ATS\n"
            f"- Score ATS BidWise : {coverage}%\n"
            f"- Keywords couverts : {', '.join(covered[:10]) if covered else 'non visible dans le CV'}\n"
            f"- Keywords manquants : {', '.join(missing[:10]) if missing else 'aucun keyword critique detecte'}\n"
            f"- Niveau compatibilite ATS : {ats_level}",
            "## 5. Prochaine etape\n" + next_step,
        ]
    )

    return {
        "status": "ready",
        "source": "deterministic",
        "analysis_markdown": markdown,
        "verdict": verdict,
        "ats_level": ats_level,
        "next_step": next_step,
    }


def _get_resume_match_opportunity(opportunity_id):
    try:
        return Opportunite.objects.select_related("source").get(
            pk=int(opportunity_id),
            statut=StatutOpportunite.ACTIVE,
        )
    except (TypeError, ValueError, Opportunite.DoesNotExist):
        return None


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def resume_match_view(request, opportunity_id):
    opportunity = _get_resume_match_opportunity(opportunity_id)
    if opportunity is None:
        return Response({"detail": "Opportunity not found."}, status=status.HTTP_404_NOT_FOUND)

    evidence = build_resume_match_evidence(user=request.user, opportunity=opportunity)
    deterministic = _deterministic_resume_match_analysis(evidence)
    return Response(
        {
            "status": evidence.get("status"),
            "has_resume": bool(evidence.get("has_resume")),
            "resume_status": evidence.get("resume_status", ""),
            "evidence": evidence,
            "deterministic_analysis": deterministic,
            "can_generate_ai_analysis": evidence.get("status") == READY_STATUS,
            "suggested_actions": [
                {"key": "full_fit_analysis", "label": "Full AI analysis"},
                {"key": "optimize_cv", "label": "Optimize my CV for this role"},
                {"key": "rewrite_summary", "label": "Rewrite professional summary"},
                {"key": "generate_cover_letter", "label": "Generate motivation letter"},
                {"key": "interview_prep", "label": "Interview preparation"},
            ],
        },
        status=status.HTTP_200_OK,
    )


class ResumeMatchAIThrottle(UserRateThrottle):
    scope = "resume_match_ai"


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([ResumeMatchAIThrottle])
def resume_match_action_view(request, opportunity_id):
    action = str(request.data.get("action") or "").strip()
    if action not in {"full_fit_analysis", "optimize_cv", "rewrite_summary", "generate_cover_letter", "interview_prep"}:
        return Response(
            {"action": ["Unsupported action. Use full_fit_analysis, optimize_cv, rewrite_summary, generate_cover_letter, or interview_prep."]},
            status=status.HTTP_400_BAD_REQUEST,
        )

    opportunity = _get_resume_match_opportunity(opportunity_id)
    if opportunity is None:
        return Response({"detail": "Opportunity not found."}, status=status.HTTP_404_NOT_FOUND)

    evidence = build_resume_match_evidence(user=request.user, opportunity=opportunity)
    deterministic = _deterministic_resume_match_analysis(evidence)
    if evidence.get("status") != READY_STATUS:
        return Response(
            {
                "status": evidence.get("status"),
                "has_resume": bool(evidence.get("has_resume")),
                "resume_status": evidence.get("resume_status", ""),
                "evidence": evidence,
                "analysis": deterministic,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    cache_key = _resume_match_cache_key(request, opportunity, evidence, action)
    if cache_key:
        cached = cache.get(cache_key)
        if cached is not None:
            response = Response(cached, status=status.HTTP_200_OK)
            response["X-BidWise-Resume-Match-Cache"] = "hit"
            return response

    try:
        if action == "optimize_cv":
            analysis = generate_resume_optimization(evidence)
        elif action == "rewrite_summary":
            analysis = generate_summary_rewrite(evidence)
        elif action == "generate_cover_letter":
            analysis = generate_cover_letter(evidence)
        elif action == "interview_prep":
            analysis = generate_interview_prep(evidence)
        else:
            analysis = generate_resume_match_analysis(evidence)
    except ResumeMatchLLMError as exc:
        logger.warning(
            "Resume match LLM failed user_id=%s opportunity_id=%s reason=%s",
            getattr(request.user, "id", None),
            getattr(opportunity, "id", None),
            exc,
        )
        if action in {"optimize_cv", "rewrite_summary", "generate_cover_letter", "interview_prep"}:
            return Response(
                {
                    "status": "fallback",
                    "source": "llm",
                    "error": str(exc),
                    "evidence": evidence,
                    "analysis": None,
                },
                status=status.HTTP_200_OK,
            )
        response_payload = {
            "status": "fallback",
            "source": "deterministic",
            "error": str(exc),
            "evidence": evidence,
            "analysis": deterministic,
        }
        return Response(response_payload, status=status.HTTP_200_OK)

    response_payload = {
        "status": "ready",
        "action": action,
        "evidence": evidence,
        "analysis": analysis,
    }
    if cache_key:
        cache.set(cache_key, response_payload, timeout=RESUME_MATCH_LLM_CACHE_TTL_SECONDS)

    response = Response(response_payload, status=status.HTTP_200_OK)
    response["X-BidWise-Resume-Match-Cache"] = "miss" if cache_key else "skip"
    return response
