import logging
import re
from datetime import date, datetime
from typing import Any

from opportunities.models import RawOpportunite, StatutOpportunite, TypeOpportunite
from opportunities.scraping.quality import infer_date_confidence, normalize_date_confidence
from opportunities.scraping.scraper_utils import (
    infer_city_from_text,
    infer_organization_from_text,
    infer_organization_from_title,
    looks_closed_opportunity,
    normalize_organization_name,
)


logger = logging.getLogger(__name__)


FALLBACK_TYPE = TypeOpportunite.EMPLOI
FALLBACK_STATUS = StatutOpportunite.ACTIVE


# Canonical mapping only. Keep this deterministic and replayable.
TYPE_MAP = {
    "job": TypeOpportunite.EMPLOI,
    "emploi": TypeOpportunite.EMPLOI,
    "internship": TypeOpportunite.STAGE,
    "stage": TypeOpportunite.STAGE,
    "project": TypeOpportunite.PROJET,
    "projet": TypeOpportunite.PROJET,
    "funding": TypeOpportunite.FINANCEMENT,
    "financement": TypeOpportunite.FINANCEMENT,
    "research": TypeOpportunite.RECHERCHE,
    "recherche": TypeOpportunite.RECHERCHE,
}

STATUS_MAP = {
    "active": StatutOpportunite.ACTIVE,
    "ouverte": StatutOpportunite.ACTIVE,
    "open": StatutOpportunite.ACTIVE,
    "expired": StatutOpportunite.EXPIREE,
    "expiree": StatutOpportunite.EXPIREE,
    "archived": StatutOpportunite.ARCHIVEE,
    "archivee": StatutOpportunite.ARCHIVEE,
}

DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d")

FR_MONTHS = {
    "janvier": 1,
    "fevrier": 2,
    "février": 2,
    "mars": 3,
    "avril": 4,
    "mai": 5,
    "juin": 6,
    "juillet": 7,
    "aout": 8,
    "août": 8,
    "septembre": 9,
    "octobre": 10,
    "novembre": 11,
    "decembre": 12,
    "décembre": 12,
}

_EXPERIENCE_RANGE_RE = re.compile(
    r"(?:entre\s*)?(\d+)\s*(?:a|à|-|et)\s*(\d+)\s*(?:ans|years)\b",
    flags=re.IGNORECASE,
)
_EXPERIENCE_SINGLE_RE = re.compile(r"(\d+)\s*(?:ans|years)\b", flags=re.IGNORECASE)
_GENERIC_OPPORTUNITY_TYPE_TOKENS = set(TYPE_MAP.keys()) | {value.lower() for value in TypeOpportunite.values}

def _canonical_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().split())


def _trace_id(raw_id: int | None) -> str:
    return str(raw_id) if raw_id is not None else "unknown"


def _build_validation_error(message: str, *, raw_id: int | None) -> ValueError:
    return ValueError(f"{message} (raw_id={_trace_id(raw_id)})")


def _pick_first_non_empty(*values: Any) -> Any:
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return None


def _resolve_type(raw_type: str, *, raw_id: int | None) -> str:
    if not raw_type:
        # Policy choice: fallback is allowed only when source value is missing.
        # This stays explicit/auditable via warning logs.
        logger.warning(
            "raw_id=%s missing type_opportunite; fallback applied to '%s'. "
            "Source parser should provide an explicit type when available.",
            _trace_id(raw_id),
            FALLBACK_TYPE,
        )
        return FALLBACK_TYPE

    type_opportunite = TYPE_MAP.get(raw_type)
    if type_opportunite is None:
        logger.warning(
            "raw_id=%s unknown type_opportunite='%s'; record rejected until mapping is updated.",
            _trace_id(raw_id),
            raw_type,
        )
        raise _build_validation_error(
            f"Unknown type_opportunite value: {raw_type}",
            raw_id=raw_id,
        )

    return type_opportunite


def _resolve_status(raw_status: str, *, raw_id: int | None) -> str:
    if not raw_status:
        logger.warning(
            "raw_id=%s missing statut; fallback applied to '%s'. "
            "Source parser should provide an explicit status when available.",
            _trace_id(raw_id),
            FALLBACK_STATUS,
        )
        return FALLBACK_STATUS

    statut = STATUS_MAP.get(raw_status)
    if statut is None:
        logger.warning(
            "raw_id=%s unknown statut='%s'; record rejected until mapping is updated.",
            _trace_id(raw_id),
            raw_status,
        )
        raise _build_validation_error(
            f"Unknown statut value: {raw_status}",
            raw_id=raw_id,
        )

    return statut


