import logging

from opportunities.models import Opportunite, SourceOpportunite

from .parser import normalize_opportunity


logger = logging.getLogger(__name__)


def run_collection(scraper, organisation=None):
    """
    Collect raw records, normalize them, then upsert into database.
    Duplicate key policy: (titre, source, date_publication).
    """
    default_source = {
        "name": scraper.source_name,
        "url": scraper.source_url,
        "type_source": scraper.source_type,
    }

    stats = {
        "created": 0,
        "updated": 0,
        "skipped": 0,
        "errors": [],
    }

    for raw in scraper.collect():
        try:
            normalized = normalize_opportunity(raw, default_source=default_source)
        except ValueError as exc:
            stats["skipped"] += 1
            stats["errors"].append(str(exc))
            logger.warning("Invalid record skipped for source=%s: %s", scraper.source_name, exc)
            continue

        source, _ = SourceOpportunite.objects.get_or_create(
            nom=normalized["source_name"],
            defaults={
                "url": normalized["source_url"],
                "type_source": normalized["source_type"],
            },
        )

        source_updated = False
        if source.url != normalized["source_url"]:
            source.url = normalized["source_url"]
            source_updated = True
        if source.type_source != normalized["source_type"]:
            source.type_source = normalized["source_type"]
            source_updated = True
        if source_updated:
            source.save(update_fields=["url", "type_source"])

        opportunity_defaults = {
            "description": normalized["description"],
            "type_opportunite": normalized["type_opportunite"],
            "statut": normalized["statut"],
            "date_limite": normalized["date_limite"],
            "organisation": organisation if organisation is not None else normalized.get("organisation"),
            "organisation_nom": normalized.get("organisation_nom", ""),
        }

        _, created = Opportunite.objects.update_or_create(
            titre=normalized["titre"],
            source=source,
            date_publication=normalized["date_publication"],
            defaults=opportunity_defaults,
        )

        if created:
            stats["created"] += 1
        else:
            stats["updated"] += 1

    logger.info(
        "Collection finished for source=%s (created=%s, updated=%s, skipped=%s)",
        scraper.source_name,
        stats["created"],
        stats["updated"],
        stats["skipped"],
    )
    return stats
