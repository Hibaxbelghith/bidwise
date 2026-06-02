from __future__ import annotations

import json
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from django.db import close_old_connections
from django.db.models.functions import Length

from ai.enrichment_roi import NON_JOB_SOURCE_NAMES
from ai.llm.opportunity_enrichment import (
    MIN_CONFIDENCE_TO_APPLY,
    enrich_opportunity_with_llm,
    opportunity_needs_llm_enrichment,
)
from ai.llm.providers import LLMProviderError, LLMProviderUnavailable, LLMRateLimitError
from opportunities.models import Opportunite, StatutOpportunite, TypeOpportunite


def _normalized_skill_key(value):
    return " ".join(str(value or "").strip().casefold().split())


def _is_weak_skill_set(skills):
    cleaned = [_normalized_skill_key(skill) for skill in (skills or []) if _normalized_skill_key(skill)]
    return len(cleaned) <= 1


def _coverage_snapshot(queryset):
    total = queryset.count()
    if total <= 0:
        return {
            "total": 0,
            "skills_count": 0,
            "raw_skills_count": 0,
            "normalized_skills_count": 0,
            "llm_enriched_count": 0,
            "skills_pct": 0.0,
            "normalized_skills_pct": 0.0,
        }

    skills_count = queryset.exclude(skills=[]).count()
    raw_skills_count = queryset.exclude(raw_skills=[]).count()
    normalized_skills_count = queryset.exclude(normalized_skills=[]).count()
    llm_enriched_count = queryset.filter(extra_data__llm_enrichment__isnull=False).count()
    return {
        "total": total,
        "skills_count": skills_count,
        "raw_skills_count": raw_skills_count,
        "normalized_skills_count": normalized_skills_count,
        "llm_enriched_count": llm_enriched_count,
        "skills_pct": round(skills_count * 100 / total, 1),
        "normalized_skills_pct": round(normalized_skills_count * 100 / total, 1),
    }


