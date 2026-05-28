from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


SEMANTIC_RESUME_VERSION = "semantic-cv-v3"
SEMANTIC_STATUS_PENDING = "PENDING"
SEMANTIC_STATUS_PROCESSING = "PROCESSING"
SEMANTIC_STATUS_SUCCEEDED = "SUCCEEDED"
SEMANTIC_STATUS_EMPTY = "EMPTY"
SEMANTIC_STATUS_FAILED = "FAILED"
SEMANTIC_STATUS_SKIPPED = "SKIPPED"


@dataclass(frozen=True)
class SkillCandidate:
    text: str
    source: str
    confidence: float = 0.0
    start: int | None = None
    end: int | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "source": self.source,
            "confidence": round(float(self.confidence or 0.0), 4),
            "start": self.start,
            "end": self.end,
        }


@dataclass(frozen=True)
class ResumeSemanticSignals:
    skills: list[str] = field(default_factory=list)
    domains: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    business_families: list[str] = field(default_factory=list)
    family_confidence: float = 0.0
    canonical_role: str = ""
    target_roles: list[str] = field(default_factory=list)
    languages_detected: list[str] = field(default_factory=list)
    semantic_confidence: float = 0.0
    llm_enrichment: dict[str, Any] = field(default_factory=dict)
    raw_candidates: list[SkillCandidate] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def has_structured_signal(self) -> bool:
        return bool(
            self.skills
            or self.domains
            or self.tools
            or (self.business_families and self.family_confidence >= 0.75)
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "skills": self.skills,
            "domains": self.domains,
            "tools": self.tools,
            "business_families": self.business_families,
            "family_confidence": round(float(self.family_confidence or 0.0), 4),
            "canonical_role": self.canonical_role,
            "target_roles": self.target_roles,
            "languages_detected": self.languages_detected,
            "semantic_confidence": round(float(self.semantic_confidence or 0.0), 4),
            "llm_enrichment": self.llm_enrichment,
            "raw_candidates": [candidate.as_dict() for candidate in self.raw_candidates],
            "warnings": self.warnings,
        }
