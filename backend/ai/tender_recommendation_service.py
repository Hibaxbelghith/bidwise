"""Recommendation service for calls for tender.

This module is intentionally separate from the job recommendation engine. Public
tenders are prioritized as an intelligent watch list, not as CV/job matches.
"""

from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from django.db import transaction
from django.utils import timezone

try:
    from pgvector.django import CosineDistance
except ImportError:  # pragma: no cover - depends on optional pgvector package
    CosineDistance = None

from opportunities.embeddings.service import generate_embedding
from opportunities.models import Opportunite, StatutOpportunite, TypeOpportunite

from .tender_categories import (
    TENDER_CATEGORIES,
    get_tender_category_label,
    get_tender_subcategory_label,
    get_tender_subcategory_synonyms,
)


SEMANTIC_WEIGHT = 0.45
CATEGORY_WEIGHT = 0.30
REGION_WEIGHT = 0.20
BUDGET_WEIGHT = 0.05
DEFAULT_RETRIEVAL_LIMIT = 300
MAIN_CATEGORY_ONLY_SCORE = 0.35


@dataclass(frozen=True)
class TenderPreferences:
    regions: tuple[str, ...]
    categories: tuple[dict[str, str], ...]
    max_budget: float | None = None

    @property
    def is_complete(self) -> bool:
        return bool(self.regions and self.categories)


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().split())


