from __future__ import annotations

import re
from typing import Any, Iterable

from opportunities.normalization.text import (
    clean_display_text,
    dedupe_texts,
    detect_language,
    normalize_lookup_key,
)


INDUSTRY_MAX_ALIASES = 16
INDUSTRY_SPLIT_RE = re.compile(r"\s*[,;|/]\s*")


CANONICAL_INDUSTRIES = (
    "HEALTHCARE",
    "FINTECH",
    "ECOMMERCE",
    "AI",
    "EDUCATION",
    "TOURISM",
    "SAAS",
    "CYBERSECURITY",
    "LOGISTICS",
    "INDUSTRY",
    "TELECOM",
)


INDUSTRY_ALIAS_PAIRS: tuple[tuple[str, str], ...] = (
    ("healthcare", "HEALTHCARE"),
    ("health", "HEALTHCARE"),
    ("sante", "HEALTHCARE"),
    ("santé", "HEALTHCARE"),
    ("pharmacie", "HEALTHCARE"),
    ("pharmaceutical", "HEALTHCARE"),
    ("pharma", "HEALTHCARE"),
    ("hopitaux", "HEALTHCARE"),
    ("hôpitaux", "HEALTHCARE"),
    ("hospital", "HEALTHCARE"),
    ("medical", "HEALTHCARE"),
    ("equipements medicaux", "HEALTHCARE"),
    ("équipements médicaux", "HEALTHCARE"),
    ("fintech", "FINTECH"),
    ("finance", "FINTECH"),
    ("financial", "FINTECH"),
    ("banque", "FINTECH"),
    ("banking", "FINTECH"),
    ("assurance", "FINTECH"),
    ("insurance", "FINTECH"),
    ("finance digitale", "FINTECH"),
    ("paiement", "FINTECH"),
    ("payments", "FINTECH"),
    ("ecommerce", "ECOMMERCE"),
    ("e commerce", "ECOMMERCE"),
    ("e-commerce", "ECOMMERCE"),
    ("commerce electronique", "ECOMMERCE"),
    ("commerce électronique", "ECOMMERCE"),
    ("marketplace", "ECOMMERCE"),
    ("retail online", "ECOMMERCE"),
    ("ai", "AI"),
    ("ia", "AI"),
    ("artificial intelligence", "AI"),
    ("intelligence artificielle", "AI"),
    ("machine learning", "AI"),
    ("education", "EDUCATION"),
    ("éducation", "EDUCATION"),
    ("enseignement", "EDUCATION"),
    ("edtech", "EDUCATION"),
    ("tourism", "TOURISM"),
    ("tourisme", "TOURISM"),
    ("hotellerie", "TOURISM"),
    ("hôtellerie", "TOURISM"),
    ("travel", "TOURISM"),
    ("voyage", "TOURISM"),
    ("saas", "SAAS"),
    ("software as a service", "SAAS"),
    ("logiciel cloud", "SAAS"),
    ("cybersecurity", "CYBERSECURITY"),
    ("cyber security", "CYBERSECURITY"),
    ("cybersecurite", "CYBERSECURITY"),
    ("cybersécurité", "CYBERSECURITY"),
    ("securite informatique", "CYBERSECURITY"),
    ("sécurité informatique", "CYBERSECURITY"),
    ("logistics", "LOGISTICS"),
    ("logistique", "LOGISTICS"),
    ("supply chain", "LOGISTICS"),
    ("transport", "LOGISTICS"),
    ("industry", "INDUSTRY"),
    ("industrie", "INDUSTRY"),
    ("industrial", "INDUSTRY"),
    ("manufacturing", "INDUSTRY"),
    ("fabrication", "INDUSTRY"),
    ("usine", "INDUSTRY"),
    ("architecture", "INDUSTRY"),
    ("immobilier", "INDUSTRY"),
    ("btp", "INDUSTRY"),
    ("genie civil", "INDUSTRY"),
    ("gÃ©nie civil", "INDUSTRY"),
    ("construction", "INDUSTRY"),
    ("travaux", "INDUSTRY"),
    ("agriculture", "INDUSTRY"),
    ("agroalimentaire", "INDUSTRY"),
    ("agro alimentaire", "INDUSTRY"),
    ("agro-alimentaire", "INDUSTRY"),
    ("environnement", "INDUSTRY"),
    ("telecom", "TELECOM"),
    ("telecoms", "TELECOM"),
    ("telecommunications", "TELECOM"),
    ("télécommunications", "TELECOM"),
    ("telecommunication", "TELECOM"),
    ("télécommunication", "TELECOM"),
)


