from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import logging
from typing import Any

from django.db import models
from django.utils import timezone

from ai.hierarchy import HierarchyValidation
from ai.llm.providers import (
    LLMProvider,
    LLMProviderError,
    LLMProviderUnavailable,
    LLMTransientProviderError,
    get_llm_provider,
)


logger = logging.getLogger(__name__)


HIERARCHY_VALIDATION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "is_compatible": {"type": "boolean"},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "issue": {
            "type": "string",
            "enum": [
                "none",
                "seniority_gap",
                "responsibility_gap",
                "qualification_gap",
                "overqualified_scope",
                "unclear",
            ],
        },
        "reason": {"type": "string", "maxLength": 280},
    },
    "required": ["is_compatible", "confidence", "issue", "reason"],
}

VALID_ISSUES = {
    "none",
    "seniority_gap",
    "responsibility_gap",
    "qualification_gap",
    "overqualified_scope",
    "unclear",
}

DEFAULT_HIERARCHY_DECISION_TTL_DAYS = 30


@dataclass(frozen=True)
class LLMHierarchyValidation:
    is_compatible: bool
    confidence: float
    issue: str
    reason: str
    provider: str = ""
    model: str = ""
    cache_key: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _hierarchy_payload(
    hierarchy_validation: dict[str, Any] | HierarchyValidation | None,
) -> dict[str, Any]:
    if isinstance(hierarchy_validation, HierarchyValidation):
        return hierarchy_validation.as_debug().get("hierarchy_validation", {})
    if isinstance(hierarchy_validation, dict):
        return hierarchy_validation
    return {}


