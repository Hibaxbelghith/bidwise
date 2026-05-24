from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, field
from typing import Any, Callable

from ai.esco_skill_storage import (
    clean_skill_storage_list,
    summarize_normalized_skill_entries,
)
from ai.tasks import (
    normalize_opportunity_skills_storage,
    normalize_profile_skills_storage,
)
from opportunities.models import Opportunite
from users.models import Profil, ProfileResume
from users.resume_semantic.service import (
    process_profile_resume_semantics,
    refresh_resume_skill_normalization_from_existing_candidates,
)


TARGET_ALL = "all"
TARGET_OPPORTUNITIES = "opportunities"
TARGET_PROFILES = "profiles"
TARGET_RESUMES = "resumes"
VALID_TARGETS = {
    TARGET_ALL,
    TARGET_OPPORTUNITIES,
    TARGET_PROFILES,
    TARGET_RESUMES,
}


@dataclass
class BackfillStats:
    target: str
    scanned: int = 0
    eligible: int = 0
    updated: int = 0
    skipped_already_normalized: int = 0
    skipped_ineligible: int = 0
    skipped_missing: int = 0
    failed: int = 0
    matched_entities: int = 0
    unmatched_entities: int = 0
    official_matches: int = 0
    legacy_matches: int = 0
    last_processed_id: int | None = None

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass
class CoverageReport:
    target: str
    total_entities: int = 0
    eligible_entities: int = 0
    entities_with_raw_skill_source: int = 0
    entities_with_normalized_payload: int = 0
    entities_with_official_match: int = 0
    entities_with_legacy_match: int = 0
    entities_with_unmatched_only: int = 0
    entities_with_errors: int = 0
    pending_entities: int = 0
    matched_entries: int = 0
    official_match_entries: int = 0
    legacy_match_entries: int = 0
    unmatched_entries: int = 0
    top_unmatched_skills: list[dict[str, object]] = field(default_factory=list)
    top_unmatched_reasons: list[dict[str, object]] = field(default_factory=list)
    top_matched_skills: list[dict[str, object]] = field(default_factory=list)
    top_pending_raw_skills: list[dict[str, object]] = field(default_factory=list)
    top_rejected_candidates: list[dict[str, object]] = field(default_factory=list)
    top_rejected_candidate_reasons: list[dict[str, object]] = field(default_factory=list)

    @property
    def payload_coverage_pct(self) -> float:
        if self.eligible_entities <= 0:
            return 0.0
        return round((self.entities_with_normalized_payload / self.eligible_entities) * 100.0, 2)

    @property
    def official_match_coverage_pct(self) -> float:
        if self.eligible_entities <= 0:
            return 0.0
        return round((self.entities_with_official_match / self.eligible_entities) * 100.0, 2)

    def as_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["payload_coverage_pct"] = self.payload_coverage_pct
        payload["official_match_coverage_pct"] = self.official_match_coverage_pct
        return payload


def _iter_pk_batches(queryset, *, chunk_size: int, limit: int | None = None, start_after_id: int | None = None):
    safe_chunk_size = max(1, int(chunk_size or 100))
    remaining = None if limit is None else max(0, int(limit))
    last_pk = start_after_id
    base_queryset = queryset.order_by("pk")

    while True:
        batch_queryset = base_queryset
        if last_pk is not None:
            batch_queryset = batch_queryset.filter(pk__gt=last_pk)
        if remaining is not None:
            if remaining <= 0:
                break
            batch_queryset = batch_queryset[: min(safe_chunk_size, remaining)]
        else:
            batch_queryset = batch_queryset[:safe_chunk_size]

        batch = list(batch_queryset)
        if not batch:
            break

        yield batch

        last_pk = batch[-1].pk
        if remaining is not None:
            remaining -= len(batch)


def _result_has_match(result: dict[str, Any]) -> bool:
    return int(result.get("matched_count") or 0) > 0 or int(result.get("official_matches") or 0) > 0


def _result_is_fresh_skip(result: dict[str, Any]) -> bool:
    return result.get("status") == "skipped" and str(result.get("reason") or "") in {
        "fresh",
        "fresh_after_lock",
    }


def _list_skill_source(primary_values, fallback_values) -> list[str]:
    cleaned = clean_skill_storage_list(primary_values)
    if cleaned:
        return cleaned
    return clean_skill_storage_list(fallback_values)