def _parse_date(value: Any, field_name: str, *, raw_id: int | None) -> date | None:
    if not value:
        return None

    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    as_text = _canonical_text(value)
    if not as_text:
        return None

    try:
        # Handles ISO dates and datetimes from APIs.
        return datetime.fromisoformat(as_text.replace("Z", "+00:00")).date()
    except ValueError:
        pass

    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(as_text, fmt).date()
        except ValueError:
            continue

    fr_date = _parse_fr_long_date(as_text)
    if fr_date is not None:
        return fr_date

    logger.warning(
        "raw_id=%s invalid %s='%s'; supported formats are %s or ISO-8601.",
        _trace_id(raw_id),
        field_name,
        value,
        DATE_FORMATS,
    )
    raise _build_validation_error(
        f"Invalid date format for '{field_name}': {value}",
        raw_id=raw_id,
    )


def _parse_fr_long_date(value: str) -> date | None:
    text = _canonical_text(value).lower().replace(",", " ")
    parts = [part for part in text.split(" ") if part]
    if len(parts) < 3:
        return None

    day_token, month_token, year_token = parts[0], parts[1], parts[2]
    if not day_token.isdigit() or not year_token.isdigit():
        return None

    month = FR_MONTHS.get(month_token)
    if month is None:
        return None

    try:
        return date(int(year_token), int(month), int(day_token))
    except ValueError:
        return None


def _as_optional_text(value: Any) -> str | None:
    text = _canonical_text(value)
    return text or None


def _sanitize_contract_type(value: Any) -> str | None:
    text = _as_optional_text(value)
    if not text:
        return None

    if _canonical_text(text).lower() in _GENERIC_OPPORTUNITY_TYPE_TOKENS:
        return None

    return text


def _as_optional_languages(value: Any) -> list[str] | None:
    if not isinstance(value, list):
        return None

    items = []
    for item in value:
        cleaned = _canonical_text(item)
        if cleaned:
            items.append(cleaned)

    return items or None


def _as_display_location(value: Any) -> str:
    text = _canonical_text(value)
    if not text:
        return ""

    lowered = text.lower()
    if "www" in lowered or ".tn" in lowered:
        return ""

    parts = [part.strip() for part in text.split(",") if part and part.strip()]
    if not parts:
        return text

    cleaned_parts = []
    for part in parts:
        normalized = _canonical_text(part).lower()
        if normalized in {"tunisie", "tunisia", "tn", "république tunisienne", "republique tunisienne"}:
            continue
        cleaned_parts.append(part)

    if cleaned_parts:
        return ", ".join(cleaned_parts)
    return text


def _parse_optional_date_to_iso(value: Any) -> str | None:
    if not value:
        return None

    text = _canonical_text(value)
    if not text:
        return None

    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        pass

    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue

    fr_date = _parse_fr_long_date(text)
    if fr_date is not None:
        return fr_date.isoformat()

    return None


def _parse_experience_bounds(value: Any) -> tuple[int | None, int | None]:
    text = _canonical_text(value)
    if not text:
        return None, None

    range_match = _EXPERIENCE_RANGE_RE.search(text)
    if range_match:
        try:
            first = int(range_match.group(1))
            second = int(range_match.group(2))
        except (TypeError, ValueError):
            return None, None

        low = min(first, second)
        high = max(first, second)
        return low, high

    single_match = _EXPERIENCE_SINGLE_RE.search(text)
    if single_match:
        try:
            years = int(single_match.group(1))
            return years, years
        except (TypeError, ValueError):
            return None, None

    return None, None