def build_hierarchy_validation_cache_key(
    *,
    profile_text: str,
    opportunity_id: Any,
    hierarchy_validation: dict[str, Any] | HierarchyValidation | None,
    opportunity_content_hash: str = "",
) -> str:
    raw = json.dumps(
        {
            "profile_text": str(profile_text or "").strip(),
            "opportunity_id": str(opportunity_id or ""),
            "opportunity_content_hash": str(opportunity_content_hash or ""),
            "hierarchy_validation": _hierarchy_payload(hierarchy_validation),
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_profile_hash(profile_text: str) -> str:
    return hashlib.sha256(str(profile_text or "").strip().encode("utf-8")).hexdigest()


def build_opportunity_content_hash(
    *,
    opportunity_title: str,
    opportunity_description: str = "",
    opportunity_skills: list[str] | None = None,
) -> str:
    raw = json.dumps(
        {
            "title": " ".join(str(opportunity_title or "").split()),
            "description": " ".join(str(opportunity_description or "").split()),
            "skills": sorted(str(skill).strip() for skill in (opportunity_skills or []) if str(skill or "").strip()),
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def get_cached_hierarchy_decision(cache_key: str) -> LLMHierarchyValidation | None:
    from ai.models import LLMHierarchyDecision

    now = timezone.now()
    decision = (
        LLMHierarchyDecision.objects.filter(cache_key=cache_key)
        .filter(models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=now))
        .first()
    )
    if decision is None:
        return None
    LLMHierarchyDecision.objects.filter(pk=decision.pk).update(
        hit_count=models.F("hit_count") + 1,
        last_accessed_at=now,
    )
    return LLMHierarchyValidation(
        is_compatible=decision.is_compatible,
        confidence=decision.confidence,
        issue=decision.issue,
        reason=decision.reason,
        provider=decision.provider,
        model=decision.model,
        cache_key=decision.cache_key,
    )


def store_hierarchy_decision(
    *,
    cache_key: str,
    profile_text: str,
    opportunity_id: Any,
    opportunity_content_hash: str,
    hierarchy_validation: dict[str, Any] | HierarchyValidation | None,
    result: LLMHierarchyValidation,
    ttl_days: int = DEFAULT_HIERARCHY_DECISION_TTL_DAYS,
) -> None:
    from ai.models import LLMHierarchyDecision
    from opportunities.models import Opportunite

    expires_at = timezone.now() + timezone.timedelta(days=max(1, int(ttl_days)))
    opportunity_pk = int(opportunity_id) if str(opportunity_id or "").isdigit() else None
    if opportunity_pk is not None and not Opportunite.objects.filter(pk=opportunity_pk).exists():
        opportunity_pk = None
    LLMHierarchyDecision.objects.update_or_create(
        cache_key=cache_key,
        defaults={
            "profile_hash": build_profile_hash(profile_text),
            "opportunity_id": opportunity_pk,
            "opportunity_content_hash": opportunity_content_hash,
            "provider": result.provider,
            "model": result.model,
            "is_compatible": result.is_compatible,
            "confidence": result.confidence,
            "issue": result.issue,
            "reason": result.reason,
            "hierarchy_payload": _hierarchy_payload(hierarchy_validation),
            "response_payload": result.as_dict(),
            "expires_at": expires_at,
        },
    )


def build_hierarchy_validation_prompt(
    *,
    profile_text: str,
    opportunity_title: str,
    opportunity_description: str = "",
    opportunity_skills: list[str] | None = None,
    hierarchy_validation: dict[str, Any] | HierarchyValidation | None = None,
) -> str:
    skills = [str(skill).strip() for skill in (opportunity_skills or []) if str(skill or "").strip()]
    description = " ".join(str(opportunity_description or "").split())[:1800]
    return (
        "Tu es un expert RH specialise dans la validation de recommandations d'emploi.\n"
        "Ta mission est limitee: evaluer uniquement la compatibilite hierarchique entre un profil candidat "
        "et une offre. Ne reevalue pas la similarite metier generale, car elle est deja calculee par JobBERT.\n\n"
        "Criteres a verifier:\n"
        "- seniorite: stage, junior, confirme, senior, lead, expert;\n"
        "- responsabilite: contributeur, chef d'equipe, superviseur, responsable, manager/directeur;\n"
        "- qualification: Bac+2, Bac+3, Bac+5, ingenieur, technicien;\n"
        "- surqualification: le profil peut etre au-dessus du scope de l'offre.\n\n"
        "Reponds uniquement en JSON valide avec ces champs:\n"
        "{\n"
        '  "is_compatible": true/false,\n'
        '  "confidence": 0.0-1.0,\n'
        '  "issue": "none|seniority_gap|responsibility_gap|qualification_gap|overqualified_scope|unclear",\n'
        '  "reason": "explication courte"\n'
        "}\n\n"
        "Regles de coherence obligatoires:\n"
        '- si "is_compatible" est true, alors "issue" doit etre "none";\n'
        '- si "issue" est un gap, alors "is_compatible" doit etre false;\n'
        '- si les signaux sont contradictoires ou incomplets, utilise "issue": "unclear".\n\n'
        f"PROFIL CANDIDAT:\n{profile_text.strip()}\n\n"
        f"OFFRE:\nTitre: {opportunity_title.strip()}\n"
        f"Competences: {', '.join(skills[:16]) if skills else 'non precisees'}\n"
        f"Description: {description or 'non precisee'}\n\n"
        "DIAGNOSTIC REGLES EXISTANT:\n"
        f"{json.dumps(_hierarchy_payload(hierarchy_validation), ensure_ascii=False, sort_keys=True)}\n"
    )


def _coerce_confidence(value: Any) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, confidence))


def normalize_llm_hierarchy_response(
    payload: dict[str, Any],
    *,
    provider_name: str = "",
    model: str = "",
    cache_key: str = "",
) -> LLMHierarchyValidation:
    issue = str(payload.get("issue") or "unclear").strip()
    if issue not in VALID_ISSUES:
        issue = "unclear"
    is_compatible = bool(payload.get("is_compatible"))
    if is_compatible and issue != "none":
        issue = "unclear"
        is_compatible = False
    reason = " ".join(str(payload.get("reason") or "").split())[:280]
    return LLMHierarchyValidation(
        is_compatible=is_compatible,
        confidence=_coerce_confidence(payload.get("confidence")),
        issue=issue,
        reason=reason or "No explanation provided by LLM.",
        provider=provider_name,
        model=model,
        cache_key=cache_key,
    )


def validate_hierarchy_with_llm(
    *,
    profile_text: str,
    opportunity_id: Any,
    opportunity_title: str,
    opportunity_description: str = "",
    opportunity_skills: list[str] | None = None,
    hierarchy_validation: dict[str, Any] | HierarchyValidation | None = None,
    provider: LLMProvider | None = None,
) -> LLMHierarchyValidation:
    opportunity_content_hash = build_opportunity_content_hash(
        opportunity_title=opportunity_title,
        opportunity_description=opportunity_description,
        opportunity_skills=opportunity_skills,
    )
    cache_key = build_hierarchy_validation_cache_key(
        profile_text=profile_text,
        opportunity_id=opportunity_id,
        hierarchy_validation=hierarchy_validation,
        opportunity_content_hash=opportunity_content_hash,
    )
    llm_provider = provider or get_llm_provider()
    prompt = build_hierarchy_validation_prompt(
        profile_text=profile_text,
        opportunity_title=opportunity_title,
        opportunity_description=opportunity_description,
        opportunity_skills=opportunity_skills,
        hierarchy_validation=hierarchy_validation,
    )
    try:
        payload = llm_provider.generate_json(prompt, schema=HIERARCHY_VALIDATION_SCHEMA)
    except (LLMProviderUnavailable, LLMTransientProviderError, LLMProviderError):
        logger.exception("LLM hierarchy validation failed opportunity_id=%s", opportunity_id)
        raise
    return normalize_llm_hierarchy_response(
        payload,
        provider_name=getattr(llm_provider, "provider_name", ""),
        model=getattr(llm_provider, "model", ""),
        cache_key=cache_key,
    )
