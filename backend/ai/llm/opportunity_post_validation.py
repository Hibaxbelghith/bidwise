from __future__ import annotations

import re
import unicodedata
from dataclasses import replace
from typing import Iterable

from ai.business_families import normalize_family_set
from opportunities.models import Opportunite

from .schemas import LLMExtractionResult


SOFT_SKILL_KEYS = {
    "autonomie",
    "communication",
    "confidentialite",
    "confidentialité",
    "discretion",
    "discrétion",
    "diplomatie",
    "dynamique",
    "esprit d'equipe",
    "esprit d'équipe",
    "motivation",
    "organisation",
    "professionnalisme",
    "reactivite",
    "réactivité",
    "relationnel",
    "rigueur",
    "serieux",
    "sérieux",
}

ACTION_SKILL_KEYS = {
    "diagnostiquer",
    "resoudre incidents",
    "résoudre incidents",
    "installer",
    "mettre a jour",
    "mettre à jour",
    "securiser",
    "sécuriser",
}

FAMILY_RULES = (
    (
        "healthcare",
        (
            "cabinet medical",
            "cabinet dentaire",
            "endodontie",
            "medical",
            "medicale",
            "médical",
            "médicale",
            "patient",
            "patients",
            "clinique",
            "sante",
            "santé",
            "pharmacie",
            "infirmier",
            "infirmiere",
            "infirmière",
        ),
    ),
    (
        "administration",
        (
            "assistante administrative",
            "assistant administratif",
            "administrative et financiere",
            "administrative et financière",
            "secretaire",
            "secrétaire",
            "secretariat",
            "secrétariat",
            "gestion administrative",
            "accueil",
            "rendez-vous",
            "planning",
            "dossiers",
            "classement",
            "archivage",
        ),
    ),
    (
        "accounting_finance_audit",
        (
            "finance",
            "financiere",
            "financière",
            "facturation",
            "comptabilite",
            "comptabilité",
            "comptable",
            "banque",
            "fournisseurs",
            "budget",
        ),
    ),
    (
        "hr_administration",
        (
            "ressources humaines",
            "recrutement",
            "dossiers rh",
            "contrats de travail",
            "absences",
            "conges",
            "congés",
            "paie",
        ),
    ),
    (
        "customer_support",
        (
            "teleconseiller",
            "téléconseiller",
            "conseiller clientele",
            "conseiller clientèle",
            "service client",
            "support client",
            "assistance client",
            "satisfaction client",
            "fidelisation client",
            "fidélisation client",
            "portefeuille client",
            "centre d'appel",
            "call center",
            "hotline",
        ),
    ),
    (
        "it_network_support",
        (
            "support informatique",
            "technicien support",
            "helpdesk",
            "systemes et reseaux",
            "systèmes et réseaux",
            "maintenance informatique",
            "active directory",
            "tcp/ip",
            "windows",
            "wan",
            "lan",
        ),
    ),
)


def _norm(value: object) -> str:
    text = str(value or "").casefold()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join(text.replace("’", "'").split())


def _contains_any(text: str, terms: Iterable[str]) -> bool:
    for term in terms:
        normalized = _norm(term)
        if not normalized:
            continue
        if len(normalized) <= 3 and normalized.isalnum():
            if re.search(rf"(?<!\w){re.escape(normalized)}(?!\w)", text):
                return True
            continue
        if normalized in text:
            return True
    return False


def _source_values(opportunity: Opportunite, result: LLMExtractionResult) -> list[str]:
    extra_data = getattr(opportunity, "extra_data", None)
    extra_values = []
    if isinstance(extra_data, dict):
        extra_values = [
            extra_data.get("company_sector"),
            extra_data.get("sector"),
            extra_data.get("secteur"),
            extra_data.get("industry"),
        ]
    return [
        getattr(opportunity, "titre", ""),
        getattr(opportunity, "description", ""),
        getattr(opportunity, "organisation_nom", ""),
        result.canonical_role,
        *result.target_roles,
        *result.domains,
        *result.responsibilities,
        *result.requirements,
        *extra_values,
    ]


def _role_values(opportunity: Opportunite, result: LLMExtractionResult) -> list[str]:
    return [
        getattr(opportunity, "titre", ""),
        getattr(opportunity, "description", ""),
        getattr(opportunity, "organisation_nom", ""),
        result.canonical_role,
        *result.target_roles,
        *result.responsibilities,
        *result.requirements,
    ]


def _evidence_text(opportunity: Opportunite, result: LLMExtractionResult) -> str:
    return _norm(" ".join(str(value or "") for value in _source_values(opportunity, result)))


def _role_evidence_text(opportunity: Opportunite, result: LLMExtractionResult) -> str:
    return _norm(" ".join(str(value or "") for value in _role_values(opportunity, result)))


def _dedupe(values: Iterable[str], *, limit: int = 20) -> list[str]:
    output = []
    seen = set()
    for value in values:
        label = str(value or "").strip()
        key = _norm(label)
        if not label or key in seen:
            continue
        seen.add(key)
        output.append(label)
        if len(output) >= limit:
            break
    return output