INTEREST_NOISE_KEYS = {
    normalize_lookup_key(value)
    for value in (
        "mission",
        "missions",
        "poste",
        "postes",
        "profil",
        "urgent",
        "hiring",
        "remote",
        "tunis",
        "commercial",
        "machines",
        "machine",
        "secteur",
        "sector",
    )
}


def _normalize_alias_pairs(pairs: Iterable[tuple[str, str]]) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for alias, canonical in pairs:
        alias_key = normalize_lookup_key(alias)
        canonical_key = normalize_lookup_key(canonical)
        if alias_key and canonical in CANONICAL_INDUSTRIES:
            aliases[alias_key] = canonical
        if canonical_key and canonical in CANONICAL_INDUSTRIES:
            aliases.setdefault(canonical_key, canonical)
    return aliases


INTEREST_ALIAS_MAP = _normalize_alias_pairs(INDUSTRY_ALIAS_PAIRS)
KNOWN_INTEREST_KEYS = set(INTEREST_ALIAS_MAP) | {
    normalize_lookup_key(value) for value in CANONICAL_INDUSTRIES
}


def canonicalize_industry(value: Any) -> str | None:
    key = normalize_lookup_key(value)
    if not key or key in INTEREST_NOISE_KEYS:
        return None
    return INTEREST_ALIAS_MAP.get(key)


def is_known_industry(value: Any) -> bool:
    key = normalize_lookup_key(value)
    return key in KNOWN_INTEREST_KEYS or canonicalize_industry(key) is not None


def industry_alias_keys_for(canonical: Any) -> list[str]:
    canonical_key = normalize_lookup_key(canonical)
    if not canonical_key:
        return []
    aliases = [
        key
        for key, alias_canonical in INTEREST_ALIAS_MAP.items()
        if normalize_lookup_key(alias_canonical) == canonical_key
    ]
    return [key for key in dict.fromkeys(aliases) if key][:INDUSTRY_MAX_ALIASES]


def _iter_industry_candidates(values: Any) -> Iterable[str]:
    if values is None:
        return
    if isinstance(values, str):
        for part in INDUSTRY_SPLIT_RE.split(values):
            part = clean_display_text(part, max_length=120)
            if part:
                yield part
        text = clean_display_text(values, max_length=240)
        if text:
            yield text
        return
    if isinstance(values, dict):
        for key in ("company_sector", "sector", "industry", "industries"):
            yield from _iter_industry_candidates(values.get(key))
        return
    if isinstance(values, (list, tuple, set)):
        for item in values:
            yield from _iter_industry_candidates(item)
        return
    text = clean_display_text(values, max_length=120)
    if text:
        yield text


def normalize_industries(values: Any) -> list[str]:
    canonical_values: list[str] = []
    for candidate in _iter_industry_candidates(values):
        canonical = canonicalize_industry(candidate)
        if not canonical:
            continue
        canonical_values.append(canonical)
    return dedupe_texts(canonical_values)


def industry_language(value: Any) -> str:
    return detect_language(value)


__all__ = [
    "CANONICAL_INDUSTRIES",
    "INTEREST_ALIAS_MAP",
    "KNOWN_INTEREST_KEYS",
    "canonicalize_industry",
    "industry_alias_keys_for",
    "industry_language",
    "is_known_industry",
    "normalize_industries",
]
