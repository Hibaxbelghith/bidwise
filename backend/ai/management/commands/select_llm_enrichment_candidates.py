from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from ai.enrichment_roi import (
    DEFAULT_WEAK_BENCHMARK_FAMILIES,
    RecommendationStats,
    base_enrichment_queryset,
    score_opportunity_for_enrichment,
)
from opportunities.models import TypeOpportunite


def _parse_csv(value: str) -> list[str]:
    return [item.strip() for item in str(value or "").split(",") if item.strip()]


def _load_recommendation_stats(path: str) -> dict[int, RecommendationStats]:
    if not path:
        return {}
    report_path = Path(path)
    if not report_path.exists():
        raise CommandError(f"Recommendation report not found: {report_path}")
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    rows_by_id: dict[int, dict[str, Any]] = defaultdict(lambda: {"appeared": 0, "strong": 0, "related": 0, "profiles": set()})
    for profile in payload.get("profiles", []) or []:
        profile_key = str(profile.get("profile") or profile.get("label") or "").strip()
        for row in profile.get("top", []) or []:
            try:
                opportunity_id = int(row.get("id"))
            except (TypeError, ValueError):
                continue
            bucket = str(row.get("bucket") or row.get("recommendation_bucket") or "").strip()
            rows_by_id[opportunity_id]["appeared"] += 1
            rows_by_id[opportunity_id]["profiles"].add(profile_key)
            if bucket == "STRONG_MATCH":
                rows_by_id[opportunity_id]["strong"] += 1
            elif bucket:
                rows_by_id[opportunity_id]["related"] += 1
    return {
        opportunity_id: RecommendationStats(
            appeared_count=int(values["appeared"]),
            strong_count=int(values["strong"]),
            related_count=int(values["related"]),
            profiles=tuple(sorted(values["profiles"])),
        )
        for opportunity_id, values in rows_by_id.items()
    }


def _roi_to_dict(roi) -> dict[str, Any]:
    return {
        "id": roi.opportunity_id,
        "title": roi.title,
        "source": roi.source,
        "priority": roi.priority,
        "score": roi.score,
        "eligible": roi.eligible,
        "reasons": list(roi.reasons),
        "exclusions": list(roi.exclusions),
        "description_length": roi.description_length,
        "skill_count": roi.skill_count,
        "has_llm_enrichment": roi.has_llm_enrichment,
        "days_until_deadline": roi.days_until_deadline,
        "business_families": list(roi.business_families),
        "recommendation_stats": {
            "appeared_count": roi.recommendation_stats.appeared_count,
            "strong_count": roi.recommendation_stats.strong_count,
            "related_count": roi.recommendation_stats.related_count,
            "profiles": list(roi.recommendation_stats.profiles),
        },
    }


