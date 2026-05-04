import logging
import ipaddress
from urllib.parse import urlparse

from django.db.models import Avg, Count, Max, Min, Q, Sum
from django.db.models.functions import Length
from django.utils import timezone

from opportunities.models import (
    Opportunite,
    PipelineRun,
    PipelineRunStatus,
    RawOpportunite,
    RawOpportuniteProcessingStatus,
)
from opportunities.pipeline import get_source_config
from opportunities.source_cleanup import REMOVED_SOURCE_KEYS, removed_source_q


logger = logging.getLogger(__name__)
PIPELINE_FLOW_LABEL = "Scraping -> Processing -> Materialization -> Embeddings"


def _is_valid_web_url(value: str) -> bool:
    if not value:
        return False

    try:
        parsed = urlparse(str(value).strip())
    except Exception:
        return False

    if parsed.scheme not in {"http", "https"}:
        return False

    host = (parsed.hostname or "").strip().lower()
    if not host:
        return False

    if host == "localhost" or host.endswith(".local") or host.endswith(".localdomain"):
        return False

    try:
        ip = ipaddress.ip_address(host)
        if not ip.is_global:
            return False
    except ValueError:
        # Hostname (non-IP): accepted.
        pass

    return True


def compute_dataset_metrics():
    queryset = Opportunite.objects.all()
    total = queryset.count()

    empty_description = queryset.filter(
        Q(description__isnull=True) | Q(description="")
    ).count()
    empty_title = queryset.filter(
        Q(titre__isnull=True) | Q(titre="")
    ).count()

    organization_filled = queryset.exclude(
        Q(organisation_nom__isnull=True) | Q(organisation_nom="")
    ).count()
    organization_rate = (organization_filled / total) * 100 if total else 0.0

    with_lengths = queryset.annotate(description_length=Length("description"))
    length_stats = with_lengths.aggregate(
        avg_length=Avg("description_length"),
        min_length=Min("description_length"),
        max_length=Max("description_length"),
    )

    structured_count = queryset.filter(
        Q(description__icontains="contract:")
        | Q(description__icontains="type:")
        | Q(titre__icontains="contract:")
        | Q(titre__icontains="type:")
    ).count()
    structured_rate = (structured_count / total) * 100 if total else 0.0

    top_organizations_rows = (
        queryset.exclude(Q(organisation_nom__isnull=True) | Q(organisation_nom=""))
        .values("organisation_nom")
        .annotate(count=Count("id"))
        .order_by("-count", "organisation_nom")[:10]
    )
    top_organizations = [
        {"name": row["organisation_nom"], "count": row["count"]}
        for row in top_organizations_rows
    ]

    length_buckets = with_lengths.aggregate(
        len_0_49=Count("id", filter=Q(description_length__lt=50)),
        len_50_149=Count(
            "id", filter=Q(description_length__gte=50, description_length__lt=150)
        ),
        len_150_299=Count(
            "id", filter=Q(description_length__gte=150, description_length__lt=300)
        ),
        len_300_plus=Count("id", filter=Q(description_length__gte=300)),
    )

    html_coverage_total_with_any_url = 0
    html_coverage_total_valid_urls = 0
    html_coverage_with_html_valid_urls = 0

    for source_item_url, description_html in queryset.values_list("source_item_url", "description_html"):
        source_item_url = (source_item_url or "").strip()
        description_html = (description_html or "").strip()

        if source_item_url:
            html_coverage_total_with_any_url += 1

        if not _is_valid_web_url(source_item_url):
            continue

        html_coverage_total_valid_urls += 1
        if description_html:
            html_coverage_with_html_valid_urls += 1

    html_coverage_excluded_invalid_urls = (
        html_coverage_total_with_any_url - html_coverage_total_valid_urls
    )
    html_coverage_rate_valid_urls = (
        (html_coverage_with_html_valid_urls / html_coverage_total_valid_urls) * 100
        if html_coverage_total_valid_urls
        else 0.0
    )

    return {
        "total": total,
        "empty_description": empty_description,
        "empty_title": empty_title,
        "organization_non_empty": organization_filled,
        "organization_rate": organization_rate,
        "avg_length": float(length_stats["avg_length"] or 0.0),
        "min_length": int(length_stats["min_length"] or 0),
        "max_length": int(length_stats["max_length"] or 0),
        "structured_count": structured_count,
        "structured_rate": structured_rate,
        "top_organizations": top_organizations,
        "length_buckets": {
            "0-49": int(length_buckets["len_0_49"] or 0),
            "50-149": int(length_buckets["len_50_149"] or 0),
            "150-299": int(length_buckets["len_150_299"] or 0),
            "300+": int(length_buckets["len_300_plus"] or 0),
        },
        "html_coverage": {
            "total_with_any_url": int(html_coverage_total_with_any_url),
            "valid_web_urls": int(html_coverage_total_valid_urls),
            "excluded_invalid_urls": int(html_coverage_excluded_invalid_urls),
            "with_description_html": int(html_coverage_with_html_valid_urls),
            "rate_valid_web_urls": float(html_coverage_rate_valid_urls),
        },
    }


