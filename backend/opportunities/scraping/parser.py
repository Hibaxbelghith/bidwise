from datetime import datetime

from opportunities.models import StatutOpportunite, TypeOpportunite
from opportunities.nlp_preprocessing import extract_organization, prepare_text_for_nlp
from opportunities.utils.text_cleaning import clean_text


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


def _clean_text(value):
    if value is None:
        return ""
    return str(value).strip()


def _parse_date(value, field_name):
    if not value:
        return None

    if hasattr(value, "isoformat"):
        return value

    as_text = str(value).strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(as_text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Invalid date format for '{field_name}': {value}")


def _resolve_organisation_nom(raw_record, raw_titre, raw_description):
    explicit_org = _clean_text(
        raw_record.get("organisation_nom")
        or raw_record.get("organization")
        or raw_record.get("organisation_name")
        or raw_record.get("organization_name")
        or raw_record.get("company")
        or raw_record.get("employer")
    )
    if explicit_org:
        normalized = _clean_text(explicit_org)
        if normalized and normalized.lower() != "unknown":
            return normalized

    inferred = extract_organization(f"{raw_titre} {raw_description}")
    inferred = _clean_text(inferred)
    if inferred and inferred.lower() != "unknown":
        return inferred
    return ""


def normalize_opportunity(raw_record, default_source):
    # Normalize and sanitize user-facing text before persistence.
    raw_titre = clean_text(raw_record.get("titre") or raw_record.get("title"))
    raw_description = clean_text(raw_record.get("description"))
    organisation_nom = _resolve_organisation_nom(raw_record, raw_titre, raw_description)

    # NLP-oriented cleaning (embedding-ready) with safe fallback for ingestion stability.
    titre = prepare_text_for_nlp(raw_titre) or raw_titre
    description = prepare_text_for_nlp(raw_description) or raw_description
    if not titre or not description:
        raise ValueError("Missing required fields: title/description")

    raw_type = _clean_text(raw_record.get("type_opportunite") or raw_record.get("opportunity_type")).lower()
    type_opportunite = TYPE_MAP.get(raw_type, TypeOpportunite.EMPLOI)

    raw_status = _clean_text(raw_record.get("statut") or raw_record.get("status")).lower()
    statut = STATUS_MAP.get(raw_status, StatutOpportunite.ACTIVE)

    date_publication = _parse_date(
        raw_record.get("date_publication") or raw_record.get("publication_date"),
        "date_publication",
    )
    if not date_publication:
        raise ValueError("Missing required field: date_publication")

    date_limite = _parse_date(
        raw_record.get("date_limite") or raw_record.get("deadline"),
        "date_limite",
    )

    source_name = _clean_text(raw_record.get("source_name")) or default_source["name"]
    source_url = _clean_text(raw_record.get("source_url")) or default_source["url"]
    source_type = _clean_text(raw_record.get("source_type")) or default_source["type_source"]

    return {
        "titre": titre,
        "description": description,
        "type_opportunite": type_opportunite,
        "statut": statut,
        "date_publication": date_publication,
        "date_limite": date_limite,
        # Keep owner key for backward compatibility; scraping should not assign owners.
        "organisation": None,
        "organisation_nom": organisation_nom,
        "source_name": source_name,
        "source_url": source_url,
        "source_type": source_type,
    }
