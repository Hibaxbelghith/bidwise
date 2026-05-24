import logging

from celery import shared_task
from django.db import close_old_connections, connection, transaction
from django.utils import timezone

from ai.esco_skill_storage import (
    SkillNormalizationStoragePayload,
    build_skill_normalization_payload,
    build_skill_storage_hash,
    clean_skill_storage_list,
    safe_normalization_error,
    summarize_normalized_skill_entries,
)
from opportunities.models import Opportunite
from users.models import Profil


logger = logging.getLogger(__name__)


def _resolve_profile_raw_skills(profile) -> list[str]:
    stored_raw_skills = clean_skill_storage_list(getattr(profile, "raw_skills", []))
    if stored_raw_skills:
        return stored_raw_skills
    return clean_skill_storage_list(getattr(profile, "competences", []))


def _resolve_opportunity_raw_skills(opportunity) -> list[str]:
    stored_raw_skills = clean_skill_storage_list(getattr(opportunity, "raw_skills", []))
    if stored_raw_skills:
        return stored_raw_skills
    return clean_skill_storage_list(getattr(opportunity, "skills", []))


def _set_profile_skill_storage_state(
    profile: Profil,
    *,
    payload: SkillNormalizationStoragePayload,
    error: str,
) -> list[str]:
    update_fields = []

    if list(getattr(profile, "raw_skills", []) or []) != payload.raw_skills:
        profile.raw_skills = payload.raw_skills
        update_fields.append("raw_skills")
    if list(getattr(profile, "normalized_skills", []) or []) != payload.normalized_skills:
        profile.normalized_skills = payload.normalized_skills
        update_fields.append("normalized_skills")
    if getattr(profile, "skills_normalization_hash", "") != payload.content_hash:
        profile.skills_normalization_hash = payload.content_hash
        update_fields.append("skills_normalization_hash")
    if getattr(profile, "skills_normalization_error", "") != error:
        profile.skills_normalization_error = error
        update_fields.append("skills_normalization_error")

    profile.skills_normalization_updated_at = timezone.now()
    update_fields.append("skills_normalization_updated_at")
    return update_fields


def _set_opportunity_skill_storage_state(
    opportunity: Opportunite,
    *,
    payload: SkillNormalizationStoragePayload,
    error: str,
) -> list[str]:
    update_fields = []

    if list(getattr(opportunity, "raw_skills", []) or []) != payload.raw_skills:
        opportunity.raw_skills = payload.raw_skills
        update_fields.append("raw_skills")
    if list(getattr(opportunity, "normalized_skills", []) or []) != payload.normalized_skills:
        opportunity.normalized_skills = payload.normalized_skills
        update_fields.append("normalized_skills")
    if getattr(opportunity, "skills_normalization_hash", "") != payload.content_hash:
        opportunity.skills_normalization_hash = payload.content_hash
        update_fields.append("skills_normalization_hash")
    if getattr(opportunity, "skills_normalization_error", "") != error:
        opportunity.skills_normalization_error = error
        update_fields.append("skills_normalization_error")

    opportunity.skills_normalization_updated_at = timezone.now()
    update_fields.append("skills_normalization_updated_at")
    return update_fields


def enqueue_profile_skill_normalization(profile_id) -> bool:
    try:
        normalize_profile_skills_storage.delay(profile_id)
    except Exception:
        logger.exception("profile skill normalization enqueue failed profile_id=%s", profile_id)
        return False
    return True


def enqueue_opportunity_skill_normalization(opportunity_id) -> bool:
    try:
        normalize_opportunity_skills_storage.delay(opportunity_id)
    except Exception:
        logger.exception("opportunity skill normalization enqueue failed opportunity_id=%s", opportunity_id)
        return False
    return True


def enqueue_opportunity_llm_enrichment(opportunity_id) -> bool:
    try:
        enrich_opportunity_with_llm_task.delay(opportunity_id)
    except Exception:
        logger.exception("opportunity LLM enrichment enqueue failed opportunity_id=%s", opportunity_id)
        return False
    return True


