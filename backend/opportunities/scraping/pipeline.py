import hashlib
import json
import logging
import re
import unicodedata

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Case, F, IntegerField, Q, Value, When
from django.utils import timezone

from opportunities.models import (
    RawOpportunite,
    RawOpportuniteProcessingStatus,
    SourceOpportunite,
)
from opportunities.scraping.scraper_utils import canonicalize_source_item_url


logger = logging.getLogger(__name__)

SOURCE_CONFIG_KEYS = {
    "keejob": "keejob",
    "marchespublics": "marches_publics",
    "emploitunisie": "emploi_tn",
}


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


def _identity_filter(source, raw_data):
    source_record_id = raw_data.get("source_record_id")
    source_item_url = raw_data.get("source_item_url")
    identity_query = Q()
    if source_record_id:
        identity_query |= Q(source_record_id=source_record_id)
    if source_item_url:
        identity_query |= Q(source_item_url=source_item_url)

    if not identity_query:
        return None

    return Q(source=source) & identity_query


def _find_raw_opportunity_by_identity(source, raw_data, *, lock=False):
    identity_query = _identity_filter(source, raw_data)
    if identity_query is None:
        return None

    source_record_id = raw_data.get("source_record_id")
    source_item_url = raw_data.get("source_item_url")
    queryset = RawOpportunite.objects.filter(identity_query)
    if lock:
        queryset = queryset.select_for_update()
    identity_cases = []
    if source_record_id:
        identity_cases.append(When(source_record_id=source_record_id, then=Value(0)))
    if source_item_url:
        identity_cases.append(When(source_item_url=source_item_url, then=Value(1)))

    return (
        queryset.annotate(
            identity_rank=Case(
                *identity_cases,
                default=Value(2),
                output_field=IntegerField(),
            )
        )
        .order_by("identity_rank", "-last_seen_at", "-id")
        .first()
    )


def _drop_conflicting_identity_updates(raw_opportunity, source, update_values):
    for field in ("source_record_id", "source_item_url"):
        value = update_values.get(field)
        if not value:
            continue

        conflict = (
            RawOpportunite.objects.filter(source=source, **{field: value})
            .exclude(pk=raw_opportunity.pk)
            .only("id")
            .first()
        )
        if conflict is None:
            continue

        logger.warning(
            "Raw opportunity identity conflict skipped raw_id=%s conflict_id=%s field=%s value=%s",
            raw_opportunity.pk,
            conflict.pk,
            field,
            value,
        )
        update_values.pop(field)


def _apply_raw_opportunity_update(raw_opportunity, source, raw_data):
    update_values = {
        field: value
        for field, value in raw_data.items()
        if getattr(raw_opportunity, field) != value
    }
    _drop_conflicting_identity_updates(raw_opportunity, source, update_values)

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
    return raw_opportunity, False


def _upsert_raw_opportunity_by_identity(source, raw_data):
    with transaction.atomic():
        raw_opportunity = _find_raw_opportunity_by_identity(source, raw_data, lock=True)
        if raw_opportunity is not None:
            return _apply_raw_opportunity_update(raw_opportunity, source, raw_data)

        raw_opportunity = RawOpportunite.objects.create(
            source=source,
            processing_status=RawOpportuniteProcessingStatus.NEW,
            **raw_data,
        )
        return raw_opportunity, True


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
        "source_listing_url": canonicalize_source_item_url(
            raw_record.get("source_listing_url") or raw_record.get("listing_url")
        ),
        "source_record_id": _as_text(
            raw_record.get("source_record_id") or raw_record.get("record_id") or raw_record.get("external_id")
        )
        or None,
        "payload_hash": payload_hash,
        "content_fingerprint": content_fingerprint,
    }

    # Use DB-backed identity keys when available. Native source IDs are checked
    # before URLs because listings can emit the same record with changing URLs.
    has_identity = bool(raw_data["source_record_id"] or raw_data["source_item_url"])
    if has_identity:
        try:
            raw_opportunity, created = _upsert_raw_opportunity_by_identity(source, raw_data)
            return raw_opportunity, created, payload_hash
        except IntegrityError:
            logger.warning(
                "Raw opportunity duplicate recovered by identity source=%s record_id=%s url=%s",
                source.nom,
                raw_data.get("source_record_id"),
                raw_data.get("source_item_url"),
            )
            with transaction.atomic():
                raw_opportunity = _find_raw_opportunity_by_identity(source, raw_data, lock=True)
                if raw_opportunity is None:
                    raise
                raw_opportunity, _ = _apply_raw_opportunity_update(raw_opportunity, source, raw_data)
            return raw_opportunity, False, payload_hash
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

    raw_opportunity, _ = _apply_raw_opportunity_update(raw_opportunity, source, raw_data)
    return raw_opportunity, False, payload_hash


