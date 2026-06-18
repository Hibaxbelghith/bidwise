from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from django.db.models import QuerySet
from django.db.models.functions import Length
from django.utils import timezone

from ai.business_families import opportunity_llm_business_families, opportunity_text_business_families
from opportunities.models import Opportunite, StatutOpportunite, TypeOpportunite


DEFAULT_WEAK_BENCHMARK_FAMILIES = {
    "backend",
    "data_ai",
    "devops_cloud_infrastructure",
    "hr",
    "it_network_support",
    "it_support_network",
    "legal",
    "legal_regulatory",
    "logistics_supply_chain",
    "software_web",
}

LOW_COVERAGE_SOURCE_WEIGHTS = {
    "keejob": 36,
    "emploitunisie": 28,
    "linkedin": 6,
}

NON_JOB_SOURCE_NAMES = {"marchespublics", "marches publics", "marches_publics"}


@dataclass(frozen=True)
class RecommendationStats:
    appeared_count: int = 0
    strong_count: int = 0
    related_count: int = 0
    profiles: tuple[str, ...] = ()


@dataclass(frozen=True)
class EnrichmentROI:
    opportunity_id: int
    title: str
    source: str
    priority: str
    score: float
    reasons: tuple[str, ...]
    exclusions: tuple[str, ...] = ()
    description_length: int = 0
    skill_count: int = 0
    has_llm_enrichment: bool = False
    days_until_deadline: int | None = None
    business_families: tuple[str, ...] = ()
    recommendation_stats: RecommendationStats = field(default_factory=RecommendationStats)

    @property
    def eligible(self) -> bool:
        return not self.exclusions


def _source_name(opportunity: Opportunite) -> str:
    source = getattr(opportunity, "source", None)
    return str(getattr(source, "nom", "") or "").strip()


def _source_key(opportunity: Opportunite) -> str:
    return _source_name(opportunity).casefold().replace(" ", "")


def _clean_skill_value(value: Any) -> str:
    if isinstance(value, dict):
        value = (
            value.get("canonical")
            or value.get("label")
            or value.get("name")
            or value.get("skill")
            or value.get("text")
        )
    return " ".join(str(value or "").strip().casefold().split())


def opportunity_skill_count(opportunity: Opportunite) -> int:
    values: list[Any] = []
    for attr in ("skills", "raw_skills", "normalized_skills"):
        raw = getattr(opportunity, attr, None) or []
        if isinstance(raw, (list, tuple, set)):
            values.extend(raw)
        elif raw:
            values.append(raw)
    cleaned = {_clean_skill_value(value) for value in values if _clean_skill_value(value)}
    return len(cleaned)


def has_llm_enrichment(opportunity: Opportunite) -> bool:
    extra_data = getattr(opportunity, "extra_data", None)
    return isinstance(extra_data, dict) and isinstance(extra_data.get("llm_enrichment"), dict)


def days_until_deadline(opportunity: Opportunite) -> int | None:
    deadline = getattr(opportunity, "date_limite", None)
    if not deadline:
        return None
    return (deadline - timezone.localdate()).days


def opportunity_business_families(opportunity: Opportunite) -> set[str]:
    return opportunity_llm_business_families(opportunity) or opportunity_text_business_families(
        opportunity,
        include_description=False,
    )


def score_opportunity_for_enrichment(
    opportunity: Opportunite,
    *,
    recommendation_stats: RecommendationStats | None = None,
    weak_families: set[str] | None = None,
    min_process_description_chars: int = 120,
    rich_description_chars: int = 300,
    weak_skill_threshold: int = 2,
    exclude_expiring_days: int = 7,
    job_types: set[str] | None = None,
) -> EnrichmentROI:
    stats = recommendation_stats or RecommendationStats()
    weak_families = weak_families if weak_families is not None else set(DEFAULT_WEAK_BENCHMARK_FAMILIES)
    job_types = job_types if job_types is not None else {TypeOpportunite.EMPLOI}

    description = getattr(opportunity, "description", "") or ""
    description_length = len(description)
    skill_count = opportunity_skill_count(opportunity)
    source_name = _source_name(opportunity)
    source_key = _source_key(opportunity)
    llm_enriched = has_llm_enrichment(opportunity)
    deadline_days = days_until_deadline(opportunity)
    families = opportunity_business_families(opportunity)

    exclusions: list[str] = []
    if getattr(opportunity, "statut", None) != StatutOpportunite.ACTIVE:
        exclusions.append("inactive")
    if getattr(opportunity, "type_opportunite", None) not in job_types:
        exclusions.append("non_job_type")
    if source_key in NON_JOB_SOURCE_NAMES:
        exclusions.append("non_job_source")
    if description_length < min_process_description_chars:
        exclusions.append("short_description")
    if deadline_days is not None and deadline_days <= exclude_expiring_days:
        exclusions.append("deadline_too_close")
    if llm_enriched:
        exclusions.append("already_llm_enriched")

    score = 0.0
    reasons: list[str] = []

    if description_length >= rich_description_chars and skill_count <= weak_skill_threshold and not llm_enriched:
        score += 60
        reasons.append("P1 rich description with weak skills")

    if stats.appeared_count and stats.strong_count <= 0:
        score += 38 + min(stats.related_count * 4, 16)
        reasons.append("P2 dark offer: appeared in recommendations without STRONG_MATCH")

    source_weight = LOW_COVERAGE_SOURCE_WEIGHTS.get(source_key, 0)
    if source_weight:
        score += source_weight
        reasons.append(f"P3 low coverage source: {source_name}")

    if families.intersection(weak_families):
        score += 24
        reasons.append("Weak benchmark family")

    if not llm_enriched and skill_count == 0:
        score += 8
        reasons.append("No structured skills")
    elif not llm_enriched and skill_count <= weak_skill_threshold:
        score += 4
        reasons.append("Few structured skills")

    if deadline_days is not None:
        score += max(0, min(deadline_days, 30)) / 10

    if exclusions:
        score = 0.0

    if exclusions:
        priority = "P0"
    elif "P1 rich description with weak skills" in reasons:
        priority = "P1"
    elif "P2 dark offer: appeared in recommendations without STRONG_MATCH" in reasons:
        priority = "P2"
    elif score > 0:
        priority = "P3"
    else:
        priority = "P0"

    return EnrichmentROI(
        opportunity_id=opportunity.pk,
        title=getattr(opportunity, "titre", "") or "",
        source=source_name,
        priority=priority,
        score=round(score, 2),
        reasons=tuple(reasons),
        exclusions=tuple(exclusions),
        description_length=description_length,
        skill_count=skill_count,
        has_llm_enrichment=llm_enriched,
        days_until_deadline=deadline_days,
        business_families=tuple(sorted(families)),
        recommendation_stats=stats,
    )


def base_enrichment_queryset(*, include_stages: bool = False) -> QuerySet:
    job_types = [TypeOpportunite.EMPLOI]
    if include_stages:
        job_types.append(TypeOpportunite.STAGE)
    return (
        Opportunite.objects.filter(statut=StatutOpportunite.ACTIVE, type_opportunite__in=job_types)
        .select_related("source")
        .annotate(description_length=Length("description"))
        .order_by("-date_publication", "-id")
    )


def expiring_cutoff_date(days: int):
    return timezone.localdate() + timedelta(days=max(0, int(days)))
