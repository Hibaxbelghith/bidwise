import re
from typing import Any

from opportunities.scraping.scraper_utils import (
    classify_source_item_url,
    normalize_organization_name,
)

DATE_CONFIDENCE_EXACT = "EXACT"
DATE_CONFIDENCE_ESTIMATED = "ESTIMATED"
DATE_CONFIDENCE_FALLBACK = "FALLBACK"
DATE_CONFIDENCE_VALUES = {
    DATE_CONFIDENCE_EXACT,
    DATE_CONFIDENCE_ESTIMATED,
    DATE_CONFIDENCE_FALLBACK,
}

_MONTH_YEAR_RE = re.compile(r"\b([A-Za-z\u00C0-\u017F]{3,12})\s*,?\s*(20\d{2})\b")
_FULL_DATE_PATTERNS = (
    re.compile(r"^\d{4}-\d{2}-\d{2}$"),
    re.compile(r"^\d{4}/\d{2}/\d{2}$"),
    re.compile(r"^\d{2}/\d{2}/\d{4}$"),
    re.compile(r"^\d{2}-\d{2}-\d{4}$"),
    re.compile(r"^\d{2}\.\d{2}\.\d{4}$"),
)


def normalize_date_confidence(value: Any) -> str:
    text = "" if value is None else str(value).strip().upper()
    if text in DATE_CONFIDENCE_VALUES:
        return text
    return DATE_CONFIDENCE_FALLBACK


def infer_date_confidence(raw_value: Any) -> str:
    text = "" if raw_value is None else str(raw_value).strip()
    if not text:
        return DATE_CONFIDENCE_FALLBACK

    if "T" in text and len(text) >= 10 and text[:4].isdigit():
        return DATE_CONFIDENCE_EXACT

    lowered = text.lower()
    for pattern in _FULL_DATE_PATTERNS:
        if pattern.match(lowered):
            return DATE_CONFIDENCE_EXACT

    if _MONTH_YEAR_RE.search(text):
        return DATE_CONFIDENCE_ESTIMATED

    return DATE_CONFIDENCE_FALLBACK


def _description_quality_score(description: str) -> float:
    length = len((description or "").strip())
    if length >= 250:
        return 1.0
    if length >= 120:
        return 0.85
    if length >= 80:
        return 0.7
    if length >= 40:
        return 0.55
    return 0.0


def _date_quality_score(date_confidence: str) -> float:
    normalized = normalize_date_confidence(date_confidence)
    if normalized == DATE_CONFIDENCE_EXACT:
        return 1.0
    if normalized == DATE_CONFIDENCE_ESTIMATED:
        return 0.6
    return 0.3


def compute_quality_score(
    *,
    organisation_nom: str,
    ville: str,
    description: str,
    source_item_url: str,
    date_confidence: str,
) -> float:
    normalized_org = normalize_organization_name(organisation_nom)
    if not normalized_org:
        org_score = 0.0
    elif re.search(r"\bentreprise\s+anonyme\b", normalized_org, flags=re.IGNORECASE):
        org_score = 0.35
    else:
        org_score = 1.0
    city_score = 1.0 if (ville or "").strip() else 0.0
    description_score = _description_quality_score(description)
    url_score = 1.0 if classify_source_item_url(source_item_url) == "detail_like" else 0.0
    date_score = _date_quality_score(date_confidence)

    score = (
        (0.30 * org_score)
        + (0.20 * city_score)
        + (0.20 * description_score)
        + (0.20 * url_score)
        + (0.10 * date_score)
    )

    if score < 0.0:
        return 0.0
    if score > 1.0:
        return 1.0
    return round(score, 4)