def _percentage(count: int, total: int) -> int:
    if not total:
        return 0
    return int(round((count / total) * 100))


def _run_total(run, total_field, legacy_field):
    if run is None:
        return 0
    value = getattr(run, total_field, 0) or 0
    if value:
        return int(value)
    return int(getattr(run, legacy_field, 0) or 0)


def _compute_data_quality(queryset) -> dict:
    total = queryset.count()
    if not total:
        return {
            "description": 0,
            "salary": 0,
            "skills": 0,
            "embeddings": 0,
        }

    with_description = queryset.exclude(Q(description__isnull=True) | Q(description="")).count()
    with_salary = queryset.exclude(Q(salary__isnull=True) | Q(salary="")).count()
    with_skills = queryset.exclude(skills=[]).count()
    with_embeddings = queryset.exclude(
        Q(embedding_vector__isnull=True) | Q(embedding_vector=[])
    ).count()

    return {
        "description": _percentage(with_description, total),
        "salary": _percentage(with_salary, total),
        "skills": _percentage(with_skills, total),
        "embeddings": _percentage(with_embeddings, total),
    }


def _compute_latest_freshness_delay_seconds() -> float:
    raw_obj = (
        RawOpportunite.objects.exclude(removed_source_q("source__nom"))
        .filter(
            processing_status=RawOpportuniteProcessingStatus.MATERIALIZED,
            processed_at__isnull=False,
            last_seen_at__isnull=False,
        )
        .order_by("-processed_at", "-id")
        .only("processed_at", "last_seen_at")
        .first()
    )
    if raw_obj is None:
        return 0.0
    return float(max((raw_obj.processed_at - raw_obj.last_seen_at).total_seconds(), 0.0))


def _compute_pipeline_throughput(run) -> float:
    if run is None or not getattr(run, "duration_seconds", 0):
        return 0.0
    processed = _run_total(run, "total_processed", "processed_count")
    if not processed:
        return 0.0
    minutes = max(float(run.duration_seconds) / 60.0, 1 / 60)
    return round(processed / minutes, 2)


def _freshness_component(source, last_success_at) -> float:
    if last_success_at is None:
        return 0.0
    stale_after_seconds = int(get_source_config(source).get("stale_after_seconds", 12 * 60 * 60) or 12 * 60 * 60)
    age_seconds = max((timezone.now() - last_success_at).total_seconds(), 0.0)
    if stale_after_seconds <= 0:
        return 0.0
    return max(0.0, min(1.0, 1.0 - (age_seconds / stale_after_seconds)))


def _compute_source_reliability_scores() -> dict:
    source_rows = (
        PipelineRun.objects.exclude(source__in=REMOVED_SOURCE_KEYS)
        .values("source")
        .annotate(
            total_runs=Count("id"),
            success_runs=Count("id", filter=Q(status=PipelineRunStatus.SUCCESS)),
            failed_runs=Count("id", filter=Q(status=PipelineRunStatus.FAILED)),
            total_failed_pages=Sum("total_failed_pages"),
            last_success_at=Max(
                "finished_at",
                filter=Q(status=PipelineRunStatus.SUCCESS),
            ),
        )
        .order_by("source")
    )

    scores = {}
    for row in source_rows:
        source = row.get("source") or "unknown"
        total_runs = int(row.get("total_runs") or 0)
        if not total_runs:
            scores[source] = 0
            continue

        success_component = (row.get("success_runs") or 0) / total_runs
        failed_pages = int(row.get("total_failed_pages") or 0)
        error_component = max(0.0, 1.0 - min(failed_pages / max(total_runs, 1), 1.0))
        freshness_component = _freshness_component(source, row.get("last_success_at"))
        score = (
            success_component * 0.50
            + error_component * 0.25
            + freshness_component * 0.25
        ) * 100
        scores[source] = int(round(max(0.0, min(score, 100.0))))

    return scores