def _post_validated_families(
    result: LLMExtractionResult,
    opportunity: Opportunite,
) -> tuple[list[str], float, list[str]]:
    text = _evidence_text(opportunity, result)
    role_text = _role_evidence_text(opportunity, result)
    families = list(normalize_family_set(result.business_families))
    warnings = list(result.warnings)

    evidence_families = []
    for family, terms in FAMILY_RULES:
        evidence_text = role_text if family == "customer_support" else text
        if _contains_any(evidence_text, terms):
            evidence_families.append(family)

    CUSTOMER_SUPPORT_STRONG_SIGNALS = (
        "teleconseiller",
        "téléconseiller",
        "centre d'appel",
        "call center",
        "service client",
        "support client",
        "assistance client",
        "satisfaction client",
        "fidelisation client",
        "fidélisation client",
        "portefeuille client",
        "hotline",
        "conseiller clientele",
        "conseiller clientèle",
    )
    explicit_customer_support = _contains_any(role_text, CUSTOMER_SUPPORT_STRONG_SIGNALS)

    # Ne jamais ajouter customer_support via evidence_families sans signal fort
    if not explicit_customer_support and "customer_support" in evidence_families:
        evidence_families = [f for f in evidence_families if f != "customer_support"]
        warnings.append("post_validation_blocked_customer_support_evidence_no_signal")

    for family in evidence_families:
        if family not in families:
            families.append(family)
            warnings.append(f"post_validation_added_family:{family}")

    # Retire customer_support (injecté par LLM) si aucun signal fort
    ADMIN_FINANCE_HR_FAMILIES = {"accounting_finance_audit", "administration", "hr_administration", "healthcare"}
    dominant_non_cs = ADMIN_FINANCE_HR_FAMILIES.intersection(set(families))
    if "customer_support" in families and not explicit_customer_support:
        families = [f for f in families if f != "customer_support"]
        warnings.append("post_validation_removed_customer_support_without_evidence")
    elif "customer_support" in families and dominant_non_cs and not explicit_customer_support:
        families = [f for f in families if f != "customer_support"]
        warnings.append("post_validation_removed_customer_support_dominated_by_admin_finance")

    has_medical_admin = "healthcare" in evidence_families and "administration" in evidence_families
    has_hr_evidence = "hr_administration" in evidence_families or _contains_any(
        text,
        ("ressources humaines", "recrutement", "dossiers rh", "contrats de travail", "paie"),
    )
    if has_medical_admin and not has_hr_evidence and "hr_administration" in families:
        families = [family for family in families if family != "hr_administration"]
        warnings.append("post_validation_removed_hr_for_medical_admin")

    strong_accounting_evidence = _contains_any(
        text,
        (
            "finance",
            "financiere",
            "financière",
            "comptabilite",
            "comptabilité",
            "comptable",
            "banque",
            "fournisseurs",
            "budget",
            "audit",
        ),
    )
    if has_medical_admin and "accounting_finance_audit" in families and not strong_accounting_evidence:
        families = [family for family in families if family != "accounting_finance_audit"]
        warnings.append("post_validation_removed_accounting_for_medical_admin")

    if "accounting_finance_audit" in families and "administration" in evidence_families:
        if "administration" not in families:
            families.append("administration")
            warnings.append("post_validation_added_family:administration")

    if not families:
        families = ["other"]
    if len(families) > 1 and "other" in families:
        families = [family for family in families if family != "other"]

    family_confidence = float(result.family_confidence or 0.0)
    if evidence_families:
        family_confidence = max(family_confidence, 0.8)
    if any(warning.startswith("post_validation_removed_") for warning in warnings):
        family_confidence = min(family_confidence, 0.85)

    return _dedupe(families, limit=4), family_confidence, _dedupe(warnings, limit=12)


def _post_validated_skills(result: LLMExtractionResult) -> tuple[list[str], list[str], list[str]]:
    skills = list(result.skills)
    soft_skills = []
    warnings = list(result.warnings)

    for soft_skill in result.soft_skills:
        key = _norm(soft_skill)
        if key in ACTION_SKILL_KEYS:
            skills.append(soft_skill)
            warnings.append(f"post_validation_moved_action_to_skill:{soft_skill}")
            continue
        soft_skills.append(soft_skill)

    soft_keys = {_norm(value) for value in soft_skills}
    filtered_skills = []
    for skill in skills:
        key = _norm(skill)
        if key in SOFT_SKILL_KEYS:
            if key not in soft_keys:
                soft_skills.append(skill)
                soft_keys.add(key)
            warnings.append(f"post_validation_moved_soft_skill:{skill}")
            continue
        filtered_skills.append(skill)

    return _dedupe(filtered_skills, limit=12), _dedupe(soft_skills, limit=10), _dedupe(warnings, limit=12)


def post_validate_opportunity_enrichment(
    result: LLMExtractionResult,
    opportunity: Opportunite,
) -> LLMExtractionResult:
    skills, soft_skills, skill_warnings = _post_validated_skills(result)
    intermediate = replace(result, skills=skills, soft_skills=soft_skills, warnings=skill_warnings)
    families, family_confidence, family_warnings = _post_validated_families(intermediate, opportunity)
    return replace(
        intermediate,
        business_families=families,
        family_confidence=family_confidence,
        warnings=family_warnings,
    )