def _opportunity_skill_source(opportunity: Opportunite) -> list[str]:
    return _list_skill_source(getattr(opportunity, "raw_skills", []), getattr(opportunity, "skills", []))


def _profile_skill_source(profile: Profil) -> list[str]:
    return _list_skill_source(getattr(profile, "raw_skills", []), getattr(profile, "competences", []))


def _resume_has_semantic_source(resume: ProfileResume) -> bool:
    if str(getattr(resume, "parsing_status", "") or "").upper() != ProfileResume.ParsingStatus.SUCCEEDED:
        return False
    parsed_text = str(getattr(resume, "parsed_text", "") or "").strip()
    embedding_source = str(getattr(resume, "resume_text_embedding_source", "") or "").strip()
    extracted_raw = clean_skill_storage_list(getattr(resume, "extracted_raw_skills", []))
    return bool(parsed_text or embedding_source or extracted_raw)


def _append_counter_items(counter: Counter, values) -> None:
    for value in values:
        text = str(value or "").strip()
        if text:
            counter[text] += 1


def _top_counter(counter: Counter, *, top_n: int) -> list[dict[str, object]]:
    return [
        {"label": label, "count": count}
        for label, count in counter.most_common(max(0, int(top_n)))
    ]


def _build_batch_runner(target: str):
    if target == TARGET_OPPORTUNITIES:
        return lambda entity_id, force=False: normalize_opportunity_skills_storage.run(entity_id, force=force)
    if target == TARGET_PROFILES:
        return lambda entity_id, force=False: normalize_profile_skills_storage.run(entity_id, force=force)
    raise ValueError(f"Unsupported backfill runner target: {target}")


def _normalize_resume_by_id(resume_id: int, *, force: bool = False) -> dict[str, Any]:
    try:
        resume = ProfileResume.objects.only(
            "id",
            "parsed_text",
            "resume_text_embedding_source",
            "extracted_raw_skills",
            "extracted_normalized_skills",
            "extracted_skills_normalization_hash",
            "extracted_skills_normalization_updated_at",
            "extracted_skills_normalization_error",
            "semantic_resume_status",
            "semantic_resume_content_hash",
            "semantic_resume_updated_at",
            "semantic_resume_version",
            "parsing_status",
        ).get(pk=resume_id)
    except ProfileResume.DoesNotExist:
        return {"status": "skipped", "reason": "missing_resume", "resume_id": resume_id}

    if not _resume_has_semantic_source(resume):
        return {"status": "skipped", "reason": "ineligible_resume", "resume_id": resume_id}

    result = process_profile_resume_semantics(resume, force=force)
    status = str(result.get("status") or "")
    if status == "FAILED":
        return {**result, "status": "failed", "resume_id": resume_id}
    if status == "SKIPPED":
        return {
            **result,
            "status": "skipped",
            "reason": str(result.get("reason") or "fresh"),
            "resume_id": resume_id,
        }
    return {**result, "status": "updated", "resume_id": resume_id}


def _cleanup_resume_candidates_by_id(resume_id: int, *, force: bool = False) -> dict[str, Any]:
    try:
        resume = ProfileResume.objects.only(
            "id",
            "parsed_text",
            "resume_text_embedding_source",
            "extracted_raw_skills",
            "extracted_normalized_skills",
            "extracted_skills_normalization_hash",
            "extracted_skills_normalization_updated_at",
            "extracted_skills_normalization_error",
            "semantic_resume_metadata",
            "parsing_status",
        ).get(pk=resume_id)
    except ProfileResume.DoesNotExist:
        return {"status": "skipped", "reason": "missing_resume", "resume_id": resume_id}

    if not _resume_has_semantic_source(resume):
        return {"status": "skipped", "reason": "ineligible_resume", "resume_id": resume_id}

    return refresh_resume_skill_normalization_from_existing_candidates(resume, force=force)


