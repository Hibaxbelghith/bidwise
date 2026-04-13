import logging
import hashlib
import re
import unicodedata
from typing import Any

from django.db import transaction

from opportunities.models import Opportunite, StatutOpportunite, TypeOpportunite
from opportunities.scraping.quality import (
    DATE_CONFIDENCE_ESTIMATED,
    DATE_CONFIDENCE_EXACT,
    compute_quality_score,
    normalize_date_confidence,
)
from opportunities.scraping.scraper_utils import classify_source_item_url, normalize_organization_name
from opportunities.scraping.scraper_utils import canonicalize_source_item_url


logger = logging.getLogger(__name__)
MIN_DESCRIPTION_LENGTH = 40
HIINTERNS_STAGE_MIN_QUALITY_SCORE = 0.85


def _persist_text(value: Any) -> str:
    if value is None:
        return ""
    # Persistence layer must not reshape text; normalization owns canonical cleaning.
    return value if isinstance(value, str) else str(value)


def _trace_id(raw_id: Any) -> str:
    return str(raw_id) if raw_id is not None else "unknown"


def _build_validation_error(message: str, *, raw_id: Any) -> ValueError:
    return ValueError(f"{message} (raw_id={_trace_id(raw_id)})")


def _truncate(value: str, max_length: int) -> str:
    if len(value) <= max_length:
        return value
    return value[:max_length]


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    return False


