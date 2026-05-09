from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any


MAX_PARSED_TEXT_CHARS = 20000

CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")
WHITESPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class CleanedResumeText:
    text: str
    truncated: bool


def clean_resume_text_result(
    value: Any,
    *,
    max_length: int = MAX_PARSED_TEXT_CHARS,
) -> CleanedResumeText:
    if value is None:
        return CleanedResumeText(text="", truncated=False)

    text = unicodedata.normalize("NFKC", str(value))
    text = text.replace("\ufeff", " ").replace("\u00a0", " ")
    text = CONTROL_CHARS_RE.sub(" ", text)
    text = WHITESPACE_RE.sub(" ", text).strip()

    truncated = len(text) > max_length
    if truncated:
        text = text[:max_length].rstrip()

    return CleanedResumeText(text=text, truncated=truncated)


def clean_resume_text(
    value: Any,
    *,
    max_length: int = MAX_PARSED_TEXT_CHARS,
) -> str:
    return clean_resume_text_result(value, max_length=max_length).text
