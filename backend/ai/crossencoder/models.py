from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class CrossEncoderConfig:
    enabled: bool
    model_name: str
    max_candidates: int
    weight: float
    batch_size: int
    timeout_seconds: float
    max_text_chars: int
    reason_threshold: float
    local_files_only: bool


@dataclass(frozen=True)
class CrossEncoderCandidateScore:
    score: float
    raw_score: float
    metadata: dict[str, Any] = field(default_factory=dict)


class CrossEncoderUnavailable(RuntimeError):
    """Raised when the local CrossEncoder cannot be loaded or used safely."""


class CrossEncoderTimeout(CrossEncoderUnavailable):
    """Raised when CrossEncoder scoring exceeds the configured latency budget."""