@shared_task(
    name="ai.normalize_profile_skills_storage",
    max_retries=0,
)
def normalize_profile_skills_storage(profile_id, *, force=False):
    if not connection.in_atomic_block:
        close_old_connections()
    try:
        profile_id = int(profile_id)
    except (TypeError, ValueError):
        return {"status": "skipped", "reason": "invalid_profile_id"}

    try:
        profile = Profil.objects.only(
            "id",
            "competences",
            "raw_skills",
            "normalized_skills",
            "skills_normalization_hash",
            "skills_normalization_updated_at",
            "skills_normalization_error",
        ).get(pk=profile_id)
    except Profil.DoesNotExist:
        return {"status": "skipped", "reason": "missing_profile", "profile_id": profile_id}

    raw_skills = _resolve_profile_raw_skills(profile)
    content_hash = build_skill_storage_hash(raw_skills)
    if (
        not force
        and getattr(profile, "skills_normalization_hash", "") == content_hash
        and getattr(profile, "skills_normalization_updated_at", None)
    ):
        return {"status": "skipped", "reason": "fresh", "profile_id": profile_id}

    error = ""
    try:
        payload = build_skill_normalization_payload(raw_skills)
    except Exception as exc:  # noqa: BLE001 - normalization must fail soft
        error = safe_normalization_error(exc)
        logger.exception("profile skill normalization failed profile_id=%s", profile_id)
        payload = SkillNormalizationStoragePayload(
            raw_skills=raw_skills,
            normalized_skills=[],
            content_hash=content_hash,
        )

    with transaction.atomic():
        try:
            locked_profile = Profil.objects.select_for_update().get(pk=profile_id)
        except Profil.DoesNotExist:
            return {"status": "skipped", "reason": "missing_profile", "profile_id": profile_id}

        latest_raw_skills = _resolve_profile_raw_skills(locked_profile)
        latest_hash = build_skill_storage_hash(latest_raw_skills)
        if not force and latest_hash != content_hash:
            return {"status": "skipped", "reason": "content_changed", "profile_id": profile_id}
        if (
            not force
            and getattr(locked_profile, "skills_normalization_hash", "") == latest_hash
            and getattr(locked_profile, "skills_normalization_updated_at", None)
        ):
            return {"status": "skipped", "reason": "fresh_after_lock", "profile_id": profile_id}

        persisted_payload = SkillNormalizationStoragePayload(
            raw_skills=latest_raw_skills,
            normalized_skills=payload.normalized_skills,
            content_hash=latest_hash,
        )
        update_fields = _set_profile_skill_storage_state(
            locked_profile,
            payload=persisted_payload,
            error=error,
        )
        locked_profile.save(update_fields=update_fields)

    summary = summarize_normalized_skill_entries(payload.normalized_skills)
    return {
        "status": "updated",
        "profile_id": profile_id,
        "raw_skills_count": len(payload.raw_skills),
        "normalized_skills_count": len(payload.normalized_skills),
        "matched_count": summary.matched_entries,
        "unmatched_count": summary.unmatched_entries,
        "official_matches": summary.official_matches,
        "legacy_matches": summary.legacy_matches,
        "error": error,
    }


@shared_task(
    name="ai.normalize_opportunity_skills_storage",
    max_retries=0,
)
def normalize_opportunity_skills_storage(opportunity_id, *, force=False):
    if not connection.in_atomic_block:
        close_old_connections()
    try:
        opportunity_id = int(opportunity_id)
    except (TypeError, ValueError):
        return {"status": "skipped", "reason": "invalid_opportunity_id"}

    try:
        opportunity = Opportunite.objects.only(
            "id",
            "skills",
            "raw_skills",
            "normalized_skills",
            "skills_normalization_hash",
            "skills_normalization_updated_at",
            "skills_normalization_error",
        ).get(pk=opportunity_id)
    except Opportunite.DoesNotExist:
        return {"status": "skipped", "reason": "missing_opportunity", "opportunity_id": opportunity_id}

    raw_skills = _resolve_opportunity_raw_skills(opportunity)
    content_hash = build_skill_storage_hash(raw_skills)
    if (
        not force
        and getattr(opportunity, "skills_normalization_hash", "") == content_hash
        and getattr(opportunity, "skills_normalization_updated_at", None)
    ):
        return {"status": "skipped", "reason": "fresh", "opportunity_id": opportunity_id}

    error = ""
    try:
        payload = build_skill_normalization_payload(raw_skills)
    except Exception as exc:  # noqa: BLE001 - normalization must fail soft
        error = safe_normalization_error(exc)
        logger.exception("opportunity skill normalization failed opportunity_id=%s", opportunity_id)
        payload = SkillNormalizationStoragePayload(
            raw_skills=raw_skills,
            normalized_skills=[],
            content_hash=content_hash,
        )

    with transaction.atomic():
        try:
            locked_opportunity = Opportunite.objects.select_for_update().get(pk=opportunity_id)
        except Opportunite.DoesNotExist:
            return {"status": "skipped", "reason": "missing_opportunity", "opportunity_id": opportunity_id}

        latest_raw_skills = _resolve_opportunity_raw_skills(locked_opportunity)
        latest_hash = build_skill_storage_hash(latest_raw_skills)
        if not force and latest_hash != content_hash:
            return {"status": "skipped", "reason": "content_changed", "opportunity_id": opportunity_id}
        if (
            not force
            and getattr(locked_opportunity, "skills_normalization_hash", "") == latest_hash
            and getattr(locked_opportunity, "skills_normalization_updated_at", None)
        ):
            return {"status": "skipped", "reason": "fresh_after_lock", "opportunity_id": opportunity_id}

        persisted_payload = SkillNormalizationStoragePayload(
            raw_skills=latest_raw_skills,
            normalized_skills=payload.normalized_skills,
            content_hash=latest_hash,
        )
        update_fields = _set_opportunity_skill_storage_state(
            locked_opportunity,
            payload=persisted_payload,
            error=error,
        )
        locked_opportunity.save(update_fields=update_fields)

    summary = summarize_normalized_skill_entries(payload.normalized_skills)
    return {
        "status": "updated",
        "opportunity_id": opportunity_id,
        "raw_skills_count": len(payload.raw_skills),
        "normalized_skills_count": len(payload.normalized_skills),
        "matched_count": summary.matched_entries,
        "unmatched_count": summary.unmatched_entries,
        "official_matches": summary.official_matches,
        "legacy_matches": summary.legacy_matches,
        "error": error,
    }


@shared_task(
    name="ai.enrich_opportunity_with_llm",
    max_retries=0,
)
def enrich_opportunity_with_llm_task(opportunity_id, *, force=False, apply_skills=True):
    if not connection.in_atomic_block:
        close_old_connections()
    from ai.llm.opportunity_enrichment import enrich_opportunity_with_llm

    return enrich_opportunity_with_llm(
        opportunity_id,
        force=bool(force),
        apply_skills=bool(apply_skills),
    )