def _get_scraper_config_key(scraper):
    normalized_name = _normalize_text_for_fingerprint(getattr(scraper, "source_name", ""))
    normalized_name = normalized_name.replace(" ", "")
    return SOURCE_CONFIG_KEYS.get(normalized_name, normalized_name)


def _get_max_empty_pages(scraper):
    config_key = _get_scraper_config_key(scraper)
    config = getattr(settings, "SCRAPER_CONFIG", {})
    source_config = config.get(config_key, {}) if isinstance(config, dict) else {}
    try:
        return max(1, int(source_config.get("max_empty_pages", 2)))
    except (TypeError, ValueError):
        return 2


def _get_max_failures(scraper):
    config_key = _get_scraper_config_key(scraper)
    config = getattr(settings, "SCRAPER_CONFIG", {})
    source_config = config.get(config_key, {}) if isinstance(config, dict) else {}
    try:
        return max(1, int(source_config.get("max_failures", 3)))
    except (TypeError, ValueError):
        return 3


def _empty_collection_stats():
    return {
        "created": 0,
        "updated": 0,
        "skipped": 0,
        "failed_pages": 0,
        "stopped_due_to_failures": False,
        "errors": [],
    }


def _merge_collection_stats(total_stats, page_stats):
    total_stats["created"] += page_stats["created"]
    total_stats["updated"] += page_stats["updated"]
    total_stats["skipped"] += page_stats["skipped"]
    total_stats["failed_pages"] += page_stats.get("failed_pages", 0)
    total_stats["stopped_due_to_failures"] = (
        total_stats["stopped_due_to_failures"] or page_stats.get("stopped_due_to_failures", False)
    )
    total_stats["errors"].extend(page_stats["errors"])


def _persist_raw_records(raw_records, *, scraper, default_source, source_cache):
    stats = _empty_collection_stats()

    for raw in raw_records:
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

    return stats


def _iter_scraper_record_pages(scraper):
    if hasattr(scraper, "fetch_raw_record_pages"):
        yield from scraper.fetch_raw_record_pages()
        return
    yield scraper.collect()


def run_collection(scraper, organisation=None):
    """
    Collect raw records and persist them into RawOpportunite only.
    """

    default_source = {
        "name": scraper.source_name,
        "url": scraper.source_url,
        "type_source": scraper.source_type,
    }
    stats = _empty_collection_stats()
    source_cache = {}
    max_empty_pages = _get_max_empty_pages(scraper)
    max_failures = _get_max_failures(scraper)
    empty_pages_count = 0
    failure_count = 0
    source_key = _get_scraper_config_key(scraper)

    for page, raw_records in enumerate(_iter_scraper_record_pages(scraper), start=1):
        page_failed = bool(getattr(scraper, "last_page_failed", False))
        if hasattr(scraper, "last_page_failed"):
            scraper.last_page_failed = False

        if page_failed:
            failure_count += 1
            stats["failed_pages"] += 1
            logger.warning("[%s] failed page=%s", source_key, page)
            if failure_count >= max_failures:
                stats["stopped_due_to_failures"] = True
                logger.info("[%s] stopping due to failures", source_key)
                break
            continue

        failure_count = 0
        page_stats = _persist_raw_records(
            raw_records,
            scraper=scraper,
            default_source=default_source,
            source_cache=source_cache,
        )
        _merge_collection_stats(stats, page_stats)

        new_jobs = page_stats["created"]
        logger.info("[%s] page=%s new_jobs=%s", source_key, page, new_jobs)

        if new_jobs == 0:
            empty_pages_count += 1
        else:
            empty_pages_count = 0

        if empty_pages_count >= max_empty_pages:
            logger.info("[%s] stopping early at page=%s (no new data)", source_key, page)
            break

    logger.info(
        "Collection finished for source=%s (created=%s, updated=%s, skipped=%s)",
        scraper.source_name,
        stats["created"],
        stats["updated"],
        stats["skipped"],
    )
    return stats