def run_backfill_for_target(
    target: str,
    *,
    chunk_size: int = 100,
    limit: int | None = None,
    force: bool = False,
    start_after_id: int | None = None,
    resume_mode: str = "full",
    progress_callback: Callable[[BackfillStats], None] | None = None,
) -> BackfillStats:
    if target == TARGET_OPPORTUNITIES:
        queryset = Opportunite.objects.only("id", "skills", "raw_skills")
        eligibility_fn = _opportunity_skill_source
        runner = _build_batch_runner(target)
    elif target == TARGET_PROFILES:
        queryset = Profil.objects.only("id", "competences", "raw_skills")
        eligibility_fn = _profile_skill_source
        runner = _build_batch_runner(target)
    elif target == TARGET_RESUMES:
        queryset = ProfileResume.objects.only(
            "id",
            "parsed_text",
            "resume_text_embedding_source",
            "extracted_raw_skills",
            "parsing_status",
        )
        eligibility_fn = _resume_has_semantic_source
        if resume_mode == "candidate_cleanup":
            runner = lambda entity_id, force=False: _cleanup_resume_candidates_by_id(entity_id, force=force)
        else:
            runner = lambda entity_id, force=False: _normalize_resume_by_id(entity_id, force=force)
    else:
        raise ValueError(f"Unsupported target: {target}")

    stats = BackfillStats(target=target)

    for batch in _iter_pk_batches(
        queryset,
        chunk_size=chunk_size,
        limit=limit,
        start_after_id=start_after_id,
    ):
        for entity in batch:
            stats.scanned += 1
            stats.last_processed_id = entity.pk

            skill_source = eligibility_fn(entity)
            is_eligible = bool(skill_source)
            if not is_eligible:
                stats.skipped_ineligible += 1
                continue

            stats.eligible += 1
            result = runner(entity.pk, force=force)
            status = str(result.get("status") or "")
            if status == "updated":
                stats.updated += 1
                if _result_has_match(result):
                    stats.matched_entities += 1
                else:
                    stats.unmatched_entities += 1
                stats.official_matches += int(result.get("official_matches") or 0)
                stats.legacy_matches += int(result.get("legacy_matches") or 0)
            elif _result_is_fresh_skip(result):
                stats.skipped_already_normalized += 1
            elif status == "skipped":
                reason = str(result.get("reason") or "")
                if reason.startswith("missing_"):
                    stats.skipped_missing += 1
                elif reason == "ineligible_resume":
                    stats.skipped_ineligible += 1
                else:
                    stats.skipped_already_normalized += 1
            else:
                stats.failed += 1

        if progress_callback is not None:
            progress_callback(stats)

    return stats


def backfill_esco_normalization(
    *,
    target: str = TARGET_ALL,
    chunk_size: int = 100,
    limit: int | None = None,
    force: bool = False,
    start_after_id: int | None = None,
    resume_mode: str = "full",
    progress_callback: Callable[[BackfillStats], None] | None = None,
) -> dict[str, dict[str, object]]:
    if target not in VALID_TARGETS:
        raise ValueError(f"Unsupported target: {target}")

    selected_targets = (
        [TARGET_OPPORTUNITIES, TARGET_PROFILES, TARGET_RESUMES]
        if target == TARGET_ALL
        else [target]
    )

    results = {}
    for selected_target in selected_targets:
        stats = run_backfill_for_target(
            selected_target,
            chunk_size=chunk_size,
            limit=limit,
            force=force,
            start_after_id=start_after_id,
            resume_mode=resume_mode,
            progress_callback=progress_callback,
        )
        results[selected_target] = stats.as_dict()
    return results


