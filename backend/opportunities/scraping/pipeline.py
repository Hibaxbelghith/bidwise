import hashlib
import json
import logging
import re
import unicodedata

from django.db.models import F
from django.utils import timezone

from opportunities.models import (
    RawOpportunite,
    RawOpportuniteProcessingStatus,
    SourceOpportunite,
)
from opportunities.scraping.scraper_utils import canonicalize_source_item_url


logger = logging.getLogger(__name__)


def _normalize_text_for_fingerprint(value):
    if not value:
        return ""
    cleaned = unicodedata.normalize("NFKD", str(value))
    cleaned = "".join(ch for ch in cleaned if not unicodedata.combining(ch))
    cleaned = cleaned.lower()
    cleaned = re.sub(r"[^a-z0-9\s]", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def _build_content_fingerprint(raw_record):
    title = _as_text(raw_record.get("titre") or raw_record.get("title"))
    description = _as_text(raw_record.get("description"))
    normalized_title = _normalize_text_for_fingerprint(title)[:100]
    normalized_description = _normalize_text_for_fingerprint(description)[:500]
    payload = f"{normalized_title}|{normalized_description}".strip("|")
    if not payload:
        return ""
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def _build_payload_hash(raw_record):
    serialized = json.dumps(raw_record, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha1(serialized.encode("utf-8")).hexdigest()


def _as_text(value):
    if value is None:
        return ""
    return str(value).strip()


def _get_or_create_source(source_cache, *, name, url, type_source):
    source = source_cache.get(name)
    if source is None:
        source, _ = SourceOpportunite.objects.get_or_create(
            nom=name,
            defaults={"url": url, "type_source": type_source},
        )
        source_cache[name] = source

    source_updated = False
    if source.url != url:
        source.url = url
        source_updated = True
    if source.type_source != type_source:
        source.type_source = type_source
        source_updated = True
    if source_updated:
        source.save(update_fields=["url", "type_source"])

    return source


def _shadow_store_raw_record(raw_record, source, *, payload_hash, content_fingerprint):
    raw_data = {
        "raw_payload": raw_record,
        "raw_titre": _as_text(raw_record.get("titre") or raw_record.get("title")),
        "raw_description": _as_text(raw_record.get("raw_description") or raw_record.get("description")),
        "raw_organisation_nom": _as_text(
            raw_record.get("organisation_nom")
            or raw_record.get("organisation")
            or raw_record.get("organization")
        ),
        "raw_type": _as_text(raw_record.get("type_opportunite") or raw_record.get("type")),
        "raw_status": _as_text(raw_record.get("statut") or raw_record.get("status")),
        "raw_date_publication": _as_text(raw_record.get("date_publication") or raw_record.get("publication_date")),
        "raw_date_limite": _as_text(raw_record.get("date_limite") or raw_record.get("deadline")),
        "source_item_url": canonicalize_source_item_url(
            raw_record.get("source_item_url") or raw_record.get("item_url") or raw_record.get("url")
        ),
        "source_listing_url": raw_record.get("source_listing_url") or raw_record.get("listing_url"),
        "source_record_id": _as_text(
            raw_record.get("source_record_id") or raw_record.get("record_id") or raw_record.get("external_id")
        )
        or None,
        "payload_hash": payload_hash,
        "content_fingerprint": content_fingerprint,
    }

    # Use DB-backed identity keys when available. This gives us strong dedup
    # guarantees on source_record_id / source_item_url without changing the
    # existing canonical Opportunite flow yet.
    identity_lookup = None
    if raw_data["source_item_url"]:
        identity_lookup = {
            "source": source,
            "source_item_url": raw_data["source_item_url"],
        }
    elif raw_data["source_record_id"]:
        identity_lookup = {
            "source": source,
            "source_record_id": raw_data["source_record_id"],
        }

    if identity_lookup:
        raw_opportunity, created = RawOpportunite.objects.get_or_create(
            defaults={
                **raw_data,
                "processing_status": RawOpportuniteProcessingStatus.NEW,
            },
            **identity_lookup,
        )
        if created:
            return raw_opportunity, True, payload_hash
    else:
        # payload_hash is still a best-effort fallback because it is not backed
        # by a unique DB constraint. We reuse the newest matching row if found.
        raw_opportunity = RawOpportunite.objects.filter(
            source=source,
            payload_hash=payload_hash,
        ).order_by("-last_seen_at", "-id").first()
        if raw_opportunity is None:
            raw_opportunity = RawOpportunite.objects.create(
                source=source,
                processing_status=RawOpportuniteProcessingStatus.NEW,
                **raw_data,
            )
            return raw_opportunity, True, payload_hash

    update_values = {
        field: value
        for field, value in raw_data.items()
        if getattr(raw_opportunity, field) != value
    }

    impactful_fields = {
        "raw_payload",
        "raw_titre",
        "raw_description",
        "raw_organisation_nom",
        "raw_type",
        "raw_status",
        "raw_date_publication",
        "raw_date_limite",
        "source_item_url",
        "source_listing_url",
        "source_record_id",
        "payload_hash",
        "content_fingerprint",
    }
    if any(field in update_values for field in impactful_fields):
        # Re-queue updated raw snapshots so canonical data can be refreshed.
        update_values["processing_status"] = RawOpportuniteProcessingStatus.NEW
        update_values["validation_errors"] = []
        update_values["processed_at"] = None

    # Never downgrade processing state or overwrite canonical linkage during
    # shadow ingestion. Only refresh raw snapshots and bump freshness counters.
    update_values["seen_count"] = F("seen_count") + 1
    update_values["last_seen_at"] = timezone.now()
    RawOpportunite.objects.filter(pk=raw_opportunity.pk).update(**update_values)
    raw_opportunity.refresh_from_db()
    return raw_opportunity, False, payload_hash


def run_collection(scraper, organisation=None):
    """
    Collect raw records and persist them into RawOpportunite only.
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
    source_cache = {}

    for raw in scraper.collect():
        payload_hash = _build_payload_hash(raw)
        content_fingerprint = _build_content_fingerprint(raw)

        try:
            raw_source = _get_or_create_source(
                source_cache,
                name=default_source["name"],
                url=default_source["url"],
                type_source=default_source["type_source"],
            )
            _, created, _ = _shadow_store_raw_record(
                raw,
                raw_source,
                payload_hash=payload_hash,
                content_fingerprint=content_fingerprint,
            )
            if created:
                stats["created"] += 1
            else:
                stats["updated"] += 1
        except Exception:
            stats["skipped"] += 1
            stats["errors"].append(f"raw_ingestion_failed:{payload_hash}")
            logger.exception(
                "Raw opportunity shadow-ingestion failed for source=%s payload_hash=%s",
                scraper.source_name,
                payload_hash,
            )

    logger.info(
        "Collection finished for source=%s (created=%s, updated=%s, skipped=%s)",
        scraper.source_name,
        stats["created"],
        stats["updated"],
        stats["skipped"],
    )
    return stats
