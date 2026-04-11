import logging

from django.db.models import Avg, Count, Max, Min, Q
from django.db.models.functions import Length

from opportunities.models import (
    Opportunite,
    RawOpportunite,
    RawOpportuniteProcessingStatus,
)


logger = logging.getLogger(__name__)


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
    }
    logger.debug("Pipeline metrics computed: %s", metrics)
    return metrics
