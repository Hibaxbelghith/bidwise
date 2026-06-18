from __future__ import annotations

import re
import unicodedata


WHITESPACE_RE = re.compile(r"\s+")
CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")
SECTION_HEADER_RE = re.compile(
    r"^\s*(?P<title>[A-ZÀÂÄÇÉÈÊËÎÏÔÖÙÛÜŸ][^\n]{0,80})\s*$",
    re.MULTILINE,
)
HIGH_VALUE_SECTION_RE = re.compile(
    r"technologies?|outils?|tools?|skills?|comp[eé]tences?|stack|langages?|languages?",
    re.IGNORECASE,
)
PROFILE_SECTION_RE = re.compile(
    r"profil|r[eé]sum[eé]|resume|summary|about|objectif|pr[eé]sentation",
    re.IGNORECASE,
)


def _collapse_whitespace(value: str) -> str:
    return WHITESPACE_RE.sub(" ", value).strip()


def _split_resume_sections(text: str) -> list[tuple[str, str]]:
    matches = [
        match
        for match in SECTION_HEADER_RE.finditer(text)
        if _looks_like_section_header(match.group("title"))
    ]
    if not matches:
        return [("", text)]

    sections: list[tuple[str, str]] = []
    if matches[0].start() > 0:
        sections.append(("", text[: matches[0].start()]))

    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        header = match.group("title").strip()
        sections.append((header, text[start:end]))
    return sections


def _looks_like_section_header(value: str) -> bool:
    title = value.strip()
    if not title:
        return False
    words = re.findall(r"[\w&/+.-]+", title, flags=re.UNICODE)
    if len(words) > 6:
        return False
    if len(title) > 80:
        return False
    return True


def _section_priority(section: tuple[str, str]) -> int:
    header, body = section
    searchable = f"{header}\n{body[:160]}"
    if HIGH_VALUE_SECTION_RE.search(searchable):
        return 0
    if PROFILE_SECTION_RE.search(searchable):
        return 1
    return 2


def _truncate_resume_text(text: str, *, max_chars: int) -> str:
    if len(_collapse_whitespace(text)) <= max_chars:
        return text

    sections = _split_resume_sections(text)
    ordered_sections = sorted(enumerate(sections), key=lambda item: (_section_priority(item[1]), item[0]))
    kept: list[str] = []
    budget = max_chars

    for _, (_, body) in ordered_sections:
        normalized_body = _collapse_whitespace(body)
        if not normalized_body:
            continue
        separator_cost = 1 if kept else 0
        if budget <= separator_cost:
            break
        available = budget - separator_cost
        if len(normalized_body) <= available:
            kept.append(normalized_body)
            budget -= len(normalized_body) + separator_cost
            continue
        kept.append(normalized_body[:available].rstrip())
        break

    return " ".join(kept)


def clean_resume_semantic_text(value: str | None, *, max_chars: int = 12000) -> str:
    text = CONTROL_RE.sub(" ", str(value or ""))
    text = unicodedata.normalize("NFKC", text)
    text = _truncate_resume_text(text, max_chars=max_chars)
    text = _collapse_whitespace(text)
    if len(text) > max_chars:
        text = text[:max_chars].rstrip()
    return text