class Command(BaseCommand):
    help = "Select high-ROI opportunities for offline LLM enrichment without calling the LLM."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=50)
        parser.add_argument("--source", default="all", help="Source name or 'all'.")
        parser.add_argument("--include-stage", action="store_true")
        parser.add_argument(
            "--min-process-description-chars",
            type=int,
            default=120,
            help="P0 exclusion threshold. Very short descriptions below this are skipped.",
        )
        parser.add_argument(
            "--rich-description-chars",
            type=int,
            default=300,
            help="P1 threshold. Descriptions above this with weak skills get highest ROI.",
        )
        parser.add_argument(
            "--min-description-chars",
            type=int,
            default=None,
            help="Backward-compatible alias for --rich-description-chars.",
        )
        parser.add_argument("--weak-skill-threshold", type=int, default=2)
        parser.add_argument(
            "--exclude-expiring-days",
            type=int,
            default=7,
            help="Exclude opportunities whose deadline is this many days away or less. Set 0 to keep only already-expiring out.",
        )
        parser.add_argument(
            "--benchmark-report",
            default="",
            help="Optional benchmark_final_recommendation_profiles JSON to identify dark offers.",
        )
        parser.add_argument(
            "--weak-families",
            default=",".join(sorted(DEFAULT_WEAK_BENCHMARK_FAMILIES)),
            help="Comma-separated business families to boost first.",
        )
        parser.add_argument("--priority", default="", help="Filter priorities, comma-separated: P1,P2,P3,P0.")
        parser.add_argument("--ids-only", action="store_true")
        parser.add_argument("--json", action="store_true")

    def handle(self, *args, **options):
        limit = max(1, min(int(options.get("limit") or 50), 1000))
        source_name = str(options.get("source") or "all").strip()
        rich_description_chars = int(
            options.get("min_description_chars")
            if options.get("min_description_chars") is not None
            else options.get("rich_description_chars")
            or 300
        )
        rich_description_chars = max(0, rich_description_chars)
        min_process_description_chars = max(0, int(options.get("min_process_description_chars") or 0))
        weak_skill_threshold = max(0, int(options.get("weak_skill_threshold") or 0))
        exclude_expiring_days = max(0, int(options.get("exclude_expiring_days") or 0))
        priorities = {item.upper() for item in _parse_csv(options.get("priority", ""))}
        weak_families = set(_parse_csv(options.get("weak_families", ""))) or set(DEFAULT_WEAK_BENCHMARK_FAMILIES)
        recommendation_stats = _load_recommendation_stats(str(options.get("benchmark_report") or "").strip())

        queryset = base_enrichment_queryset(include_stages=bool(options.get("include_stage")))
        if source_name and source_name.casefold() != "all":
            queryset = queryset.filter(source__nom__iexact=source_name)
        queryset = queryset.exclude(source__nom__iexact="BidWise Recommendation Benchmark")

        # Cheap DB prefilter: still score in Python because skill arrays/JSON and ROI reasons need full context.
        queryset = queryset.filter(description_length__gte=max(50, min_process_description_chars)).filter(
            Q(extra_data__llm_enrichment__isnull=True) | Q(id__in=list(recommendation_stats.keys()))
        )

        job_types = {TypeOpportunite.EMPLOI}
        if bool(options.get("include_stage")):
            job_types.add(TypeOpportunite.STAGE)

        rois = []
        scanned = 0
        for opportunity in queryset.iterator(chunk_size=500):
            scanned += 1
            roi = score_opportunity_for_enrichment(
                opportunity,
                recommendation_stats=recommendation_stats.get(opportunity.pk),
                weak_families=weak_families,
                min_process_description_chars=min_process_description_chars,
                rich_description_chars=rich_description_chars,
                weak_skill_threshold=weak_skill_threshold,
                exclude_expiring_days=exclude_expiring_days,
                job_types=job_types,
            )
            if priorities and roi.priority not in priorities:
                continue
            if not roi.eligible and roi.priority != "P0":
                continue
            rois.append(roi)

        rois.sort(key=lambda item: (item.eligible, item.score, item.description_length, item.opportunity_id), reverse=True)
        selected = rois[:limit]
        priority_counts = Counter(roi.priority for roi in rois)
        source_counts = Counter(roi.source for roi in selected)
        family_counts = Counter(family for roi in selected for family in roi.business_families)

        payload = {
            "scope": {
                "source": source_name,
                "limit": limit,
                "include_stage": bool(options.get("include_stage")),
                "min_process_description_chars": min_process_description_chars,
                "rich_description_chars": rich_description_chars,
                "weak_skill_threshold": weak_skill_threshold,
                "exclude_expiring_days": exclude_expiring_days,
                "benchmark_report": str(options.get("benchmark_report") or ""),
                "weak_families": sorted(weak_families),
                "priority_filter": sorted(priorities),
            },
            "summary": {
                "scanned": scanned,
                "eligible_ranked": sum(1 for roi in rois if roi.eligible),
                "selected": len(selected),
                "priority_counts": dict(priority_counts),
                "selected_source_counts": dict(source_counts),
                "selected_family_counts": dict(family_counts.most_common(20)),
            },
            "ids": [roi.opportunity_id for roi in selected],
            "results": [_roi_to_dict(roi) for roi in selected],
        }

        if bool(options.get("ids_only")):
            self.stdout.write(",".join(str(pk) for pk in payload["ids"]))
            return
        if bool(options.get("json")):
            self.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2))
            return

        self.stdout.write("LLM enrichment ROI candidates")
        self.stdout.write(json.dumps(payload["summary"], ensure_ascii=False, indent=2))
        for row in payload["results"]:
            self.stdout.write(
                f"[{row['priority']}] {row['score']:>5} #{row['id']} {row['title']} "
                f"({row['source']}) skills={row['skill_count']} desc={row['description_length']}"
            )
            if row["reasons"]:
                self.stdout.write(f"  reasons: {', '.join(row['reasons'])}")
            if row["business_families"]:
                self.stdout.write(f"  families: {', '.join(row['business_families'])}")
