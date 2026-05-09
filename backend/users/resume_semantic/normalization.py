from __future__ import annotations

import re
import unicodedata
from typing import Iterable


WHITESPACE_RE = re.compile(r"\s+")
TOKEN_BOUNDARY_RE = re.compile(r"(?<!\w){}(?!\w)", re.IGNORECASE | re.UNICODE)
CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")
PUNCTUATION_RE = re.compile(r"[^\w\s+#./-]+", re.UNICODE)


SYNONYM_TO_CANONICAL = {
    ".net": ".net",
    "airflow": "apache airflow",
    "amazon web services": "aws",
    "api rest": "rest api",
    "aws": "aws",
    "azure": "azure",
    "celery": "celery",
    "ci cd": "devops",
    "ci/cd": "devops",
    "ci/cd pipelines": "devops",
    "ci-cd": "devops",
    "cicd": "devops",
    "css": "css",
    "django": "django",
    "django rest": "django",
    "django rest framework": "django",
    "docker": "docker",
    "fastapi": "fastapi",
    "git": "git",
    "github actions": "github actions",
    "gitlab ci": "gitlab ci",
    "java": "java",
    "javascript": "javascript",
    "js": "javascript",
    "k8s": "kubernetes",
    "kubernetes": "kubernetes",
    "machine learning": "machine learning",
    "ml": "machine learning",
    "mongodb": "mongodb",
    "nlp": "natural language processing",
    "node": "node.js",
    "nodejs": "node.js",
    "node.js": "node.js",
    "postgres": "postgresql",
    "postgresql": "postgresql",
    "pytorch": "machine learning",
    "python": "python",
    "react": "react",
    "react.js": "react",
    "redis": "redis",
    "rest api": "rest api",
    "scikit learn": "machine learning",
    "scikit-learn": "machine learning",
    "siem": "cybersecurity",
    "spark": "apache spark",
    "sql": "sql",
    "terraform": "terraform",
    "typescript": "typescript",
    "ts": "typescript",
    "تطوير الويب": "web development",
    "تعلم الآلة": "machine learning",
    "ذكاء اصطناعي": "machine learning",
    "واجهات api": "rest api",
    "واجهات برمجة التطبيقات": "rest api",
    "بايثون": "python",
    "جافاسكريبت": "javascript",
    "محاسبة": "accounting",
    "موارد بشرية": "human resources",
    "تمريض": "nursing",
    "développement web": "web development",
    "developpement web": "web development",
    "intelligence artificielle": "machine learning",
    "apprentissage automatique": "machine learning",
    "comptabilité": "accounting",
    "comptabilite": "accounting",
    "ressources humaines": "human resources",
    "soins infirmiers": "nursing",
}


NOISY_CANDIDATES = {
    "api",
    "apis",
    "backend",
    "developer",
    "development",
    "engineer",
    "engineering",
    "frontend",
    "full stack",
    "mission",
    "platform",
    "profile",
    "project",
    "software",
    "web",
}


def clean_resume_semantic_text(value: str | None, *, max_chars: int = 12000) -> str:
    text = CONTROL_RE.sub(" ", str(value or ""))
    text = unicodedata.normalize("NFKC", text)
    text = WHITESPACE_RE.sub(" ", text).strip()
    if len(text) > max_chars:
        text = text[:max_chars].rstrip()
    return text


def normalize_lookup_key(value: str | None) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).casefold()
    text = PUNCTUATION_RE.sub(" ", text.replace("&", " and "))
    text = WHITESPACE_RE.sub(" ", text).strip()
    return text


def normalize_skill_label(value: str | None) -> str:
    key = normalize_lookup_key(value)
    if not key or key in NOISY_CANDIDATES:
        return ""
    return SYNONYM_TO_CANONICAL.get(key, key)


def dedupe_preserve_order(values: Iterable[str]) -> list[str]:
    output = []
    seen = set()
    for value in values:
        label = normalize_skill_label(value)
        if not label:
            continue
        key = normalize_lookup_key(label)
        if key in seen:
            continue
        seen.add(key)
        output.append(label)
    return output


def contains_phrase(text: str, phrase: str) -> bool:
    normalized_text = normalize_lookup_key(text)
    normalized_phrase = normalize_lookup_key(phrase)
    if not normalized_phrase:
        return False
    pattern = TOKEN_BOUNDARY_RE.pattern.format(re.escape(normalized_phrase))
    return bool(re.search(pattern, normalized_text, flags=re.IGNORECASE | re.UNICODE))


def detect_languages(text: str) -> list[str]:
    value = str(text or "")
    languages = []
    if re.search(r"[\u0600-\u06ff]", value):
        languages.append("ar")
    latin = value.casefold()
    french_markers = (
        "développeur",
        "developpeur",
        "compétence",
        "competence",
        "expérience",
        "experience",
        "ingénieur",
        "ingenieur",
        "comptabilité",
        "comptabilite",
        "ressources humaines",
    )
    english_markers = (
        "engineer",
        "developer",
        "experience",
        "skills",
        "backend",
        "frontend",
        "data",
        "cloud",
    )
    if any(marker in latin for marker in french_markers):
        languages.append("fr")
    if any(marker in latin for marker in english_markers):
        languages.append("en")
    if not languages and re.search(r"[a-zA-Z]", value):
        languages.append("en")
    return languages or ["und"]
