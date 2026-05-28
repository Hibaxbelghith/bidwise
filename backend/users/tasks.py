import logging

from celery import shared_task
from django.conf import settings
from django.db import close_old_connections, transaction
from django.utils import timezone

from ai.embeddings import (
    build_user_embedding,
    build_user_embedding_text,
    build_user_features_hash,
    enqueue_profile_embedding_refresh,
    profile_embedding_needs_refresh,
    store_profile_embedding,
    validate_profile_embedding_vector,
)
from ai.user_features import build_user_features
from users.models import Profil, ProfileResume
from users.resume_parsing import parse_resume_file
from users.resume_parsing.exceptions import (
    EmptyResumeTextError,
    ResumeParsingError,
    UnsupportedResumeFormat,
)
from users.resume_processing import build_resume_text_embedding_source
from users.resume_semantic.models import SEMANTIC_STATUS_FAILED, SEMANTIC_STATUS_PROCESSING
from users.resume_semantic.service import clear_resume_semantics, process_profile_resume_semantics


logger = logging.getLogger(__name__)

MAX_PARSING_ERROR_CHARS = 500


def _safe_error_message(exc):
    message = str(exc).strip() or exc.__class__.__name__
    return message[:MAX_PARSING_ERROR_CHARS]


@shared_task(
    name="users.generate_profile_embedding",
    max_retries=0,
)
def generate_profile_embedding(profile_id):
    close_old_connections()
    try:
        profile_id = int(profile_id)
    except (TypeError, ValueError):
        logger.warning(
            "profile embedding task skipped reason=invalid_profile_id profile_id=%s",
            profile_id,
            extra={"profile_id": profile_id, "reason": "invalid_profile_id"},
        )
        return {"status": "skipped", "reason": "invalid_profile_id"}

    try:
        profile = Profil.objects.get(pk=profile_id)
    except Profil.DoesNotExist:
        logger.info(
            "profile embedding task skipped reason=missing_profile profile_id=%s",
            profile_id,
            extra={"profile_id": profile_id, "reason": "missing_profile"},
        )
        return {"status": "skipped", "reason": "missing_profile", "profile_id": profile_id}

    features = build_user_features(profile)
    content_hash = build_user_features_hash(features)
    if not profile_embedding_needs_refresh(
        profile,
        features=features,
        content_hash=content_hash,
    ):
        logger.info(
            "profile embedding task skipped reason=fresh profile_id=%s",
            profile_id,
            extra={"profile_id": profile_id, "reason": "fresh"},
        )
        return {"status": "skipped", "reason": "fresh", "profile_id": profile_id}

    if not build_user_embedding_text(features).strip():
        logger.info(
            "profile embedding task skipped reason=empty_content profile_id=%s",
            profile_id,
            extra={"profile_id": profile_id, "reason": "empty_content"},
        )
        return {"status": "skipped", "reason": "empty_content", "profile_id": profile_id}

    try:
        vector = build_user_embedding(features)
        vector = validate_profile_embedding_vector(vector)
    except ValueError as exc:
        logger.warning(
            "profile embedding task rejected invalid vector profile_id=%s error=%s",
            profile_id,
            exc,
            extra={"profile_id": profile_id, "reason": "invalid_vector"},
        )
        return {
            "status": "failed",
            "reason": "invalid_vector",
            "profile_id": profile_id,
            "error": str(exc),
        }
    except Exception as exc:
        logger.exception(
            "profile embedding task failed during generation profile_id=%s",
            profile_id,
            extra={"profile_id": profile_id, "reason": "generation_failed"},
        )
        return {
            "status": "failed",
            "reason": "generation_failed",
            "profile_id": profile_id,
            "error": str(exc),
        }

    with transaction.atomic():
        try:
            locked_profile = Profil.objects.select_for_update().get(pk=profile_id)
        except Profil.DoesNotExist:
            logger.info(
                "profile embedding task skipped after generation reason=missing_profile profile_id=%s",
                profile_id,
                extra={"profile_id": profile_id, "reason": "missing_profile_after_generation"},
            )
            return {"status": "skipped", "reason": "missing_profile", "profile_id": profile_id}

        latest_features = build_user_features(locked_profile)
        latest_hash = build_user_features_hash(latest_features)
        if latest_hash != content_hash:
            logger.info(
                "profile embedding task skipped reason=content_changed profile_id=%s",
                profile_id,
                extra={"profile_id": profile_id, "reason": "content_changed"},
            )
            return {"status": "skipped", "reason": "content_changed", "profile_id": profile_id}

        if not profile_embedding_needs_refresh(
            locked_profile,
            features=latest_features,
            content_hash=latest_hash,
        ):
            logger.info(
                "profile embedding task skipped reason=fresh_after_lock profile_id=%s",
                profile_id,
                extra={"profile_id": profile_id, "reason": "fresh_after_lock"},
            )
            return {"status": "skipped", "reason": "fresh", "profile_id": profile_id}

        store_profile_embedding(locked_profile, vector, content_hash=latest_hash)

    logger.info(
        "profile embedding task completed profile_id=%s dimensions=%s",
        profile_id,
        len(vector),
        extra={"profile_id": profile_id, "dimensions": len(vector), "status": "updated"},
    )
    return {
        "status": "updated",
        "profile_id": profile_id,
        "dimensions": len(vector),
        "content_hash": content_hash,
    }


