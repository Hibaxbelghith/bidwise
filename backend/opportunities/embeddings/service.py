import logging
import math
import os
from functools import lru_cache

from django.conf import settings

from opportunities.nlp.nlp_preprocessing import prepare_combined_text


logger = logging.getLogger(__name__)

EMBEDDING_MODELS = {
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    "BAAI/bge-small-en-v1.5",
    "sentence-transformers/all-MiniLM-L6-v2",
}

DEFAULT_EMBEDDING_MODEL = getattr(
    settings,
    "OPPORTUNITY_EMBEDDING_MODEL",
    os.getenv(
        "OPPORTUNITY_EMBEDDING_MODEL",
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    ),
)

DEFAULT_BATCH_SIZE = int(
    getattr(settings, "OPPORTUNITY_EMBEDDING_BATCH_SIZE", os.getenv("OPPORTUNITY_EMBEDDING_BATCH_SIZE", 32))
)
DEFAULT_EMBEDDING_MODEL_VERSION = getattr(
    settings,
    "OPPORTUNITY_EMBEDDING_MODEL_VERSION",
    os.getenv("OPPORTUNITY_EMBEDDING_MODEL_VERSION", "v1"),
)


def resolve_model_name(model_name=None):
    selected = (model_name or DEFAULT_EMBEDDING_MODEL).strip()
    if selected not in EMBEDDING_MODELS:
        valid_models = ", ".join(sorted(EMBEDDING_MODELS))
        raise ValueError(f"Unsupported embedding model '{selected}'. Available: {valid_models}")
    return selected


def resolve_model_version(model_version=None):
    value = (model_version or DEFAULT_EMBEDDING_MODEL_VERSION).strip()
    return value or "v1"


def build_embedding_model_identifier(model_name=None, model_version=None):
    selected_model = resolve_model_name(model_name)
    selected_version = resolve_model_version(model_version)
    return f"{selected_model}@{selected_version}"


def _load_sentence_transformer(model_name):
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError(
            "sentence-transformers is required. Install dependencies before running embeddings commands."
        ) from exc

    logger.info("Loading embedding model '%s' on CPU", model_name)
    return SentenceTransformer(model_name, device="cpu")


@lru_cache(maxsize=8)
def _get_cached_model(model_name):
    return _load_sentence_transformer(model_name)


def clear_model_cache():
    _get_cached_model.cache_clear()


def _normalize_encode_input(text):
    value = (text or "").strip()
    if not value:
        return ""
    return value


def _normalize_vector(vector):
    values = [float(item) for item in vector]
    norm = math.sqrt(sum(item * item for item in values))
    if norm == 0.0:
        return values
    return [item / norm for item in values]


def generate_embeddings_batch(texts, model_name=None, batch_size=None):
    prepared_texts = [_normalize_encode_input(text) for text in texts]
    if not prepared_texts:
        return []

    selected_model = resolve_model_name(model_name)
    model = _get_cached_model(selected_model)
    effective_batch_size = batch_size or DEFAULT_BATCH_SIZE

    vectors = model.encode(
        prepared_texts,
        batch_size=effective_batch_size,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    return [_normalize_vector(vector.tolist()) for vector in vectors]


def generate_embedding(text, model_name=None):
    value = _normalize_encode_input(text)
    if not value:
        return []
    return generate_embeddings_batch([value], model_name=model_name, batch_size=1)[0]


def generate_opportunity_embedding(opportunity, model_name=None):
    combined = prepare_combined_text(opportunity)
    if not combined:
        return []
    return generate_embedding(combined, model_name=model_name)