def normalize_raw_opportunity(raw_obj: RawOpportunite) -> dict[str, Any]:
    """
    Convert one RawOpportunite snapshot into canonical fields.

    Separation of concerns:
    - This layer only does field mapping, date parsing, and basic text cleaning.
    - NLP is intentionally excluded so ingestion/canonicalization stay deterministic
      and replayable from raw payloads.
    """

    payload = raw_obj.raw_payload or {}
    raw_id = raw_obj.pk

    titre = _canonical_text(
        _pick_first_non_empty(
            raw_obj.raw_titre,
            payload.get("titre"),
            payload.get("title"),
        )
    )
    description = _canonical_text(
        _pick_first_non_empty(
            raw_obj.raw_description,
            payload.get("description"),
        )
    )
    if not titre or not description:
        logger.warning(
            "raw_id=%s missing required canonical text fields (titre/description); record rejected.",
            _trace_id(raw_id),
        )
        raise _build_validation_error("Missing required fields: title/description", raw_id=raw_id)

    raw_type = _canonical_text(
        _pick_first_non_empty(
            raw_obj.raw_type,
            payload.get("type_opportunite"),
            payload.get("opportunity_type"),
            payload.get("type"),
        )
    ).lower()
    type_opportunite = _resolve_type(raw_type, raw_id=raw_id)

    raw_status = _canonical_text(
        _pick_first_non_empty(
            raw_obj.raw_status,
            payload.get("statut"),
            payload.get("status"),
        )
    ).lower()
    statut = _resolve_status(raw_status, raw_id=raw_id)
    if looks_closed_opportunity(
        titre,
        description,
        payload.get("raw_description"),
        payload.get("description"),
    ):
        statut = StatutOpportunite.EXPIREE

    published_at_iso = _parse_optional_date_to_iso(payload.get("published_at"))

    raw_date_publication = _pick_first_non_empty(
        published_at_iso,
        raw_obj.raw_date_publication,
        payload.get("date_publication"),
        payload.get("publication_date"),
    )
    date_publication = _parse_date(
        raw_date_publication,
        "date_publication",
        raw_id=raw_id,
    )
    if date_publication is None:
        logger.warning(
            "raw_id=%s missing required date_publication; record rejected.",
            _trace_id(raw_id),
        )
        raise _build_validation_error("Missing required field: date_publication", raw_id=raw_id)

    raw_date_confidence = _canonical_text(
        _pick_first_non_empty(
            payload.get("date_confidence"),
            payload.get("publication_date_confidence"),
        )
    )
    date_confidence = normalize_date_confidence(raw_date_confidence or infer_date_confidence(raw_date_publication))
    if not raw_date_confidence and _parse_fr_long_date(raw_date_publication or "") is not None:
        date_confidence = "EXACT"

    date_limite = _parse_date(
        _pick_first_non_empty(
            raw_obj.raw_date_limite,
            payload.get("date_limite"),
            payload.get("deadline"),
        ),
        "date_limite",
        raw_id=raw_id,
    )

    organisation_nom = _canonical_text(
        _pick_first_non_empty(
            raw_obj.raw_organisation_nom,
            payload.get("organisation_nom"),
            payload.get("organisation_name"),
            payload.get("organization"),
            payload.get("organization_name"),
            payload.get("company"),
            payload.get("employer"),
        )
    )
    organisation_nom = normalize_organization_name(organisation_nom)
    if not organisation_nom:
        organisation_nom = infer_organization_from_title(titre)
    if not organisation_nom:
        organisation_nom = infer_organization_from_text(
            titre,
            description,
            payload.get("raw_description"),
            payload.get("description"),
        )

    ville = _canonical_text(
        _pick_first_non_empty(
            payload.get("ville"),
            payload.get("location"),
            payload.get("city"),
            payload.get("gouvernorat"),
            payload.get("region"),
            payload.get("lieu"),
        )
    )
    ville = _as_display_location(ville)
    if not ville:
        ville = infer_city_from_text(
            titre,
            description,
            payload.get("raw_description"),
            payload.get("description"),
            payload.get("url"),
            organisation_nom,
        )

    source_item_url = _canonical_text(
        _pick_first_non_empty(
            raw_obj.source_item_url,
            payload.get("source_item_url"),
            payload.get("item_url"),
            payload.get("url"),
        )
    )

    contract_type = _sanitize_contract_type(
        _pick_first_non_empty(
            payload.get("contract_type"),
            payload.get("type_contrat"),
            payload.get("contract"),
            payload.get("type_de_contrat"),
            payload.get("contractType"),
            payload.get("type"),
            payload.get("type_opportunite"),
            payload.get("opportunity_type"),
        )
    )

    experience_text = _as_optional_text(payload.get("experience"))
    experience_min, experience_max = _parse_experience_bounds(experience_text)

    structured_data = {
        "reference": _as_optional_text(payload.get("reference")),
        "published_at": published_at_iso,
        "contract_type": contract_type,
        "experience": experience_text,
        "experience_min": experience_min,
        "experience_max": experience_max,
        "education_level": _as_optional_text(payload.get("education_level")),
        "availability": _as_optional_text(payload.get("availability")),
        "salary": _as_optional_text(payload.get("salary")),
        "languages": _as_optional_languages(payload.get("languages")),
        "company_sector": _as_optional_text(payload.get("company_sector")),
        "company_size": _as_optional_text(payload.get("company_size")),
    }

    return {
        # raw_id supports end-to-end traceability across logs and replay runs.
        "raw_id": raw_id,
        "source": raw_obj.source,
        "titre": titre,
        "description": description,
        "organisation_nom": organisation_nom,
        "ville": ville,
        "source_item_url": source_item_url,
        "type_opportunite": type_opportunite,
        "statut": statut,
        "date_publication": date_publication,
        "date_confidence": date_confidence,
        "date_limite": date_limite,
        # Scraping flow should not assign owners in canonicalization.
        "organisation": None,
        **structured_data,
    }