class Command(BaseCommand):
    help = (
        "Enrich active weak-skill opportunities with Gemini and optionally persist extracted skills. "
        "Designed for asynchronous dataset enrichment, not request-time recommendations."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=2,
            help="Maximum opportunities to enrich in this run. Default: 2 to protect free-tier LLM quota.",
        )
        parser.add_argument("--from-id", type=int, default=None)
        parser.add_argument(
            "--ids",
            default="",
            help="Comma-separated opportunity ids to enrich explicitly. Useful for controlled audits.",
        )
        parser.add_argument(
            "--source",
            default="Keejob",
            help="Source name to target. Use 'all' for every source. Default: Keejob.",
        )
        parser.add_argument(
            "--min-description-chars",
            type=int,
            default=300,
            help="Minimum description length for LLM enrichment candidates. Default: 300.",
        )
        parser.add_argument(
            "--weak-skills-only",
            action="store_true",
            help=(
                "Only enrich opportunities with empty or generic skills. "
                "By default, all not-yet-LLM-enriched rich-description opportunities are eligible."
            ),
        )
        parser.add_argument(
            "--include-strong-skills",
            action="store_true",
            help="Also include opportunities that already have specific skills.",
        )
        parser.add_argument("--force", action="store_true")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--audit", action="store_true", help="Print coverage metrics and selected candidates.")
        parser.add_argument("--no-apply-skills", action="store_true")
        parser.add_argument("--min-confidence", type=float, default=MIN_CONFIDENCE_TO_APPLY)
        parser.add_argument("--delay-seconds", type=float, default=12.0)
        parser.add_argument(
            "--workers",
            type=int,
            default=1,
            help=(
                "Number of concurrent LLM enrichment workers. Default: 1. "
                "Use cautiously with Gemini quota/rate limits."
            ),
        )
        parser.add_argument("--json", action="store_true")

    def handle(self, *args, **options):
        limit = max(1, min(int(options["limit"] or 2), 2000))
        from_id = options.get("from_id")
        if from_id is not None and int(from_id) < 0:
            raise CommandError("--from-id must be >= 0")
        raw_ids = str(options.get("ids") or "").strip()
        explicit_ids = []
        if raw_ids:
            for raw_id in raw_ids.split(","):
                raw_id = raw_id.strip()
                if not raw_id:
                    continue
                try:
                    explicit_ids.append(int(raw_id))
                except ValueError as exc:
                    raise CommandError("--ids must contain only comma-separated integer ids") from exc
            if not explicit_ids:
                raise CommandError("--ids did not contain any valid opportunity id")
            limit = min(len(explicit_ids), 2000)

        source_name = str(options.get("source") or "Keejob").strip()
        min_description_chars = max(0, int(options.get("min_description_chars") or 0))
        weak_skills_only = bool(options.get("weak_skills_only")) and not bool(options.get("include_strong_skills"))
        audit_only = bool(options["dry_run"]) or bool(options["audit"])

        queryset = (
            Opportunite.objects.filter(
                statut=StatutOpportunite.ACTIVE,
                type_opportunite=TypeOpportunite.EMPLOI,
            )
            .select_related("source")
            .annotate(description_length=Length("description"))
            .only(
                "id",
                "titre",
                "description",
                "organisation_nom",
                "ville",
                "contract_type",
                "availability",
                "skills",
                "raw_skills",
                "normalized_skills",
                "skills_normalization_hash",
                "skills_normalization_updated_at",
                "skills_normalization_error",
                "extra_data",
                "source__nom",
                "type_opportunite",
            )
            .order_by("-date_publication", "-id")
        )
        non_job_source_filter = Q(source__nom__iexact="BidWise Recommendation Benchmark")
        for source_key in NON_JOB_SOURCE_NAMES:
            non_job_source_filter |= Q(source__nom__iexact=source_key)
        queryset = queryset.exclude(non_job_source_filter)
        if source_name and source_name.casefold() != "all":
            queryset = queryset.filter(source__nom__iexact=source_name)
        if explicit_ids:
            queryset = queryset.filter(id__in=explicit_ids)
        if from_id is not None:
            queryset = queryset.filter(id__gte=int(from_id))
        if min_description_chars:
            queryset = queryset.filter(description_length__gte=min_description_chars)

        iterable = queryset.iterator(chunk_size=200)
        if explicit_ids:
            by_id = {opportunity.id: opportunity for opportunity in queryset}
            iterable = (by_id[opportunity_id] for opportunity_id in explicit_ids if opportunity_id in by_id)

        candidates = []
        for opportunity in iterable:
            weak_skills = _is_weak_skill_set(getattr(opportunity, "skills", []))
            needs_enrichment = opportunity_needs_llm_enrichment(opportunity)
            has_previous_enrichment = isinstance(getattr(opportunity, "extra_data", None), dict) and bool(
                opportunity.extra_data.get("llm_enrichment")
            )
            if (
                bool(options["force"])
                or (
                    not has_previous_enrichment
                    and (not weak_skills_only or weak_skills or needs_enrichment)
                )
            ):
                candidates.append(opportunity)
            if len(candidates) >= limit:
                break

        before_snapshot = _coverage_snapshot(queryset)
        results = []
        delay_seconds = max(0.0, float(options["delay_seconds"] or 0.0))
        if audit_only:
            for opportunity in candidates:
                results.append(
                    {
                        "status": "audit" if bool(options["audit"]) else "dry_run",
                        "opportunity_id": opportunity.pk,
                        "title": opportunity.titre,
                        "source": getattr(getattr(opportunity, "source", None), "nom", ""),
                        "description_length": len(opportunity.description or ""),
                        "skills": list(opportunity.skills or []),
                        "weak_skills": _is_weak_skill_set(opportunity.skills),
                        "needs_enrichment": opportunity_needs_llm_enrichment(opportunity),
                    }
                )
        else:
            workers = max(1, min(int(options.get("workers") or 1), 8))

            def run_enrichment(opportunity):
                close_old_connections()
                try:
                    result = enrich_opportunity_with_llm(
                        opportunity.pk,
                        force=bool(options["force"]),
                        apply_skills=not bool(options["no_apply_skills"]),
                        min_confidence=float(options["min_confidence"]),
                    )
                except LLMProviderUnavailable:
                    raise
                except LLMRateLimitError as exc:
                    result = {
                        "status": "rate_limited",
                        "opportunity_id": opportunity.pk,
                        "error": str(exc),
                    }
                except LLMProviderError as exc:
                    result = {
                        "status": "failed",
                        "opportunity_id": opportunity.pk,
                        "error": str(exc),
                    }
                finally:
                    close_old_connections()
                result["title"] = opportunity.titre
                return result

            if workers == 1:
                for index, opportunity in enumerate(candidates):
                    if index > 0 and delay_seconds:
                        time.sleep(delay_seconds)
                    try:
                        result = run_enrichment(opportunity)
                    except LLMProviderUnavailable as exc:
                        raise CommandError(str(exc)) from exc
                    results.append(result)
                    if result.get("status") == "rate_limited":
                        break
            else:
                pending = {}
                next_index = 0
                stop_scheduling = False
                with ThreadPoolExecutor(max_workers=workers) as executor:
                    while next_index < len(candidates) and len(pending) < workers:
                        future = executor.submit(run_enrichment, candidates[next_index])
                        pending[future] = candidates[next_index]
                        next_index += 1

                    while pending:
                        done, _ = wait(pending, return_when=FIRST_COMPLETED)
                        for future in done:
                            pending.pop(future, None)
                            try:
                                result = future.result()
                            except LLMProviderUnavailable as exc:
                                raise CommandError(str(exc)) from exc
                            results.append(result)
                            if result.get("status") == "rate_limited":
                                stop_scheduling = True

                        while not stop_scheduling and next_index < len(candidates) and len(pending) < workers:
                            if next_index > 0 and delay_seconds:
                                time.sleep(delay_seconds)
                            future = executor.submit(run_enrichment, candidates[next_index])
                            pending[future] = candidates[next_index]
                            next_index += 1

                        if stop_scheduling:
                            for future in pending:
                                future.cancel()
                            pending = {}
                            break

        after_snapshot = _coverage_snapshot(queryset)
        payload = {
            "scope": {
                "source": source_name,
                "ids": explicit_ids,
                "limit": limit,
                "workers": max(1, min(int(options.get("workers") or 1), 8)),
                "min_description_chars": min_description_chars,
                "apply_skills": not bool(options["no_apply_skills"]),
                "min_confidence": float(options["min_confidence"]),
                "force": bool(options["force"]),
                "dry_run": audit_only,
            },
            "coverage_before": before_snapshot,
            "coverage_after": after_snapshot,
            "candidates_count": len(candidates),
            "results": results,
        }

        if bool(options["json"]):
            self.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2))
            return

        self.stdout.write(self.style.SUCCESS(f"Gemini opportunity enrichment candidates: {len(results)}"))
        self.stdout.write(
            "Coverage before: "
            f"skills={before_snapshot['skills_pct']}% "
            f"normalized={before_snapshot['normalized_skills_pct']}% "
            f"llm={before_snapshot['llm_enriched_count']}/{before_snapshot['total']}"
        )
        if not audit_only:
            self.stdout.write(
                "Coverage after: "
                f"skills={after_snapshot['skills_pct']}% "
                f"normalized={after_snapshot['normalized_skills_pct']}% "
                f"llm={after_snapshot['llm_enriched_count']}/{after_snapshot['total']}"
            )
        for result in results:
            self.stdout.write(f"[{result.get('opportunity_id')}] {result.get('title')}")
            self.stdout.write(f"  status: {result.get('status')}")
            if "description_length" in result:
                self.stdout.write(f"  description_length: {result.get('description_length')}")
            if "weak_skills" in result:
                self.stdout.write(f"  weak_skills: {result.get('weak_skills')}")
            if result.get("error"):
                self.stdout.write(f"  error: {result.get('error')}")
            if "applied_to_skills" in result:
                self.stdout.write(f"  applied_to_skills: {result.get('applied_to_skills')}")
                self.stdout.write(f"  families: {', '.join(result.get('business_families') or []) or '-'}")
                self.stdout.write(f"  skills: {', '.join((result.get('skills') or [])[:10]) or '-'}")
