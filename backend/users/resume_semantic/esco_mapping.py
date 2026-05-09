from __future__ import annotations

import logging
import math
import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable

from django.conf import settings

from .normalization import SYNONYM_TO_CANONICAL, dedupe_preserve_order, normalize_lookup_key, normalize_skill_label


logger = logging.getLogger(__name__)

DEFAULT_MAPPING_MODEL = getattr(
    settings,
    "RESUME_SEMANTIC_MAPPING_MODEL",
    os.getenv("RESUME_SEMANTIC_MAPPING_MODEL", "BAAI/bge-m3"),
)
FALLBACK_MAPPING_MODEL = getattr(
    settings,
    "RESUME_SEMANTIC_MAPPING_FALLBACK_MODEL",
    os.getenv(
        "RESUME_SEMANTIC_MAPPING_FALLBACK_MODEL",
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    ),
)
SEMANTIC_MAPPING_THRESHOLD = float(
    getattr(settings, "RESUME_SEMANTIC_MAPPING_THRESHOLD", os.getenv("RESUME_SEMANTIC_MAPPING_THRESHOLD", "0.68"))
)


@dataclass(frozen=True)
class EscoSkill:
    canonical: str
    kind: str
    aliases: tuple[str, ...]
    description: str


ESCO_SKILLS = (
    EscoSkill("python", "skill", ("python", "بايثون"), "Python programming language"),
    EscoSkill("django", "tool", ("django", "django rest", "django rest framework"), "Django web framework"),
    EscoSkill("fastapi", "tool", ("fastapi",), "FastAPI Python web framework"),
    EscoSkill("postgresql", "tool", ("postgresql", "postgres"), "PostgreSQL relational database"),
    EscoSkill("redis", "tool", ("redis",), "Redis cache and queue infrastructure"),
    EscoSkill("celery", "tool", ("celery",), "Celery asynchronous task processing"),
    EscoSkill("rest api", "skill", ("rest api", "api rest", "واجهات api", "واجهات برمجة التطبيقات"), "REST API design and implementation"),
    EscoSkill("react", "tool", ("react", "react.js"), "React frontend framework"),
    EscoSkill("typescript", "skill", ("typescript", "ts"), "TypeScript programming language"),
    EscoSkill("javascript", "skill", ("javascript", "js", "جافاسكريبت"), "JavaScript programming language"),
    EscoSkill("css", "skill", ("css",), "CSS styling"),
    EscoSkill("docker", "tool", ("docker",), "Docker containerization"),
    EscoSkill("kubernetes", "tool", ("kubernetes", "k8s"), "Kubernetes container orchestration"),
    EscoSkill("devops", "domain", ("devops", "ci/cd", "ci cd", "cicd", "ci-cd", "ci/cd pipelines"), "DevOps and CI/CD practices"),
    EscoSkill("terraform", "tool", ("terraform",), "Terraform infrastructure as code"),
    EscoSkill("aws", "tool", ("aws", "amazon web services"), "Amazon Web Services cloud platform"),
    EscoSkill("azure", "tool", ("azure",), "Microsoft Azure cloud platform"),
    EscoSkill("github actions", "tool", ("github actions",), "GitHub Actions CI/CD"),
    EscoSkill("gitlab ci", "tool", ("gitlab ci",), "GitLab CI/CD"),
    EscoSkill("git", "tool", ("git",), "Git version control"),
    EscoSkill("machine learning", "domain", ("machine learning", "ml", "pytorch", "scikit-learn", "تعلم الآلة", "ذكاء اصطناعي", "intelligence artificielle", "apprentissage automatique"), "Machine learning and AI engineering"),
    EscoSkill("natural language processing", "domain", ("nlp", "natural language processing"), "Natural language processing"),
    EscoSkill("sql", "skill", ("sql",), "SQL querying and data modeling"),
    EscoSkill("apache airflow", "tool", ("airflow", "apache airflow"), "Apache Airflow orchestration"),
    EscoSkill("apache spark", "tool", ("spark", "apache spark"), "Apache Spark data processing"),
    EscoSkill("data engineering", "domain", ("data engineering", "data pipelines", "etl", "elt"), "Data engineering and pipelines"),
    EscoSkill("cybersecurity", "domain", ("cybersecurity", "security", "siem", "incident response"), "Cybersecurity operations"),
    EscoSkill("accounting", "domain", ("accounting", "comptabilité", "comptabilite", "محاسبة"), "Accounting and finance operations"),
    EscoSkill("human resources", "domain", ("human resources", "hr", "recruitment", "ressources humaines", "موارد بشرية"), "Human resources and recruitment"),
    EscoSkill("nursing", "domain", ("nursing", "soins infirmiers", "تمريض"), "Nursing and clinical care"),
    EscoSkill("backend", "domain", ("backend", "backend engineering", "api platform"), "Backend software engineering"),
    EscoSkill("frontend", "domain", ("frontend", "frontend engineering"), "Frontend software engineering"),
    EscoSkill("web development", "domain", ("web development", "développement web", "developpement web", "تطوير الويب"), "Web application development"),
)