def _normalize_key_text(value: Any) -> str:
    if value is None:
        return ""
    cleaned = unicodedata.normalize("NFKC", str(value)).lower()
    cleaned = "".join(ch if (ch.isalnum() or ch.isspace()) else " " for ch in cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def _clean_optional_list(value: Any, *, max_items: int = 20, max_item_length: int = 64) -> list[str]:
    if not isinstance(value, list):
        return []

    cleaned: list[str] = []
    for item in value:
        text = _persist_text(item).strip()
        if not text:
            continue
        text = _truncate(text, max_item_length)
        if text not in cleaned:
            cleaned.append(text)
        if len(cleaned) >= max_items:
            break

    return cleaned


def _merge_unique_list(existing: Any, incoming: Any) -> list[str]:
    existing_list = _clean_optional_list(existing)
    incoming_list = _clean_optional_list(incoming)

    merged = list(existing_list)
    for item in incoming_list:
        if item not in merged:
            merged.append(item)
    return merged


def _is_more_specific_location(incoming: str, existing: str) -> bool:
    incoming_text = _persist_text(incoming).strip()
    existing_text = _persist_text(existing).strip()
    if not incoming_text or not existing_text:
        return False

    if incoming_text == existing_text:
        return False

    # Prefer granular values like "Sbikha, Kairouan" over "Kairouan".
    if "," in incoming_text and "," not in existing_text:
        normalized_incoming = _normalize_key_text(incoming_text)
        normalized_existing = _normalize_key_text(existing_text)
        if normalized_existing and normalized_existing in normalized_incoming:
            return True

    return False


def _to_optional_non_negative_int(value: Any) -> int | None:
    try:
        parsed = int(value) if value is not None else None
    except (TypeError, ValueError):
        return None

    if parsed is None or parsed < 0:
        return None
    return parsed


def _build_external_id(source_item_url: str) -> str:
    url = canonicalize_source_item_url(source_item_url)
    if not url:
        return ""
    return hashlib.sha1(url.encode("utf-8")).hexdigest()


def _merge_duplicate_fields(opportunity: Opportunite, defaults: dict[str, Any]) -> list[str]:
    update_fields = []

    def _confidence_rank(value: Any) -> int:
        normalized = normalize_date_confidence(value)
        if normalized == DATE_CONFIDENCE_EXACT:
            return 3
        if normalized == DATE_CONFIDENCE_ESTIMATED:
            return 2
        return 1

    incoming_description = defaults.get("description", "")
    if len(incoming_description or "") > len(opportunity.description or ""):
        opportunity.description = incoming_description
        update_fields.append("description")

    incoming_description_html = _persist_text(defaults.get("description_html", "")).strip()
    if len(incoming_description_html) > len(_persist_text(getattr(opportunity, "description_html", "")).strip()):
        opportunity.description_html = incoming_description_html
        update_fields.append("description_html")

    incoming_ville = defaults.get("ville", "")
    if not opportunity.ville and incoming_ville:
        opportunity.ville = incoming_ville
        update_fields.append("ville")
    elif _is_more_specific_location(incoming_ville, opportunity.ville):
        opportunity.ville = incoming_ville
        update_fields.append("ville")

    source_obj = defaults.get("source") or getattr(opportunity, "source", None)
    source_name = _persist_text(getattr(source_obj, "nom", "")).strip().lower()
    is_keejob_source = source_name == "keejob"

    incoming_status = defaults.get("statut")
    def _status_rank(value: Any) -> int:
        if value == StatutOpportunite.EXPIREE:
            return 3
        if value == StatutOpportunite.ARCHIVEE:
            return 2
        if value == StatutOpportunite.ACTIVE:
            return 1
        return 0

    if incoming_status:
        if is_keejob_source:
            if incoming_status != opportunity.statut:
                opportunity.statut = incoming_status
                update_fields.append("statut")
        elif _status_rank(incoming_status) > _status_rank(opportunity.statut):
            opportunity.statut = incoming_status
            update_fields.append("statut")

    incoming_deadline = defaults.get("date_limite")
    if opportunity.date_limite is None and incoming_deadline is not None:
        opportunity.date_limite = incoming_deadline
        update_fields.append("date_limite")

    incoming_source_item_url = _persist_text(defaults.get("source_item_url", "")).strip()
    if incoming_source_item_url and not _persist_text(getattr(opportunity, "source_item_url", "")).strip():
        opportunity.source_item_url = incoming_source_item_url
        update_fields.append("source_item_url")

    incoming_external_id = _persist_text(defaults.get("external_id", "")).strip()
    if incoming_external_id and not _persist_text(getattr(opportunity, "external_id", "")).strip():
        opportunity.external_id = incoming_external_id
        update_fields.append("external_id")

    incoming_company_logo = _persist_text(defaults.get("company_logo", "")).strip()
    current_company_logo = _persist_text(getattr(opportunity, "company_logo", "")).strip()
    if incoming_company_logo and incoming_company_logo != current_company_logo:
        opportunity.company_logo = incoming_company_logo
        update_fields.append("company_logo")

    incoming_contract_type = _persist_text(defaults.get("contract_type", "")).strip()
    if incoming_contract_type and not _persist_text(getattr(opportunity, "contract_type", "")).strip():
        opportunity.contract_type = incoming_contract_type
        update_fields.append("contract_type")

    incoming_owner = defaults.get("organisation")
    if opportunity.organisation_id is None and incoming_owner is not None:
        opportunity.organisation = incoming_owner
        update_fields.append("organisation")

    incoming_confidence = normalize_date_confidence(defaults.get("date_confidence"))
    if _confidence_rank(incoming_confidence) > _confidence_rank(opportunity.date_confidence):
        opportunity.date_confidence = incoming_confidence
        update_fields.append("date_confidence")

    incoming_quality_score = float(defaults.get("quality_score", 0.0) or 0.0)
    if incoming_quality_score > float(opportunity.quality_score or 0.0):
        opportunity.quality_score = incoming_quality_score
        update_fields.append("quality_score")

    incoming_salary = _persist_text(defaults.get("salary", "")).strip()
    if incoming_salary and not _persist_text(getattr(opportunity, "salary", "")).strip():
        opportunity.salary = incoming_salary
        update_fields.append("salary")

    incoming_education_level = _persist_text(defaults.get("education_level", "")).strip()
    if incoming_education_level and not _persist_text(getattr(opportunity, "education_level", "")).strip():
        opportunity.education_level = incoming_education_level
        update_fields.append("education_level")

    incoming_availability = _persist_text(defaults.get("availability", "")).strip()
    if incoming_availability and not _persist_text(getattr(opportunity, "availability", "")).strip():
        opportunity.availability = incoming_availability
        update_fields.append("availability")

    incoming_experience = defaults.get("experience_years")
    current_experience = getattr(opportunity, "experience_years", None)
    if incoming_experience is not None and current_experience is None:
        opportunity.experience_years = incoming_experience
        update_fields.append("experience_years")

    seed_experience = incoming_experience if incoming_experience is not None else current_experience

    incoming_experience_min = defaults.get("experience_min")
    if incoming_experience_min is None and seed_experience is not None:
        incoming_experience_min = seed_experience
    current_experience_min = getattr(opportunity, "experience_min", None)
    if incoming_experience_min is not None and (
        current_experience_min is None or incoming_experience_min < current_experience_min
    ):
        opportunity.experience_min = incoming_experience_min
        update_fields.append("experience_min")

    incoming_experience_max = defaults.get("experience_max")
    if incoming_experience_max is None and seed_experience is not None:
        incoming_experience_max = seed_experience
    current_experience_max = getattr(opportunity, "experience_max", None)
    if incoming_experience_max is not None and (
        current_experience_max is None or incoming_experience_max > current_experience_max
    ):
        opportunity.experience_max = incoming_experience_max
        update_fields.append("experience_max")

    merged_skills = _merge_unique_list(getattr(opportunity, "skills", []), defaults.get("skills", []))
    if merged_skills != _clean_optional_list(getattr(opportunity, "skills", [])):
        opportunity.skills = merged_skills
        update_fields.append("skills")

    merged_languages = _merge_unique_list(getattr(opportunity, "languages", []), defaults.get("languages", []))
    if merged_languages != _clean_optional_list(getattr(opportunity, "languages", [])):
        opportunity.languages = merged_languages
        update_fields.append("languages")

    merged_languages_fallback = _merge_unique_list(
        getattr(opportunity, "languages_fallback", []),
        defaults.get("languages_fallback", []),
    )
    if merged_languages_fallback != _clean_optional_list(getattr(opportunity, "languages_fallback", [])):
        opportunity.languages_fallback = merged_languages_fallback
        update_fields.append("languages_fallback")

    return update_fields


def _validate_required_fields(normalized_data: dict[str, Any], *, raw_id: Any) -> None:
    required_fields = (
        "source",
        "titre",
        "description",
        "date_publication",
        "type_opportunite",
        "statut",
    )
    missing_fields = [name for name in required_fields if _is_missing(normalized_data.get(name))]
    if missing_fields:
        logger.warning(
            "raw_id=%s missing required canonical fields: %s",
            _trace_id(raw_id),
            ", ".join(missing_fields),
        )
        raise _build_validation_error(
            f"Missing required normalized fields: {', '.join(missing_fields)}",
            raw_id=raw_id,
        )


def _validate_choice(value: Any, valid_values: list[str], *, field_name: str, raw_id: Any) -> None:
    if value in valid_values:
        return

    logger.warning(
        "raw_id=%s invalid %s='%s'; expected one of %s.",
        _trace_id(raw_id),
        field_name,
        value,
        valid_values,
    )
    raise _build_validation_error(f"Invalid {field_name}: {value}", raw_id=raw_id)


def _apply_quality_policy(
    *,
    normalized_data: dict[str, Any],
    organisation_nom: str,
    ville: str,
    description: str,
    quality_score: float,
    raw_id: Any,
) -> str:
    source = normalized_data.get("source")
    source_name = getattr(source, "nom", "")
    type_opportunite = normalized_data.get("type_opportunite")
    statut = normalized_data.get("statut")
    source_item_url = _persist_text(normalized_data.get("source_item_url", "")).strip()

    if len((description or "").strip()) < MIN_DESCRIPTION_LENGTH:
        raise _build_validation_error(
            f"Low-quality description: min length is {MIN_DESCRIPTION_LENGTH}",
            raw_id=raw_id,
        )

    url_quality = classify_source_item_url(source_item_url)
    if url_quality != "detail_like":
        raise _build_validation_error(
            f"Invalid source URL quality for user redirection: {url_quality}",
            raw_id=raw_id,
        )

    if statut != StatutOpportunite.ACTIVE:
        return statut

    has_org = bool(normalize_organization_name(organisation_nom))
    has_city = bool(_normalize_key_text(ville))

    # Keejob contract for Sprint 3: organization and city must both be usable.
    if source_name == "Keejob":
        if not has_org:
            raise _build_validation_error("Missing organization for Keejob record", raw_id=raw_id)
        if not has_city:
            raise _build_validation_error("Missing city for Keejob record", raw_id=raw_id)

    # USER FEED SAFETY: stage/job cards with no company and no city are archived.
    if type_opportunite in (TypeOpportunite.STAGE, TypeOpportunite.EMPLOI) and not (has_org or has_city):
        return StatutOpportunite.ARCHIVEE

    # Keep HiInterns internships in ACTIVE feed only when quality is strict.
    if (
        source_name == "HiInterns"
        and type_opportunite == TypeOpportunite.STAGE
        and float(quality_score or 0.0) <= HIINTERNS_STAGE_MIN_QUALITY_SCORE
    ):
        return StatutOpportunite.ARCHIVEE

    # SOURCE DOMINANCE SAFETY: dominant project source with low-information cards
    # is archived to reduce recommendation and UX noise.
    if source_name == "TunisieTenders" and type_opportunite == TypeOpportunite.PROJET and not (has_org or has_city):
        return StatutOpportunite.ARCHIVEE

    return statut


def materialize_opportunity(normalized_data: dict[str, Any]) -> Opportunite:
    """
    Persist canonical data into Opportunite.

    Separation of concerns:
    - This layer does DB persistence and canonical deduplication only.
    - NLP is intentionally not executed here; enrichment belongs to later stages.
    """

    raw_id = normalized_data.get("raw_id")
    _validate_required_fields(normalized_data, raw_id=raw_id)

    _validate_choice(
        normalized_data.get("type_opportunite"),
        TypeOpportunite.values,
        field_name="type_opportunite",
        raw_id=raw_id,
    )
    _validate_choice(
        normalized_data.get("statut"),
        StatutOpportunite.values,
        field_name="statut",
        raw_id=raw_id,
    )

    titre = _persist_text(normalized_data["titre"])
    description = _persist_text(normalized_data["description"])
    if not titre or not description:
        logger.warning(
            "raw_id=%s empty titre/description at persistence stage; record rejected.",
            _trace_id(raw_id),
        )
        raise _build_validation_error(
            "Missing required normalized fields: titre/description",
            raw_id=raw_id,
        )

    titre_max_length = Opportunite._meta.get_field("titre").max_length
    if len(titre) > titre_max_length:
        logger.warning(
            "raw_id=%s titre truncated for DB safety (len=%s, max=%s).",
            _trace_id(raw_id),
            len(titre),
            titre_max_length,
        )
    titre = _truncate(titre, titre_max_length)

    organisation_nom_max_length = Opportunite._meta.get_field("organisation_nom").max_length
    organisation_nom_value = _persist_text(normalized_data.get("organisation_nom", ""))
    if len(organisation_nom_value) > organisation_nom_max_length:
        logger.warning(
            "raw_id=%s organisation_nom truncated for DB safety (len=%s, max=%s).",
            _trace_id(raw_id),
            len(organisation_nom_value),
            organisation_nom_max_length,
        )
    organisation_nom = _truncate(
        organisation_nom_value,
        organisation_nom_max_length,
    )
    fallback_company_used = False
    if not organisation_nom:
        organisation_nom = "Entreprise Anonyme"
        fallback_company_used = True

    ville_max_length = Opportunite._meta.get_field("ville").max_length
    ville_value = _persist_text(normalized_data.get("ville", ""))
    if len(ville_value) > ville_max_length:
        logger.warning(
            "raw_id=%s ville truncated for DB safety (len=%s, max=%s).",
            _trace_id(raw_id),
            len(ville_value),
            ville_max_length,
        )
    ville = _truncate(ville_value, ville_max_length)

    description_html = _persist_text(normalized_data.get("description_html", "")).strip()

    company_logo_max_length = Opportunite._meta.get_field("company_logo").max_length
    company_logo_value = _persist_text(normalized_data.get("company_logo", "")).strip()
    if len(company_logo_value) > company_logo_max_length:
        logger.warning(
            "raw_id=%s company_logo truncated for DB safety (len=%s, max=%s).",
            _trace_id(raw_id),
            len(company_logo_value),
            company_logo_max_length,
        )
    company_logo = _truncate(company_logo_value, company_logo_max_length)

    salary_max_length = Opportunite._meta.get_field("salary").max_length
    salary_value = _persist_text(normalized_data.get("salary", "")).strip()
    if len(salary_value) > salary_max_length:
        logger.warning(
            "raw_id=%s salary truncated for DB safety (len=%s, max=%s).",
            _trace_id(raw_id),
            len(salary_value),
            salary_max_length,
        )
    salary = _truncate(salary_value, salary_max_length)

    contract_type_max_length = Opportunite._meta.get_field("contract_type").max_length
    contract_type_value = _persist_text(normalized_data.get("contract_type", "")).strip()
    if len(contract_type_value) > contract_type_max_length:
        logger.warning(
            "raw_id=%s contract_type truncated for DB safety (len=%s, max=%s).",
            _trace_id(raw_id),
            len(contract_type_value),
            contract_type_max_length,
        )
    contract_type = _truncate(contract_type_value, contract_type_max_length)

    education_level_max_length = Opportunite._meta.get_field("education_level").max_length
    education_level_value = _persist_text(normalized_data.get("education_level", "")).strip()
    if len(education_level_value) > education_level_max_length:
        logger.warning(
            "raw_id=%s education_level truncated for DB safety (len=%s, max=%s).",
            _trace_id(raw_id),
            len(education_level_value),
            education_level_max_length,
        )
    education_level = _truncate(education_level_value, education_level_max_length)

    availability_max_length = Opportunite._meta.get_field("availability").max_length
    availability_value = _persist_text(normalized_data.get("availability", "")).strip()
    if len(availability_value) > availability_max_length:
        logger.warning(
            "raw_id=%s availability truncated for DB safety (len=%s, max=%s).",
            _trace_id(raw_id),
            len(availability_value),
            availability_max_length,
        )
    availability = _truncate(availability_value, availability_max_length)

    experience_min = _to_optional_non_negative_int(normalized_data.get("experience_min"))
    experience_max = _to_optional_non_negative_int(normalized_data.get("experience_max"))
    legacy_experience_years = _to_optional_non_negative_int(normalized_data.get("experience_years"))

    if experience_min is None and legacy_experience_years is not None:
        experience_min = legacy_experience_years
    if experience_max is None and legacy_experience_years is not None:
        experience_max = legacy_experience_years

    if experience_min is None and experience_max is not None:
        experience_min = experience_max
    if experience_max is None and experience_min is not None:
        experience_max = experience_min
    if experience_min is not None and experience_max is not None and experience_min > experience_max:
        experience_min, experience_max = experience_max, experience_min

    if experience_min is not None:
        legacy_experience_years = experience_min

    skills = _clean_optional_list(normalized_data.get("skills", []))
    languages = _clean_optional_list(normalized_data.get("languages", []))
    languages_fallback = _clean_optional_list(normalized_data.get("languages_fallback", []))

    source = normalized_data["source"]
    if fallback_company_used:
        logger.info(
            "fallback_company_used",
            extra={"source": getattr(source, "nom", ""), "raw_id": _trace_id(raw_id)},
        )
    date_publication = normalized_data["date_publication"]
    date_confidence = normalize_date_confidence(normalized_data.get("date_confidence"))
    source_item_url = canonicalize_source_item_url(normalized_data.get("source_item_url", ""))
    external_id = _build_external_id(source_item_url)
    incoming_quality_score = normalized_data.get("quality_score")
    if incoming_quality_score is None:
        quality_score = compute_quality_score(
            organisation_nom=organisation_nom,
            ville=ville,
            description=description,
            source_item_url=source_item_url,
            date_confidence=date_confidence,
        )
    else:
        quality_score = float(incoming_quality_score)
    quality_status = _apply_quality_policy(
        normalized_data=normalized_data,
        organisation_nom=organisation_nom,
        ville=ville,
        description=description,
        quality_score=quality_score,
        raw_id=raw_id,
    )

    defaults = {
        "description": description,
        "description_html": description_html,
        "organisation_nom": organisation_nom,
        "company_logo": company_logo,
        "ville": ville,
        "source_item_url": source_item_url or None,
        "external_id": external_id,
        "contract_type": contract_type,
        "experience_min": experience_min,
        "experience_max": experience_max,
        "education_level": education_level,
        "availability": availability,
        "salary": salary,
        "experience_years": legacy_experience_years,
        "skills": skills,
        "languages": languages,
        "languages_fallback": languages_fallback,
        "date_confidence": date_confidence,
        "quality_score": quality_score,
        "type_opportunite": normalized_data["type_opportunite"],
        "statut": quality_status,
        "date_limite": normalized_data.get("date_limite"),
        "organisation": normalized_data.get("organisation"),
    }

    # Canonical identity policy:
    # source + source_item_url is the only reliable matching key.
    # Title/company-based matching is intentionally disabled.
    with transaction.atomic():
        same_source_url = None
        if source_item_url:
            same_source_url = Opportunite.objects.select_for_update().filter(
                source=source,
                source_item_url=source_item_url,
            ).first()

        if same_source_url is None and external_id:
            same_source_url = Opportunite.objects.select_for_update().filter(
                source=source,
                external_id=external_id,
            ).first()

        if same_source_url is not None:
            update_fields = _merge_duplicate_fields(same_source_url, defaults)
            if update_fields:
                same_source_url.save(update_fields=update_fields)
            return same_source_url

        opportunity = Opportunite.objects.create(
            titre=titre,
            source=source,
            date_publication=date_publication,
            **defaults,
        )

    return opportunity
