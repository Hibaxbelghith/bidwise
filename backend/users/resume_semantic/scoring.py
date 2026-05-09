from __future__ import annotations

from statistics import mean

from .models import SkillCandidate


def semantic_confidence(
    *,
    candidates: list[SkillCandidate],
    mapped_count: int,
    text_length: int,
    language_count: int,
) -> float:
    if not candidates or not mapped_count:
        return 0.0

    candidate_confidence = mean(float(item.confidence or 0.0) for item in candidates)
    coverage = min(1.0, mapped_count / 8.0)
    text_signal = 0.20 if text_length >= 120 else 0.05
    multilingual_bonus = 0.05 if language_count > 1 else 0.0
    score = (0.55 * candidate_confidence) + (0.30 * coverage) + text_signal + multilingual_bonus
    return round(max(0.0, min(1.0, score)), 4)


def extraction_relevance_score(extracted: list[str], expected_terms: list[str]) -> float:
    if not extracted:
        return 0.0
    expected = {item.casefold() for item in expected_terms if item}
    if not expected:
        return 0.0
    hits = sum(1 for item in extracted if item.casefold() in expected)
    return round(hits / len(extracted), 4)