ESCO_BY_ALIAS = {
    normalize_lookup_key(alias): skill
    for skill in ESCO_SKILLS
    for alias in skill.aliases
}
ESCO_BY_CANONICAL = {skill.canonical: skill for skill in ESCO_SKILLS}


@lru_cache(maxsize=2)
def _load_sentence_transformer(model_name: str):
    from sentence_transformers import SentenceTransformer

    logger.info("Loading resume semantic mapping model '%s' on CPU", model_name)
    return SentenceTransformer(model_name, device="cpu")


def _encode_with_model(texts: list[str], model_name: str) -> list[list[float]]:
    model = _load_sentence_transformer(model_name)
    vectors = model.encode(
        texts,
        batch_size=32,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    return [vector.tolist() for vector in vectors]


@lru_cache(maxsize=2)
def _canonical_embeddings(model_name: str) -> tuple[tuple[float, ...], ...]:
    texts = [
        f"{skill.canonical}. {skill.description}. aliases: {', '.join(skill.aliases)}"
        for skill in ESCO_SKILLS
    ]
    return tuple(tuple(vector) for vector in _encode_with_model(texts, model_name))


def _cosine(left: Iterable[float], right: Iterable[float]) -> float:
    left_values = [float(value) for value in left]
    right_values = [float(value) for value in right]
    if len(left_values) != len(right_values) or not left_values:
        return 0.0
    numerator = sum(a * b for a, b in zip(left_values, right_values))
    left_norm = math.sqrt(sum(value * value for value in left_values))
    right_norm = math.sqrt(sum(value * value for value in right_values))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return max(0.0, min(1.0, numerator / (left_norm * right_norm)))


def _map_lexically(label: str) -> EscoSkill | None:
    normalized = normalize_lookup_key(label)
    if not normalized:
        return None
    synonym = normalize_skill_label(label)
    if synonym in ESCO_BY_CANONICAL:
        return ESCO_BY_CANONICAL[synonym]
    if normalized in ESCO_BY_ALIAS:
        return ESCO_BY_ALIAS[normalized]
    if synonym in SYNONYM_TO_CANONICAL.values() and synonym in ESCO_BY_CANONICAL:
        return ESCO_BY_CANONICAL[synonym]
    return None


def _map_semantically(label: str, *, threshold: float) -> tuple[EscoSkill | None, float, str]:
    texts = [label]
    for model_name in (DEFAULT_MAPPING_MODEL, FALLBACK_MAPPING_MODEL):
        try:
            candidate_vector = _encode_with_model(texts, model_name)[0]
            canonical_vectors = _canonical_embeddings(model_name)
        except Exception:
            logger.warning(
                "Resume semantic mapping model unavailable; falling back to lexical mapping model=%s",
                model_name,
                exc_info=True,
            )
            continue
        scores = [_cosine(candidate_vector, vector) for vector in canonical_vectors]
        best_index = max(range(len(scores)), key=lambda index: scores[index])
        best_score = scores[best_index]
        if best_score >= threshold:
            return ESCO_SKILLS[best_index], best_score, model_name
    return None, 0.0, "lexical"


def map_to_esco(
    labels: Iterable[str],
    *,
    threshold: float = SEMANTIC_MAPPING_THRESHOLD,
    allow_semantic: bool = True,
) -> list[dict[str, object]]:
    mapped = []
    seen = set()
    for label in dedupe_preserve_order(labels):
        skill = _map_lexically(label)
        score = 1.0 if skill else 0.0
        model = "lexical"
        if skill is None and allow_semantic:
            skill, score, model = _map_semantically(label, threshold=threshold)
        if skill is None:
            continue
        key = normalize_lookup_key(skill.canonical)
        if key in seen:
            continue
        seen.add(key)
        mapped.append(
            {
                "source": label,
                "canonical": skill.canonical,
                "kind": skill.kind,
                "score": round(float(score), 4),
                "model": model,
            }
        )
    return mapped

