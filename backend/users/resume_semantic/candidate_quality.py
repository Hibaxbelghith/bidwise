from __future__ import annotations

import re

from .esco_mapping import ESCO_BY_ALIAS, ESCO_BY_CANONICAL
from .models import RejectedSkillCandidate, SkillCandidate
from .normalization import NOISY_CANDIDATES, clean_resume_semantic_text, normalize_lookup_key, normalize_skill_label


MAX_CANDIDATE_TOKENS = 6
MIN_CANDIDATE_TEXT_CHARS = 2

LEADING_FRAGMENT_TOKENS = {
    "a",
    "an",
    "and",
    "as",
    "au",
    "aux",
    "avec",
    "d",
    "de",
    "des",
    "du",
    "en",
    "et",
    "for",
    "l",
    "la",
    "le",
    "les",
    "of",
    "on",
    "ou",
    "par",
    "pour",
    "sur",
    "the",
    "to",
    "un",
    "une",
    "with",
}

TRAILING_FRAGMENT_TOKENS = LEADING_FRAGMENT_TOKENS | {
    "clients",
    "projets",
}

GENERIC_BUSINESS_TERMS = {
    "application",
    "clients",
    "equipe",
    "force",
    "mission",
    "missions",
    "opportunite",
    "opportunites",
    "opportunité",
    "opportunités",
    "portfolio",
    "portefeuille",
    "poste",
    "pression",
    "projet",
    "projets",
    "suivi",
    "travail",
}

ACTION_TOKENS = {
    "analyse",
    "build",
    "concevoir",
    "create",
    "deliver",
    "develop",
    "developper",
    "développer",
    "drive",
    "gérer",
    "gerer",
    "lead",
    "manage",
    "mettre",
    "open",
    "ouvrir",
    "pilotage",
}

SENTENCE_LIKE_RE = re.compile(r"[,:;!?]| \(|\) ")

ACTION_TOKENS.update(
    {
        "analyser",
        "assister",
        "built",
        "comprend",
        "comprendre",
        "conduct",
        "creating",
        "creation",
        "developp",
        "identifier",
        "implement",
        "participa",
        "proposer",
        "proposa",
        "suivre",
        "etre",
    }
)

GENERIC_BUSINESS_TERMS.update(
    {
        "la pression",
        "a la pression",
        "quipe",
    }
)

ACTION_TOKENS.update(
    {
        "assurer",
        "maintenir",
        "prospec",
        "tre",
        "a tre",
    }
)

GENERIC_ACTION_TERMS = ACTION_TOKENS | {
    "aj",
    "deploy",
    "deploi",
    "mainten",
    "out",
    "persuasi",
    "propose",
    "si",
}

NON_SKILL_PHRASE_PATTERNS = (
    "best practices",
    "cohesive and high quality",
    "high quality solutions",
    "reusable components",
    "robust and scalable",
    "scalable systems",
    "smooth and efficient",
    "thorough testing",
)

RAW_TEXT_STOPWORDS = {
    "être",
    "à la pression",
    "équipe",
}

SAFE_LOOKUP_KEYS = frozenset(
    set(ESCO_BY_ALIAS.keys())
    | set(ESCO_BY_CANONICAL.keys())
    | {
        normalize_lookup_key(value)
        for value in (
            "Excel",
            "Photoshop",
            "SAP",
            "Tailwind",
            "Next.js",
            "Node.js",
            "React",
            "JavaScript",
            "Python",
        )
    }
)


def _tokenize(text: str) -> list[str]:
    return [token for token in normalize_lookup_key(text).split() if token]


def classify_resume_skill_candidate(candidate: SkillCandidate) -> tuple[bool, str]:
    text = clean_resume_semantic_text(candidate.text, max_chars=160)
    raw_key = text.casefold()
    normalized_key = normalize_lookup_key(text)
    token_count = len(_tokenize(text))

    if not normalized_key:
        return False, "empty_candidate"
    if raw_key in RAW_TEXT_STOPWORDS:
        return False, "generic_noise_term"
    if len(normalized_key) < MIN_CANDIDATE_TEXT_CHARS or token_count == 0:
        return False, "too_short"
    if normalized_key in SAFE_LOOKUP_KEYS:
        return True, "accepted_safe_alias"

    canonical = normalize_skill_label(text)
    if canonical and normalize_lookup_key(canonical) in SAFE_LOOKUP_KEYS:
        return True, "accepted_canonical_alias"

    tokens = normalized_key.split()
    if len(tokens) == 1 and normalized_key in NOISY_CANDIDATES:
        return False, "generic_noise_term"
    if len(tokens) == 1 and normalized_key in GENERIC_BUSINESS_TERMS:
        return False, "generic_business_term"
    if len(tokens) == 1 and normalized_key in GENERIC_ACTION_TERMS:
        return False, "generic_action_term"
    if any(pattern in normalized_key for pattern in NON_SKILL_PHRASE_PATTERNS):
        return False, "non_skill_phrase"
    if len(tokens) > MAX_CANDIDATE_TOKENS:
        return False, "phrase_too_long"
    if tokens[0] in LEADING_FRAGMENT_TOKENS:
        return False, "phrase_fragment"
    if tokens[-1] in TRAILING_FRAGMENT_TOKENS:
        return False, "phrase_fragment"
    if len(tokens) >= 2 and tokens[0] in ACTION_TOKENS:
        return False, "action_phrase"
    if len(tokens) >= 3 and sum(token in LEADING_FRAGMENT_TOKENS for token in tokens) >= 2:
        return False, "sentence_like_fragment"
    if len(tokens) >= 4 and SENTENCE_LIKE_RE.search(text):
        return False, "sentence_like_fragment"

    return True, "accepted"


def filter_resume_skill_candidates(
    candidates: list[SkillCandidate],
) -> tuple[list[SkillCandidate], list[RejectedSkillCandidate]]:
    accepted: list[SkillCandidate] = []
    rejected: list[RejectedSkillCandidate] = []
    seen = set()

    for candidate in candidates:
        text = clean_resume_semantic_text(candidate.text, max_chars=160)
        normalized_key = normalize_lookup_key(text)
        if not normalized_key:
            rejected.append(
                RejectedSkillCandidate(
                    text=text,
                    source=candidate.source,
                    reason="empty_candidate",
                    confidence=candidate.confidence,
                    normalized_key=normalized_key,
                    token_count=0,
                )
            )
            continue

        accepted_candidate, reason = classify_resume_skill_candidate(candidate)
        token_count = len(normalized_key.split())
        if not accepted_candidate:
            rejected.append(
                RejectedSkillCandidate(
                    text=text,
                    source=candidate.source,
                    reason=reason,
                    confidence=candidate.confidence,
                    normalized_key=normalized_key,
                    token_count=token_count,
                )
            )
            continue

        if normalized_key in seen:
            continue
        seen.add(normalized_key)
        accepted.append(
            SkillCandidate(
                text=text,
                source=candidate.source,
                confidence=candidate.confidence,
                start=candidate.start,
                end=candidate.end,
            )
        )

    return accepted, rejected
