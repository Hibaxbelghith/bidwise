from __future__ import annotations

import re
import unicodedata


WHITESPACE_RE = re.compile(r"\s+")
CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")


def clean_resume_semantic_text(value: str | None, *, max_chars: int = 12000) -> str:
    text = CONTROL_RE.sub(" ", str(value or ""))
    text = unicodedata.normalize("NFKC", text)
    text = WHITESPACE_RE.sub(" ", text).strip()
    if len(text) > max_chars:
        text = text[:max_chars].rstrip()
    return text
