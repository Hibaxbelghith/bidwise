import hashlib
import json
import logging
import math
import os
import re
from contextlib import nullcontext

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from opportunities.embeddings.service import build_embedding_model_identifier, generate_embedding
from .user_features import build_user_features


logger = logging.getLogger(__name__)

DEFAULT_PROVIDER = getattr(
    settings,
    "USER_EMBEDDING_PROVIDER",
    os.getenv("USER_EMBEDDING_PROVIDER", "local"),
)
DEFAULT_OPENAI_MODEL = getattr(
    settings,
    "USER_OPENAI_EMBEDDING_MODEL",
    os.getenv("USER_OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
)
MAX_RESUME_EMBEDDING_TEXT_CHARS = 4000
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")
_WHITESPACE_RE = re.compile(r"\s+")
_HASH_LIST_FIELDS = (
    "skills",
    "profile_skills",
    "semantic_resume_skills",
    "semantic_resume_domains",
    "semantic_resume_tools",
    "semantic_resume_languages",
    "target_roles",
    "interests",
    "locations",
    "work_modes",
    "employment_types",
)
_HASH_CASEFOLD_SCALAR_FIELDS = (
    "experience_level",
    "remote",
    "salary_currency",
    "salary_period",
)
_HASH_SCALAR_FIELDS = (
    "experience_years",
    "salary",
    "semantic_resume_confidence",
)


def _as_list(value):
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if value:
        return [str(value).strip()]
    return []


def _clean_resume_embedding_text(value):
    if value is None:
        return ""

    text = _CONTROL_CHARS_RE.sub(" ", str(value))
    text = _WHITESPACE_RE.sub(" ", text).strip()
    if len(text) > MAX_RESUME_EMBEDDING_TEXT_CHARS:
        text = text[:MAX_RESUME_EMBEDDING_TEXT_CHARS].rstrip()
    return text


def _clean_hash_text(value):
    if value is None:
        return ""
    return _WHITESPACE_RE.sub(" ", str(value)).strip()


def _canonical_hash_list(value):
    normalized = set()
    for item in _as_list(value):
        text = _clean_hash_text(item)
        if not text:
            continue
        normalized.add(text.casefold())
    return sorted(normalized)


def build_profile_embedding_content_payload(features):
    """Return the deterministic semantic profile payload used for staleness checks."""
    if not isinstance(features, dict):
        return {}

    payload = {}
    for field in _HASH_LIST_FIELDS:
        source_value = features.get(field)
        if field == "target_roles" and not source_value:
            source_value = features.get("roles")
        if field == "locations" and not source_value:
            source_value = features.get("location")
        payload[field] = _canonical_hash_list(source_value)
    for field in _HASH_CASEFOLD_SCALAR_FIELDS:
        payload[field] = _clean_hash_text(features.get(field)).casefold()
    for field in _HASH_SCALAR_FIELDS:
        payload[field] = _clean_hash_text(features.get(field))
    has_structured_resume = bool(
        _canonical_hash_list(features.get("semantic_resume_skills"))
        or _canonical_hash_list(features.get("semantic_resume_domains"))
        or _canonical_hash_list(features.get("semantic_resume_tools"))
    )
    payload["resume_text"] = (
        ""
        if has_structured_resume
        else _clean_resume_embedding_text(features.get("resume_text"))
    )
    return payload


def build_user_embedding_text(features):
    """Build a stable text representation from normalized user features."""
    if not isinstance(features, dict):
        return ""

    parts = []
    skills = _as_list(features.get("skills"))
    profile_skills = _as_list(features.get("profile_skills"))
    semantic_resume_skills = _as_list(features.get("semantic_resume_skills"))
    semantic_resume_domains = _as_list(features.get("semantic_resume_domains"))
    semantic_resume_tools = _as_list(features.get("semantic_resume_tools"))
    roles = _as_list(features.get("target_roles")) or _as_list(features.get("roles"))
    interests = _as_list(features.get("interests"))
    locations = _as_list(features.get("locations")) or _as_list(features.get("location"))
    work_modes = _as_list(features.get("work_modes"))
    employment_types = _as_list(features.get("employment_types"))

    if profile_skills:
        parts.append(f"profile skills: {', '.join(profile_skills)}")
    elif skills:
        parts.append(f"skills: {', '.join(skills)}")
    if semantic_resume_skills:
        parts.append(f"resume extracted skills: {', '.join(semantic_resume_skills)}")
    if semantic_resume_tools:
        parts.append(f"resume extracted tools: {', '.join(semantic_resume_tools)}")
    if semantic_resume_domains:
        parts.append(f"resume inferred domains: {', '.join(semantic_resume_domains)}")
    if roles:
        parts.append(f"target roles: {', '.join(roles)}")
    if interests:
        parts.append(f"industries: {', '.join(interests)}")
    if features.get("experience_level"):
        parts.append(f"experience level: {features['experience_level']}")
    if features.get("experience_years") is not None:
        parts.append(f"years of experience: {features['experience_years']}")
    if locations:
        label = "locations" if len(locations) > 1 else "location"
        parts.append(f"{label}: {', '.join(locations)}")
    if features.get("remote"):
        parts.append(f"remote preference: {features['remote']}")
    if work_modes:
        parts.append(f"work modes: {', '.join(work_modes)}")
    if employment_types:
        parts.append(f"employment types: {', '.join(employment_types)}")
    if features.get("salary") is not None:
        salary_parts = [str(features["salary"])]
        if features.get("salary_currency"):
            salary_parts.append(str(features["salary_currency"]))
        if features.get("salary_period"):
            salary_parts.append(str(features["salary_period"]))
        parts.append(f"salary expectation: {' '.join(salary_parts)}")
    has_structured_resume = bool(semantic_resume_skills or semantic_resume_domains or semantic_resume_tools)
    resume_text = "" if has_structured_resume else _clean_resume_embedding_text(features.get("resume_text"))
    if resume_text:
        parts.append(f"resume: {resume_text}")

    return "\n".join(parts)


def _build_openai_embedding(text, model_name=None):
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required for OpenAI user embeddings.")

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError(
            "The openai package is required when USER_EMBEDDING_PROVIDER=openai."
        ) from exc

    client = OpenAI(api_key=api_key)
    response = client.embeddings.create(
        model=model_name or DEFAULT_OPENAI_MODEL,
        input=text,
    )
    return [float(value) for value in response.data[0].embedding]


def build_user_embedding(features):
    """
    Convert features into text and generate an embedding.

    The default provider reuses the local opportunity embedding model so user
    vectors and opportunity vectors have compatible dimensions. Set
    USER_EMBEDDING_PROVIDER=openai to use OpenAI embeddings in deployments that
    also store opportunity vectors from the same embedding family.
    """
    text = build_user_embedding_text(features)
    if not text:
        return []

    provider = str(DEFAULT_PROVIDER or "local").strip().lower()
    if provider == "openai":
        return _build_openai_embedding(text)
    if provider != "local":
        raise ValueError(f"Unsupported user embedding provider '{provider}'.")

    return generate_embedding(text)


def _has_vector(value):
    return isinstance(value, list) and bool(value)


def profile_embedding_has_semantic_content(features):
    return bool(build_user_embedding_text(features).strip())


def build_user_features_hash(features):
    """Return a stable content hash for semantic profile embedding inputs."""
    payload = build_profile_embedding_content_payload(features)
    serialized = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def build_profile_embedding_content_hash(profile):
    return build_user_features_hash(build_user_features(profile))


def get_current_profile_embedding_model():
    return build_embedding_model_identifier()


def get_expected_profile_embedding_dimensions():
    try:
        return int(getattr(settings, "OPPORTUNITY_PGVECTOR_DIMENSIONS", 384) or 384)
    except (TypeError, ValueError):
        return 384


def validate_profile_embedding_vector(vector, expected_dimensions=None):
    expected = expected_dimensions or get_expected_profile_embedding_dimensions()
    if not isinstance(vector, list) or not vector:
        raise ValueError("Profile embedding must be a non-empty list.")
    if len(vector) != expected:
        raise ValueError(
            f"Profile embedding dimension mismatch: expected {expected}, got {len(vector)}."
        )

    values = []
    for item in vector:
        try:
            value = float(item)
        except (TypeError, ValueError) as exc:
            raise ValueError("Profile embedding contains a non-numeric value.") from exc
        if math.isnan(value) or math.isinf(value):
            raise ValueError("Profile embedding contains NaN or infinite values.")
        values.append(value)
    return values


def _profile_embedding_vector_is_valid(profile):
    try:
        validate_profile_embedding_vector(getattr(profile, "embedding", None))
    except ValueError:
        return False
    return True


def profile_embedding_needs_refresh(profile, features=None, content_hash=None):
    if profile is None:
        return True

    features = features if features is not None else build_user_features(profile)
    content_hash = content_hash or build_user_features_hash(features)
    expected_model = get_current_profile_embedding_model()
    expected_dimensions = get_expected_profile_embedding_dimensions()

    if not _profile_embedding_vector_is_valid(profile):
        return True
    if not getattr(profile, "embedding_model", ""):
        return True
    if not getattr(profile, "embedding_updated_at", None):
        return True
    if not getattr(profile, "embedding_content_hash", ""):
        return True
    if getattr(profile, "embedding_model", "") != expected_model:
        return True
    if getattr(profile, "embedding_dimensions", None) != expected_dimensions:
        return True
    if getattr(profile, "embedding_content_hash", "") != content_hash:
        return True
    return False


def profile_embedding_is_stale(profile, features=None, content_hash=None):
    return profile_embedding_needs_refresh(
        profile,
        features=features,
        content_hash=content_hash,
    )


def store_profile_embedding(profile, embedding, content_hash=None, updated_at=None):
    vector = validate_profile_embedding_vector(embedding)
    content_hash = content_hash or build_profile_embedding_content_hash(profile)
    current_time = updated_at or timezone.now()

    context = transaction.atomic() if hasattr(profile, "_meta") else nullcontext()
    with context:
        profile.embedding = vector
        profile.embedding_features_hash = content_hash
        profile.last_embedding_update = current_time
        profile.embedding_model = get_current_profile_embedding_model()
        profile.embedding_dimensions = len(vector)
        profile.embedding_updated_at = current_time
        profile.embedding_content_hash = content_hash
        profile.save(
            update_fields=[
                "embedding",
                "embedding_features_hash",
                "last_embedding_update",
                "embedding_model",
                "embedding_dimensions",
                "embedding_updated_at",
                "embedding_content_hash",
            ]
        )
    return vector


def enqueue_profile_embedding_refresh(profile_id):
    try:
        profile_id = int(profile_id)
    except (TypeError, ValueError):
        logger.warning(
            "profile embedding enqueue skipped reason=invalid_profile_id profile_id=%s",
            profile_id,
            extra={"profile_id": profile_id, "reason": "invalid_profile_id"},
        )
        return False

    try:
        from users.tasks import generate_profile_embedding

        generate_profile_embedding.delay(profile_id)
    except Exception:
        logger.exception(
            "profile embedding enqueue failed profile_id=%s",
            profile_id,
            extra={"profile_id": profile_id},
        )
        return False
    return True


def get_cached_profile_embedding_or_enqueue(profile):
    if profile is None:
        return []

    features = build_user_features(profile)
    content_hash = build_user_features_hash(features)
    if not profile_embedding_needs_refresh(
        profile,
        features=features,
        content_hash=content_hash,
    ):
        return validate_profile_embedding_vector(profile.embedding)

    if profile_embedding_has_semantic_content(features):
        enqueue_profile_embedding_refresh(getattr(profile, "pk", None))
    return []


def build_legacy_user_features_hash(features):
    """Return the pre-metadata hash shape retained only for compatibility checks."""
    payload = json.dumps(
        features or {},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def get_or_build_profile_embedding(profile, force=False):
    """
    Return a cached profile embedding, generating and persisting it when needed.

    This keeps recommendation requests cheap after the first generation and
    allows profile updates to invalidate the cache without recomputing inline.
    """
    features = build_user_features(profile)
    content_hash = build_user_features_hash(features)

    if not force and not profile_embedding_needs_refresh(
        profile,
        features=features,
        content_hash=content_hash,
    ):
        return profile.embedding

    embedding = build_user_embedding(features)
    if not _has_vector(embedding):
        return []
    embedding = validate_profile_embedding_vector(embedding)

    return store_profile_embedding(profile, embedding, content_hash=content_hash)
