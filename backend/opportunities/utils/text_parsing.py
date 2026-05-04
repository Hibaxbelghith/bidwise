import re
import unicodedata
from typing import Any


EXPERIENCE_STRUCTURED_MAP = {
    "aucune experience": (0, 0),
    "moins d un an": (0, 1),
    "entre 1 et 2 ans": (1, 2),
    "entre 2 et 5 ans": (2, 5),
    "entre 5 et 10 ans": (5, 10),
    "plus que 10 ans": (10, None),
}

EXPERIENCE_LESS_THAN_ONE_YEAR_TOKEN = "moins d un an"

EXPERIENCE_RANGE_RE = re.compile(
    r"(?:entre\s*)?(\d+)\s*(?:ans|years)?\s*(?:a|-|et)\s*(\d+)\s*(?:ans|years)\b",
    flags=re.IGNORECASE,
)
EXPERIENCE_SINGLE_RE = re.compile(r"(\d+)\s*(?:ans|years)\b", flags=re.IGNORECASE)
EXPERIENCE_LESS_THAN_RE = re.compile(r"<\s*(\d+)\s*(?:ans|years)\b", flags=re.IGNORECASE)
EXPERIENCE_BEGINNER_RE = re.compile(r"debutant\s*(\d+)\s*(?:ans|years)\b", flags=re.IGNORECASE)
EXPERIENCE_MORE_THAN_RE = re.compile(
    r"(?:plus(?:\s+que)?\s*|>\s*)(\d+)\s*(?:ans|years)\b",
    flags=re.IGNORECASE,
)


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).replace("\xa0", " ")).strip()


def normalize_token(value: Any) -> str:
    text = normalize_text(value).lower()
    if not text:
        return ""

    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _experience_search_text(value: Any) -> str:
    text = normalize_text(value).lower()
    if not text:
        return ""

    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _normalize_experience_bounds(
    minimum: int | None,
    maximum: int | None,
) -> tuple[int | None, int | None]:
    if minimum is not None and maximum is not None and minimum > maximum:
        return maximum, minimum
    if minimum is None and maximum is not None:
        return maximum, maximum
    return minimum, maximum


def parse_experience_bounds(value: Any) -> tuple[int | None, int | None]:
    text = normalize_text(value)
    if not text:
        return None, None

    token = normalize_token(text)
    if not token:
        return None, None

    mapped = EXPERIENCE_STRUCTURED_MAP.get(token)
    if mapped is not None:
        return mapped

    search_text = _experience_search_text(text)
    minimum_candidates: list[int] = []
    maximum_candidates: list[int] = []
    has_open_ended = False
    has_match = False

    if EXPERIENCE_LESS_THAN_ONE_YEAR_TOKEN in token:
        minimum_candidates.append(0)
        maximum_candidates.append(1)
        has_match = True

    for range_match in EXPERIENCE_RANGE_RE.finditer(search_text):
        try:
            first = int(range_match.group(1))
            second = int(range_match.group(2))
        except (TypeError, ValueError):
            continue
        minimum_candidates.append(min(first, second))
        maximum_candidates.append(max(first, second))
        has_match = True

    for less_than_match in EXPERIENCE_LESS_THAN_RE.finditer(search_text):
        try:
            upper = int(less_than_match.group(1))
        except (TypeError, ValueError):
            continue
        minimum_candidates.append(0)
        maximum_candidates.append(upper)
        has_match = True

    for beginner_match in EXPERIENCE_BEGINNER_RE.finditer(token):
        try:
            upper = int(beginner_match.group(1))
        except (TypeError, ValueError):
            continue
        minimum_candidates.append(0)
        maximum_candidates.append(upper)
        has_match = True

    for more_than_match in EXPERIENCE_MORE_THAN_RE.finditer(search_text):
        try:
            lower = int(more_than_match.group(1))
        except (TypeError, ValueError):
            continue
        minimum_candidates.append(lower)
        has_open_ended = True
        has_match = True

    if not has_match:
        single_match = EXPERIENCE_SINGLE_RE.search(search_text)
        if single_match:
            try:
                years = int(single_match.group(1))
            except (TypeError, ValueError):
                return None, None
            minimum_candidates.append(years)
            maximum_candidates.append(years)
            has_match = True

    if not has_match:
        return None, None

    minimum = min(minimum_candidates) if minimum_candidates else None
    maximum = None if has_open_ended else max(maximum_candidates) if maximum_candidates else None
    return _normalize_experience_bounds(minimum, maximum)