def enqueue_profile_resume_parse(resume_id):
    try:
        resume_id = int(resume_id)
    except (TypeError, ValueError):
        logger.warning(
            "resume parsing enqueue skipped reason=invalid_resume_id resume_id=%s",
            resume_id,
            extra={"resume_id": resume_id, "reason": "invalid_resume_id"},
        )
        return False

    try:
        parse_profile_resume.delay(resume_id)
    except Exception:
        logger.exception(
            "resume parsing enqueue failed resume_id=%s",
            resume_id,
            extra={"resume_id": resume_id},
        )
        return False
    return True


@shared_task(
    name="users.parse_profile_resume",
    max_retries=0,
    soft_time_limit=getattr(settings, "PROFILE_RESUME_TASK_SOFT_TIME_LIMIT_SECONDS", 150),
    time_limit=getattr(settings, "PROFILE_RESUME_TASK_TIME_LIMIT_SECONDS", 180),
)
def parse_profile_resume(resume_id):
    if not getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
        close_old_connections()
    try:
        resume_id = int(resume_id)
    except (TypeError, ValueError):
        logger.warning(
            "resume parsing task skipped reason=invalid_resume_id resume_id=%s",
            resume_id,
            extra={"resume_id": resume_id, "reason": "invalid_resume_id"},
        )
        return {"status": "skipped", "reason": "invalid_resume_id"}

    try:
        resume = ProfileResume.objects.select_related("profile").get(pk=resume_id)
    except ProfileResume.DoesNotExist:
        logger.info(
            "resume parsing task skipped reason=missing_resume resume_id=%s",
            resume_id,
            extra={"resume_id": resume_id, "reason": "missing_resume"},
        )
        return {"status": "skipped", "reason": "missing_resume", "resume_id": resume_id}

    ProfileResume.objects.filter(pk=resume_id).update(
        parsing_status=ProfileResume.ParsingStatus.PROCESSING,
        parsing_error="",
        semantic_resume_status=SEMANTIC_STATUS_PROCESSING,
        semantic_resume_error="",
    )

    parsed_text = ""
    parser = ""
    truncated = False
    status = ProfileResume.ParsingStatus.SUCCEEDED
    error = ""

    try:
        parsed = parse_resume_file(resume.file)
        parsed_text = parsed.text
        parser = parsed.parser
        truncated = parsed.truncated
    except EmptyResumeTextError as exc:
        status = ProfileResume.ParsingStatus.EMPTY
        error = _safe_error_message(exc)
    except UnsupportedResumeFormat as exc:
        status = ProfileResume.ParsingStatus.UNSUPPORTED
        error = _safe_error_message(exc)
    except ResumeParsingError as exc:
        status = ProfileResume.ParsingStatus.FAILED
        error = _safe_error_message(exc)
    except Exception as exc:
        logger.exception(
            "resume parsing task crashed resume_id=%s",
            resume_id,
            extra={"resume_id": resume_id, "reason": "unexpected_failure"},
        )
        status = ProfileResume.ParsingStatus.FAILED
        error = _safe_error_message(exc)

    with transaction.atomic():
        try:
            locked_resume = (
                ProfileResume.objects
                .select_for_update()
                .select_related("profile")
                .get(pk=resume_id)
            )
        except ProfileResume.DoesNotExist:
            logger.info(
                "resume parsing task skipped after parsing reason=missing_resume resume_id=%s",
                resume_id,
                extra={"resume_id": resume_id, "reason": "missing_resume_after_parsing"},
            )
            return {"status": "skipped", "reason": "missing_resume", "resume_id": resume_id}

        metadata = dict(locked_resume.metadata or {})
        metadata.update(
            {
                "parser": parser,
                "parsed_text_length": len(parsed_text),
                "parsed_text_truncated": truncated,
            }
        )

        locked_resume.parsed_text = parsed_text if status == ProfileResume.ParsingStatus.SUCCEEDED else ""
        locked_resume.parsing_status = status
        locked_resume.parsing_error = error
        locked_resume.parsed_at = timezone.now()
        locked_resume.metadata = metadata
        locked_resume.resume_text_embedding_source = (
            build_resume_text_embedding_source(locked_resume.profile, parsed_text)
            if status == ProfileResume.ParsingStatus.SUCCEEDED
            else ""
        )
        locked_resume.save(
            update_fields=[
                "parsed_text",
                "parsing_status",
                "parsing_error",
                "parsed_at",
                "metadata",
                "resume_text_embedding_source",
            ]
        )
        should_refresh_embedding = locked_resume.is_active
        profile_id = locked_resume.profile_id

    semantic_result = None
    if status == ProfileResume.ParsingStatus.SUCCEEDED:
        try:
            semantic_result = process_profile_resume_semantics(
                locked_resume,
                use_model=bool(getattr(settings, "PROFILE_RESUME_REALTIME_USE_MODEL", False)),
                allow_semantic_mapping=bool(
                    getattr(settings, "PROFILE_RESUME_REALTIME_ALLOW_SEMANTIC_MAPPING", False)
                ),
                use_llm=bool(getattr(settings, "PROFILE_RESUME_REALTIME_USE_LLM", False)),
                normalize_skills=bool(getattr(settings, "PROFILE_RESUME_REALTIME_NORMALIZE_SKILLS", False)),
                structured_llm_enabled=bool(
                    getattr(settings, "PROFILE_RESUME_STRUCTURED_LLM_ENABLED", False)
                ),
                structured_llm_fallback_enabled=bool(
                    getattr(settings, "PROFILE_RESUME_STRUCTURED_LLM_FALLBACK_ENABLED", True)
                ),
            )
        except Exception as exc:
            logger.exception(
                "resume semantic enrichment crashed resume_id=%s",
                resume_id,
                extra={"resume_id": resume_id, "reason": "semantic_unexpected_failure"},
            )
            clear_resume_semantics(
                locked_resume,
                status=SEMANTIC_STATUS_FAILED,
                error=_safe_error_message(exc),
            )
            semantic_result = {
                "status": SEMANTIC_STATUS_FAILED,
                "resume_id": resume_id,
                "error": _safe_error_message(exc),
            }
    else:
        clear_resume_semantics(
            locked_resume,
            status=SEMANTIC_STATUS_FAILED,
            error=error or f"Resume parsing ended with status {status}.",
        )
        semantic_result = {
            "status": SEMANTIC_STATUS_FAILED,
            "resume_id": resume_id,
            "error": error or f"Resume parsing ended with status {status}.",
        }

    if should_refresh_embedding:
        enqueue_profile_embedding_refresh(profile_id)

    logger.info(
        "resume parsing task completed resume_id=%s status=%s chars=%s",
        resume_id,
        status,
        len(parsed_text),
        extra={"resume_id": resume_id, "status": status, "chars": len(parsed_text)},
    )
    return {
        "status": status,
        "resume_id": resume_id,
        "profile_id": profile_id,
        "parsed_text_length": len(parsed_text),
        "parser": parser,
        "semantic": semantic_result,
    }
