from __future__ import annotations

from typing import Any

from opportunities.normalization.text import clean_display_text, dedupe_texts
from .resume_parsing import MAX_PARSED_TEXT_CHARS, clean_resume_text, parse_resume_file
from .resume_parsing.exceptions import ResumeParsingError


def extract_resume_text(uploaded_file: Any) -> str:
    """
    Compatibility wrapper for callers that still need direct text extraction.

    New uploads are parsed asynchronously by users.parse_profile_resume. This
    wrapper intentionally swallows parsing errors so request/response code never
    crashes because of a malformed resume.
    """
    try:
        return parse_resume_file(uploaded_file).text
    except ResumeParsingError:
        return ""
    except Exception:
        return ""


def build_resume_text_embedding_source(profile: Any, parsed_text: str = "") -> str:
    """
    Prepare a deterministic text source for future resume embeddings without
    generating embeddings in this layer.
    """
    parts = [
        getattr(profile, "prenom", ""),
        getattr(profile, "nom", ""),
        getattr(profile, "niveau_experience", ""),
        " ".join(dedupe_texts(getattr(profile, "target_roles", []) or [])),
        " ".join(dedupe_texts(getattr(profile, "competences", []) or [])),
        " ".join(dedupe_texts(getattr(profile, "domaines_interet", []) or [])),
        parsed_text,
    ]
    return clean_resume_text(
        clean_display_text(" ".join(str(part) for part in parts if part)),
        max_length=MAX_PARSED_TEXT_CHARS,
    )


__all__ = ["build_resume_text_embedding_source", "extract_resume_text"]