def _normalize_token(value: Any) -> str:
    text = _clean_text(value).lower()
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _clean_list(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    cleaned = []
    seen = set()
    for item in value:
        text = _clean_text(item)
        key = _normalize_token(text)
        if not text or not key or key in seen:
            continue
        seen.add(key)
        cleaned.append(text)
    return tuple(cleaned)


def _clean_categories(value: Any) -> tuple[dict[str, str], ...]:
    if not isinstance(value, list):
        return ()

    valid_categories = set(TENDER_CATEGORIES)
    cleaned = []
    seen = set()
    for item in value:
        if not isinstance(item, dict):
            continue
        category = _clean_text(item.get("category"))
        subcategory = _clean_text(item.get("subcategory"))
        if category not in valid_categories:
            continue
        if category != "Autre" and subcategory not in TENDER_CATEGORIES.get(category, []):
            continue
        key = (_normalize_token(category), _normalize_token(subcategory))
        if key in seen:
            continue
        seen.add(key)
        cleaned.append({"category": category, "subcategory": subcategory})
    return tuple(cleaned)


def _clean_max_budget(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if parsed < 0 or not math.isfinite(parsed):
        return None
    return parsed


def get_tender_preferences(user) -> TenderPreferences:
    try:
        profile = getattr(user, "profil", None)
    except Exception:
        profile = None
    if profile is None:
        return TenderPreferences(regions=(), categories=(), max_budget=None)

    tender_preferences = getattr(profile, "tender_preferences", {}) or {}
    if not isinstance(tender_preferences, dict):
        tender_preferences = {}

    return TenderPreferences(
        regions=_clean_list(getattr(profile, "preferred_locations", [])),
        categories=_clean_categories(tender_preferences.get("categories")),
        max_budget=_clean_max_budget(tender_preferences.get("max_budget")),
    )


def build_tender_query_text(preferences: TenderPreferences | dict[str, Any]) -> str:
    if isinstance(preferences, dict):
        preferences = TenderPreferences(
            regions=_clean_list(preferences.get("regions")),
            categories=_clean_categories(preferences.get("categories")),
            max_budget=_clean_max_budget(preferences.get("max_budget")),
        )

    parts: list[str] = []
    for item in preferences.categories:
        category = item.get("category", "")
        subcategory = item.get("subcategory", "")
        if category:
            parts.append(category)
            parts.append(get_tender_category_label(category))
        if subcategory:
            parts.append(subcategory)
            parts.append(get_tender_subcategory_label(subcategory))
            parts.extend(get_tender_subcategory_synonyms(subcategory))
    return " ".join(part for part in parts if part).strip()


def _split_type_commande(value: Any) -> tuple[str, str]:
    text = _clean_text(value)
    if not text:
        return "", ""
    if "/" not in text:
        return text, ""
    category, subcategory = text.split("/", 1)
    return _clean_text(category), _clean_text(subcategory)


def category_match(profile_categories, profile_subcategories, opportunity_type_commande) -> float:
    opportunity_category, opportunity_subcategory = _split_type_commande(opportunity_type_commande)
    if not opportunity_category:
        return 0.30

    profile_category_keys = {_normalize_token(item) for item in profile_categories if _clean_text(item)}
    profile_subcategory_keys = {_normalize_token(item) for item in profile_subcategories if _clean_text(item)}
    opportunity_category_key = _normalize_token(opportunity_category)
    opportunity_subcategory_key = _normalize_token(opportunity_subcategory)

    if opportunity_subcategory_key and opportunity_subcategory_key in profile_subcategory_keys:
        return 1.0
    if opportunity_category_key and opportunity_category_key in profile_category_keys:
        return MAIN_CATEGORY_ONLY_SCORE
    if "autre" in profile_category_keys:
        return 0.30
    return 0.0


def _region_match_score(opportunity: Opportunite, regions: tuple[str, ...]) -> tuple[float, str]:
    if not regions:
        return 0.0, ""
    extra_data = getattr(opportunity, "extra_data", {}) or {}
    region_execution = _clean_text(extra_data.get("region_execution", ""))
    opportunity_values = [region_execution] if region_execution else [getattr(opportunity, "ville", "")]
    opportunity_keys = {_normalize_token(value) for value in opportunity_values if _clean_text(value)}
    for region in regions:
        key = _normalize_token(region)
        if key and key in opportunity_keys:
            return 1.0, region
    return 0.0, ""


def _budget_fit_score(opportunity: Opportunite, max_budget: float | None) -> float:
    if max_budget is None:
        return 0.0
    extra_data = getattr(opportunity, "extra_data", {}) or {}
    for key in ("caution", "caution_tnd", "budget", "estimated_budget", "montant_caution"):
        value = _clean_max_budget(extra_data.get(key))
        if value is not None:
            return 1.0 if value <= max_budget else 0.0
    return 0.5


def _priority_label(score: float) -> str:
    if score >= 0.60:
        return "Forte priorité"
    if score >= 0.40:
        return "À surveiller"
    return "Faible priorité"


def _candidate_queryset(queryset=None):
    base_queryset = queryset if queryset is not None else Opportunite.objects.all()
    return base_queryset.filter(
        type_opportunite=TypeOpportunite.PROJET,
        statut=StatutOpportunite.ACTIVE,
        date_limite__gte=timezone.localdate(),
    )


def _score_reasons(
    *,
    category_score: float,
    region_score: float,
    matched_region: str,
    semantic_similarity: float,
    budget_score: float,
) -> list[str]:
    reasons = []
    if category_score >= 1.0:
        reasons.append("Exact tender subcategory aligned")
    elif category_score >= MAIN_CATEGORY_ONLY_SCORE:
        reasons.append("Main tender category aligned")
    elif category_score >= 0.30:
        reasons.append("Tender category unavailable; kept for review")

    if region_score > 0:
        reasons.append(f"Region aligned: {matched_region}")
    if semantic_similarity >= 0.60:
        reasons.append("High semantic similarity with tender interests")
    elif semantic_similarity >= 0.40:
        reasons.append("Relevant semantic similarity with tender interests")
    if budget_score > 0:
        reasons.append("Budget/caution compatible")
    return reasons[:3]
    

def score_tender(opportunity: Opportunite, preferences: TenderPreferences, semantic_similarity: float) -> dict[str, Any]:
    profile_categories = [item["category"] for item in preferences.categories]
    profile_subcategories = [item["subcategory"] for item in preferences.categories if item.get("subcategory")]
    type_commande = (getattr(opportunity, "extra_data", {}) or {}).get("type_commande", "")

    category_score = category_match(profile_categories, profile_subcategories, type_commande)
    region_score, matched_region = _region_match_score(opportunity, preferences.regions)
    budget_score = _budget_fit_score(opportunity, preferences.max_budget)
    semantic_score = max(0.0, min(float(semantic_similarity or 0.0), 1.0))

    # Si la catégorie est absente côté offre ET que la similarité sémantique
    # est faible, le signal région seul ne doit pas suffire à faire monter
    # une offre hors sujet. On réduit son impact dans ce cas précis.
    effective_region_score = region_score
    if category_score <= 0.30 and semantic_score < 0.30:
        effective_region_score = region_score * 0.3

    final_score = (
        (SEMANTIC_WEIGHT * semantic_score)
        + (CATEGORY_WEIGHT * category_score)
        + (REGION_WEIGHT * effective_region_score)
        + (BUDGET_WEIGHT * budget_score)
    )

    reasons = _score_reasons(
        category_score=category_score,
        region_score=effective_region_score,
        matched_region=matched_region,
        semantic_similarity=semantic_score,
        budget_score=budget_score,
    )

    return {
        "opportunity": opportunity,
        "score": round(final_score, 4),
        "priority": _priority_label(final_score),
        "reasons": reasons,
        "components": {
            "semantic_similarity": round(semantic_score, 4),
            "category_match": category_score,
            "region_match": region_score,
            "budget_fit": budget_score,
        },
    }


def _general_watch_results(queryset, limit: int) -> list[dict[str, Any]]:
    rows = queryset.order_by("date_limite", "-quality_score", "-id")[:limit]
    return [
        {
            "opportunity": opportunity,
            "score": None,
            "priority": "Veille générale",
            "reasons": ["Active tender", "Deadline upcoming"],
            "components": {},
        }
        for opportunity in rows
    ]


def _semantic_candidates(queryset, query_text: str, limit: int):
    if CosineDistance is None or not query_text:
        return []
    query_vector = generate_embedding(query_text)
    if not query_vector:
        return []

    retrieval_limit = max(limit, min(DEFAULT_RETRIEVAL_LIMIT, max(limit * 6, 50)))
    with transaction.atomic():
        rows = (
            queryset.exclude(embedding_vector_pg__isnull=True)
            .annotate(pg_distance=CosineDistance("embedding_vector_pg", query_vector))
            .order_by("pg_distance", "date_limite", "-id")[:retrieval_limit]
        )
        return [
            (opportunity, max(0.0, min(1.0 - float(opportunity.pg_distance or 1.0), 1.0)))
            for opportunity in rows
            if getattr(opportunity, "pg_distance", None) is not None
        ]


def get_tender_opportunities(user=None, queryset=None, *, limit: int = 50) -> list[dict[str, Any]]:
    candidates = _candidate_queryset(queryset)
    preferences = get_tender_preferences(user) if user is not None else TenderPreferences((), ())
    if not preferences.is_complete:
        return _general_watch_results(candidates, limit)

    query_text = build_tender_query_text(preferences)
    semantic_candidates = _semantic_candidates(candidates, query_text, limit)
    if not semantic_candidates:
        return _general_watch_results(candidates, limit)

    scored = [
        score_tender(opportunity, preferences, semantic_similarity)
        for opportunity, semantic_similarity in semantic_candidates
    ]
    scored.sort(
        key=lambda item: (
            -float(item["score"] or 0.0),
            getattr(item["opportunity"], "date_limite", None) or timezone.localdate(),
        )
    )
    return scored[:limit]


def recommend_tenders(user, limit: int = 50) -> list[dict[str, Any]]:
    return get_tender_opportunities(user=user, limit=limit)