def _scan_coverage_for_target(
    target: str,
    *,
    chunk_size: int = 200,
    limit: int | None = None,
    start_after_id: int | None = None,
    top_n: int = 10,
) -> CoverageReport:
    if target == TARGET_OPPORTUNITIES:
        queryset = Opportunite.objects.only(
            "id",
            "skills",
            "raw_skills",
            "normalized_skills",
            "skills_normalization_updated_at",
            "skills_normalization_error",
        )
        source_fn = _opportunity_skill_source
        normalized_field = "normalized_skills"
        updated_at_field = "skills_normalization_updated_at"
        error_field = "skills_normalization_error"
    elif target == TARGET_PROFILES:
        queryset = Profil.objects.only(
            "id",
            "competences",
            "raw_skills",
            "normalized_skills",
            "skills_normalization_updated_at",
            "skills_normalization_error",
        )
        source_fn = _profile_skill_source
        normalized_field = "normalized_skills"
        updated_at_field = "skills_normalization_updated_at"
        error_field = "skills_normalization_error"
    elif target == TARGET_RESUMES:
        queryset = ProfileResume.objects.only(
            "id",
            "parsed_text",
            "resume_text_embedding_source",
            "extracted_raw_skills",
            "extracted_normalized_skills",
            "extracted_skills_normalization_updated_at",
            "extracted_skills_normalization_error",
            "parsing_status",
            "semantic_resume_status",
            "semantic_resume_metadata",
        )
        source_fn = lambda resume: clean_skill_storage_list(getattr(resume, "extracted_raw_skills", []))
        normalized_field = "extracted_normalized_skills"
        updated_at_field = "extracted_skills_normalization_updated_at"
        error_field = "extracted_skills_normalization_error"
    else:
        raise ValueError(f"Unsupported target: {target}")

    report = CoverageReport(target=target)
    unmatched_counter: Counter = Counter()
    unmatched_reason_counter: Counter = Counter()
    matched_counter: Counter = Counter()
    pending_counter: Counter = Counter()
    rejected_candidate_counter: Counter = Counter()
    rejected_reason_counter: Counter = Counter()

    for batch in _iter_pk_batches(
        queryset,
        chunk_size=chunk_size,
        limit=limit,
        start_after_id=start_after_id,
    ):
        for entity in batch:
            report.total_entities += 1

            if target == TARGET_RESUMES:
                has_source = _resume_has_semantic_source(entity)
                raw_source = source_fn(entity)
            else:
                raw_source = source_fn(entity)
                has_source = bool(raw_source)

            if has_source:
                report.eligible_entities += 1
                report.entities_with_raw_skill_source += 1

            normalized_entries = list(getattr(entity, normalized_field, []) or [])
            if normalized_entries:
                report.entities_with_normalized_payload += 1
                summary = summarize_normalized_skill_entries(normalized_entries)
                report.matched_entries += summary.matched_entries
                report.official_match_entries += summary.official_matches
                report.legacy_match_entries += summary.legacy_matches
                report.unmatched_entries += summary.unmatched_entries
                if summary.official_matches > 0:
                    report.entities_with_official_match += 1
                if summary.legacy_matches > 0:
                    report.entities_with_legacy_match += 1
                if summary.matched_entries == 0 and summary.unmatched_entries > 0:
                    report.entities_with_unmatched_only += 1
                _append_counter_items(matched_counter, summary.matched_canonical_skills)
                _append_counter_items(unmatched_counter, summary.unmatched_raw_skills)
                _append_counter_items(unmatched_reason_counter, summary.unmatched_reasons)
            elif has_source and not getattr(entity, updated_at_field, None):
                report.pending_entities += 1
                _append_counter_items(pending_counter, raw_source)

            if str(getattr(entity, error_field, "") or "").strip():
                report.entities_with_errors += 1

            if target == TARGET_RESUMES:
                metadata = getattr(entity, "semantic_resume_metadata", {}) or {}
                rejected_entries = metadata.get("rejected_raw_candidates", [])
                if isinstance(rejected_entries, list):
                    for rejected_entry in rejected_entries:
                        if not isinstance(rejected_entry, dict):
                            continue
                        text = str(rejected_entry.get("text") or "").strip()
                        reason = str(rejected_entry.get("reason") or "").strip()
                        if text:
                            rejected_candidate_counter[text] += 1
                        if reason:
                            rejected_reason_counter[reason] += 1

    report.top_unmatched_skills = _top_counter(unmatched_counter, top_n=top_n)
    report.top_unmatched_reasons = _top_counter(unmatched_reason_counter, top_n=top_n)
    report.top_matched_skills = _top_counter(matched_counter, top_n=top_n)
    report.top_pending_raw_skills = _top_counter(pending_counter, top_n=top_n)
    report.top_rejected_candidates = _top_counter(rejected_candidate_counter, top_n=top_n)
    report.top_rejected_candidate_reasons = _top_counter(rejected_reason_counter, top_n=top_n)
    return report


def build_esco_normalization_report(
    *,
    target: str = TARGET_ALL,
    chunk_size: int = 200,
    limit: int | None = None,
    start_after_id: int | None = None,
    top_n: int = 10,
) -> dict[str, dict[str, object]]:
    if target not in VALID_TARGETS:
        raise ValueError(f"Unsupported target: {target}")

    selected_targets = (
        [TARGET_OPPORTUNITIES, TARGET_PROFILES, TARGET_RESUMES]
        if target == TARGET_ALL
        else [target]
    )

    report = {}
    for selected_target in selected_targets:
        report[selected_target] = _scan_coverage_for_target(
            selected_target,
            chunk_size=chunk_size,
            limit=limit,
            start_after_id=start_after_id,
            top_n=top_n,
        ).as_dict()
    return report