def _build_pipeline_flow(*, latest_run, new_count, materialized_count, data_quality) -> dict:
    latest_status = latest_run.status if latest_run else "idle"
    embeddings_coverage = int(data_quality.get("embeddings", 0) or 0)

    return {
        "label": PIPELINE_FLOW_LABEL,
        "stages": [
            {
                "name": "Scraping",
                "status": latest_status,
                "processed": _run_total(latest_run, "total_processed", "processed_count"),
            },
            {
                "name": "Processing",
                "status": "backlog" if new_count else "complete",
                "pending": new_count,
            },
            {
                "name": "Materialization",
                "status": "complete" if materialized_count else "idle",
                "materialized": materialized_count,
            },
            {
                "name": "Embeddings",
                "status": "complete" if embeddings_coverage == 100 else "backlog",
                "coverage": embeddings_coverage,
            },
        ],
    }


def compute_pipeline_metrics() -> dict:
    status_counts = RawOpportunite.objects.aggregate(
        total_raw=Count("id"),
        new_count=Count(
            "id",
            filter=Q(processing_status=RawOpportuniteProcessingStatus.NEW),
        ),
        materialized_count=Count(
            "id",
            filter=Q(processing_status=RawOpportuniteProcessingStatus.MATERIALIZED),
        ),
        rejected_count=Count(
            "id",
            filter=Q(processing_status=RawOpportuniteProcessingStatus.REJECTED),
        ),
    )

    total_raw = int(status_counts["total_raw"] or 0)
    new_count = int(status_counts["new_count"] or 0)
    materialized_count = int(status_counts["materialized_count"] or 0)
    rejected_count = int(status_counts["rejected_count"] or 0)

    processed_count = materialized_count + rejected_count

    processing_success_rate = (
        materialized_count / processed_count if processed_count else 0.0
    )

    rejection_rate = (
        rejected_count / processed_count if processed_count else 0.0
    )

    overall_success_rate = (
        materialized_count / total_raw if total_raw else 0.0
    )

    backlog_rate = (
        new_count / total_raw if total_raw else 0.0
    )

    opportunities = Opportunite.objects.exclude(removed_source_q("source__nom"))
    data_quality = _compute_data_quality(opportunities)
    latest_run = (
        PipelineRun.objects.exclude(source__in=REMOVED_SOURCE_KEYS)
        .order_by("-started_at", "-id")
        .first()
    )
    last_run_processed = _run_total(latest_run, "total_processed", "processed_count")
    last_run_created = _run_total(latest_run, "total_created", "created_count")
    last_run_updated = _run_total(latest_run, "total_updated", "updated_count")
    last_run_duration = float(latest_run.duration_seconds or 0.0) if latest_run else 0.0
    last_run_status = latest_run.status if latest_run else "idle"

    metrics = {
        "total_raw": total_raw,
        "new_count": new_count,
        "materialized_count": materialized_count,
        "rejected_count": rejected_count,
        "processed_count": processed_count,
        "processing_success_rate": float(processing_success_rate),
        "overall_success_rate": float(overall_success_rate),
        "rejection_rate": float(rejection_rate),
        "backlog_rate": float(backlog_rate),
        "last_run_processed": last_run_processed,
        "last_run_created": last_run_created,
        "last_run_updated": last_run_updated,
        "last_run_duration": last_run_duration,
        "last_run_status": last_run_status,
        "pipeline_flow": _build_pipeline_flow(
            latest_run=latest_run,
            new_count=new_count,
            materialized_count=materialized_count,
            data_quality=data_quality,
        ),
        "data_quality": data_quality,
        "source_reliability_score": _compute_source_reliability_scores(),
        "pipeline_throughput": _compute_pipeline_throughput(latest_run),
        "freshness_delay": _compute_latest_freshness_delay_seconds(),
    }
    logger.debug("Pipeline metrics computed: %s", metrics)
    return metrics
