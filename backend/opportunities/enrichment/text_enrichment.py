import re
import unicodedata
from typing import Any


SKILLS = [
    "python",
    "java",
    "scala",
    "sql",
    "excel",
    "tcd",
    "power bi",
    "django",
    "react",
    "node",
    "aws",
    "azure",
    "gcp",
    "bigquery",
    "snowflake",
    "redshift",
    "airflow",
    "spark",
    "dbt",
    "etl",
    "elt",
    "docker",
    "sage",
    "sap",
    "linux",
    "windows",
    "kali linux",
    "burp suite",
    "metasploit",
    "wireshark",
    "tcp ip",
    "dns",
    "http",
    "vpn",
    "ceh",
    "oscp",
    "github",
    "jira",
    "confluence",
    "ms project",
    "bpf",
    "controle qualite",
    "contrôle qualité",
    "procedures qualite",
    "procédures qualité",
    "prelevement",
    "prélèvement",
    "etiquetage",
    "étiquetage",
]


_EXPERIENCE_RANGE_RE = re.compile(
    r"(?:entre\s*)?(\d+)\s*(?:ans|years)?\s*(?:à|a|-|et)\s*(\d+)\s*(?:ans|years)\b",
    flags=re.IGNORECASE,
)
_EXPERIENCE_SINGLE_RE = re.compile(r"(\d+)\s*(?:ans|years)\b", flags=re.IGNORECASE)
_EXPERIENCE_LESS_THAN_RE = re.compile(
    r"<\s*(\d+)\s*(?:ans|years)\b",
    flags=re.IGNORECASE,
)
_EXPERIENCE_BEGINNER_RE = re.compile(
    r"debutant\s*(\d+)\s*(?:ans|years)\b",
    flags=re.IGNORECASE,
)
_EXPERIENCE_MORE_THAN_RE = re.compile(
    r"(?:plus(?:\s+que)?\s*|>\s*)(\d+)\s*(?:ans|years)\b",
    flags=re.IGNORECASE,
)
_EXPERIENCE_LESS_THAN_ONE_YEAR_TOKEN = "moins d un an"


_LANGUAGE_PATTERNS = {
    "français": re.compile(r"\bfran(?:c|ç)ais\b", flags=re.IGNORECASE),
    "anglais": re.compile(r"\banglais\b", flags=re.IGNORECASE),
    "arabe": re.compile(r"\barabe\b", flags=re.IGNORECASE),
}


_SOFT_SKILL_KEYWORDS = (
    "communication",
    "esprit d equipe",
    "teamwork",
    "autonomie",
    "autonome",
    "rigueur",
    "adaptabilite",
    "leadership",
    "organisation",
    "gestion du temps",
    "proactif",
    "proactive",
    "motivation",
    "analyse",
    "analytique",
    "problem solving",
    "resolution de problemes",
)


_EXPERIENCE_KEYWORD_TOKEN = "experience"
_EXPERIENCE_PHRASE_TOKEN = "ans d experience"
_EXPERIENCE_IGNORE_PATTERNS = (
    "depuis",
    "creation",
    "fondee",
    "notre entreprise",
    "notre client",
    "a propos de l opportunite",
    "entreprise specialisee",
    "forte de plus de",
)
_MAX_REASONABLE_EXPERIENCE_YEARS = 20


_EXPERIENCE_STRUCTURED_MAP = {
    "aucune experience": (0, 0),
    "moins d un an": (0, 1),
    "entre 1 et 2 ans": (1, 2),
    "entre 2 et 5 ans": (2, 5),
    "entre 5 et 10 ans": (5, 10),
    "plus que 10 ans": (10, None),
}


_SALARY_AMOUNT_TOKEN = r"(?:\d{1,3}(?:[\.\s]\d{3})+|\d{3,5})"
_RANGE_SALARY_RE = re.compile(
    rf"(?:entre\s+)?(?P<low>{_SALARY_AMOUNT_TOKEN})\s*(?:dt|tnd|dinars?)?\s*"
    rf"(?:a|à|-|et|au|to)\s*(?P<high>{_SALARY_AMOUNT_TOKEN})\s*(?:dt|tnd|dinars?)",
    flags=re.IGNORECASE,
)
_SINGLE_SALARY_RE = re.compile(
    rf"(?P<value>{_SALARY_AMOUNT_TOKEN})\s*(?:dt|tnd|dinars?)",
    flags=re.IGNORECASE,
)


def _safe_defaults() -> dict[str, Any]:
    return {
        "salary": None,
        "experience_min": None,
        "experience_max": None,
        "experience_years": None,
        "skills": [],
        "languages_fallback": None,
    }


def _get_value(item: Any, key: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).replace("\xa0", " ")


def _normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", _as_text(value)).strip()


def _normalize_token(value: Any) -> str:
    text = _normalize_text(value).lower()
    if not text:
        return ""

    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _to_optional_int(value: Any) -> int | None:
    try:
        if value is None:
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _merge_unique(items: list[str]) -> list[str]:
    merged: list[str] = []
    seen_tokens: set[str] = set()
    for item in items:
        text = _normalize_text(item)
        if not text:
            continue
        token = _normalize_token(text)
        if token:
            if token in seen_tokens:
                continue
            seen_tokens.add(token)
        elif text in merged:
            continue

        merged.append(text)
    return merged


def _extract_amount_int(value: str) -> int | None:
    digits = re.sub(r"[^0-9]", "", value)
    if not digits:
        return None
    try:
        return int(digits)
    except (TypeError, ValueError):
        return None


def _format_salary_single(amount: int) -> str:
    return f"{amount} TND"


def _format_salary_range(low: int, high: int) -> str:
    normalized_low = min(low, high)
    normalized_high = max(low, high)
    return f"{normalized_low} - {normalized_high} TND"


def _find_salary(text: str) -> str | None:
    normalized = _normalize_text(text)
    if not normalized:
        return None

    match = _RANGE_SALARY_RE.search(normalized)
    if match:
        low = _extract_amount_int(match.group("low"))
        high = _extract_amount_int(match.group("high"))
        if low is not None and high is not None:
            return _format_salary_range(low, high)

    match = _SINGLE_SALARY_RE.search(normalized)
    if match:
        amount = _extract_amount_int(match.group("value"))
        if amount is not None:
            return _format_salary_single(amount)

    return None


def _find_experience_bounds(text: str) -> tuple[int | None, int | None]:
    normalized_text = _normalize_text(text)
    if not normalized_text:
        return None, None

    search_text = normalized_text.lower()
    search_text = unicodedata.normalize("NFKD", search_text)
    search_text = "".join(ch for ch in search_text if not unicodedata.combining(ch))
    search_text = re.sub(r"\s+", " ", search_text).strip()

    token = _normalize_token(normalized_text)
    if not token:
        return None, None

    minimum_candidates: list[int] = []
    maximum_candidates: list[int] = []
    has_open_ended = False
    has_match = False

    if _EXPERIENCE_LESS_THAN_ONE_YEAR_TOKEN in token:
        minimum_candidates.append(0)
        maximum_candidates.append(1)
        has_match = True

    for range_match in _EXPERIENCE_RANGE_RE.finditer(search_text):
        try:
            first = int(range_match.group(1))
            second = int(range_match.group(2))
            minimum_candidates.append(min(first, second))
            maximum_candidates.append(max(first, second))
            has_match = True
        except (TypeError, ValueError):
            continue

    for less_than_match in _EXPERIENCE_LESS_THAN_RE.finditer(search_text):
        try:
            upper = int(less_than_match.group(1))
            minimum_candidates.append(0)
            maximum_candidates.append(upper)
            has_match = True
        except (TypeError, ValueError):
            continue

    for beginner_match in _EXPERIENCE_BEGINNER_RE.finditer(token):
        try:
            upper = int(beginner_match.group(1))
            minimum_candidates.append(0)
            maximum_candidates.append(upper)
            has_match = True
        except (TypeError, ValueError):
            continue

    for more_than_match in _EXPERIENCE_MORE_THAN_RE.finditer(search_text):
        try:
            lower = int(more_than_match.group(1))
            minimum_candidates.append(lower)
            has_open_ended = True
            has_match = True
        except (TypeError, ValueError):
            continue

    if not has_match:
        match = _EXPERIENCE_SINGLE_RE.search(search_text)
        if match:
            try:
                years = int(match.group(1))
                minimum_candidates.append(years)
                maximum_candidates.append(years)
                has_match = True
            except (TypeError, ValueError):
                return None, None

    if not has_match:
        return None, None

    minimum = min(minimum_candidates) if minimum_candidates else None
    if has_open_ended:
        maximum = None
    else:
        maximum = max(maximum_candidates) if maximum_candidates else None

    return _normalize_experience_bounds(minimum, maximum)


def _sanitize_experience_bounds(
    minimum: int | None,
    maximum: int | None,
) -> tuple[int | None, int | None]:
    minimum, maximum = _normalize_experience_bounds(minimum, maximum)

    if minimum is not None and minimum > _MAX_REASONABLE_EXPERIENCE_YEARS:
        return None, None

    if maximum is not None and maximum > _MAX_REASONABLE_EXPERIENCE_YEARS:
        maximum = None

    return minimum, maximum


def _find_skills(text: str) -> list[str]:
    normalized_text = _normalize_token(text)
    if not normalized_text:
        return []

    found: list[str] = []
    for skill in SKILLS:
        normalized_skill = _normalize_token(skill)
        if not normalized_skill:
            continue
        pattern = r"\b" + re.escape(normalized_skill).replace(r"\ ", r"\s+") + r"\b"
        if re.search(pattern, normalized_text):
            found.append(skill)
    return found


def _normalize_structured_skills(value: Any) -> list[str]:
    if isinstance(value, list):
        return _merge_unique([_normalize_text(item) for item in value])

    text = _normalize_text(value)
    if not text:
        return []

    parts = re.split(r"\s*[-,;|/]\s*", text)
    return _merge_unique(parts)


def _find_soft_skills(text: str) -> list[str]:
    raw = _as_text(text)
    if not raw:
        return []

    candidates: list[str] = []
    bullet_pattern = re.compile(r"^\s*(?:[-*•·▪‣–]+|\d+[\.)])\s*")

    for line in re.split(r"[\r\n]+", raw):
        if not line.strip():
            continue

        is_bullet = bullet_pattern.match(line) is not None
        cleaned_line = bullet_pattern.sub("", line, count=1)
        for chunk in re.split(r"\s*[;|]\s*", cleaned_line):
            candidate = _normalize_text(chunk)
            if not candidate:
                continue
            if not (10 <= len(candidate) <= 80):
                continue
            if len(candidate.split()) > 12:
                continue
            if not is_bullet and len(candidate) > 70:
                continue
            candidates.append(candidate)

    soft_skills: list[str] = []
    for candidate in candidates:
        token = _normalize_token(candidate)
        if any(keyword in token for keyword in _SOFT_SKILL_KEYWORDS):
            soft_skills.append(candidate)

    return _merge_unique(soft_skills)


def _map_structured_experience(value: str) -> tuple[int | None, int | None] | None:
    token = _normalize_token(value)
    if not token:
        return None
    return _EXPERIENCE_STRUCTURED_MAP.get(token)


def _normalize_experience_bounds(
    minimum: int | None,
    maximum: int | None,
) -> tuple[int | None, int | None]:
    if minimum is not None and maximum is not None:
        if minimum > maximum:
            return maximum, minimum
        return minimum, maximum

    if minimum is None and maximum is not None:
        return maximum, maximum

    return minimum, maximum


def _has_experience_context(text: str) -> bool:
    token = _normalize_token(text)
    if not token:
        return False
    if _EXPERIENCE_PHRASE_TOKEN in token:
        return True
    return _EXPERIENCE_KEYWORD_TOKEN in token


def _has_ignored_experience_context(text: str) -> bool:
    token = _normalize_token(text)
    if not token:
        return False
    return any(pattern in token for pattern in _EXPERIENCE_IGNORE_PATTERNS)


def _iter_experience_segments(text: str):
    raw = _as_text(text)
    for line in re.split(r"[\r\n]+", raw):
        if not line.strip():
            continue
        for segment in re.split(r"[.;]", line):
            candidate = _normalize_text(segment)
            if candidate:
                yield candidate


def _find_experience_from_description(text: str) -> tuple[int | None, int | None]:
    for segment in _iter_experience_segments(text):
        if not _has_experience_context(segment):
            continue
        if _has_ignored_experience_context(segment):
            continue

        minimum, maximum = _find_experience_bounds(segment)
        if minimum is None and maximum is None:
            continue

        # Guard against company-age style false positives (e.g. "plus de 24 ans d'expérience").
        if minimum is not None and minimum > _MAX_REASONABLE_EXPERIENCE_YEARS:
            continue

        return _normalize_experience_bounds(minimum, maximum)

    return None, None


def _resolve_experience(
    opportunity: Any,
    structured_experience: str,
    description: str,
) -> tuple[int | None, int | None]:
    existing_min = _to_optional_int(_get_value(opportunity, "experience_min"))
    existing_max = _to_optional_int(_get_value(opportunity, "experience_max"))
    if existing_min is not None or existing_max is not None:
        return _sanitize_experience_bounds(existing_min, existing_max)

    if structured_experience:
        mapped = _map_structured_experience(structured_experience)
        if mapped is not None:
            return _sanitize_experience_bounds(*mapped)

        minimum, maximum = _find_experience_bounds(structured_experience)
        return _sanitize_experience_bounds(minimum, maximum)

    minimum, maximum = _find_experience_from_description(description)
    return _sanitize_experience_bounds(minimum, maximum)


def _find_languages_fallback(text: str) -> list[str] | None:
    found: list[str] = []
    for language, pattern in _LANGUAGE_PATTERNS.items():
        if pattern.search(text):
            found.append(language)
    return found or None


def enrich_opportunity_text(opportunity: Any) -> dict[str, Any]:
    """
    Deterministic free-text enrichment.

    Safety guarantees:
    - no exception escapes
    - scalar fields return None when unavailable
    - skills always returns a list
    - structured languages are never overridden
    """

    defaults = _safe_defaults()
    try:
        raw_description = _as_text(_get_value(opportunity, "description"))
        raw_qualifications = _as_text(_get_value(opportunity, "job_qualifications"))
        raw_skill_context = "\n".join(part for part in [raw_description, raw_qualifications] if part)
        description = _normalize_text(raw_description)
        qualifications = _normalize_text(raw_qualifications)
        text_context = _normalize_text("\n".join(part for part in [description, qualifications] if part))
        structured_experience = _normalize_text(_get_value(opportunity, "experience"))
        structured_salary = _normalize_text(_get_value(opportunity, "salary"))
        structured_skills = _get_value(opportunity, "skills")

        if not text_context and not structured_experience and not structured_salary and not structured_skills:
            return defaults

        structured_languages = _get_value(opportunity, "languages")
        has_structured_languages = isinstance(structured_languages, list) and len(structured_languages) > 0

        salary = None
        if structured_salary:
            salary = _find_salary(structured_salary) or structured_salary
        elif text_context:
            salary = _find_salary(text_context)

        experience_min, experience_max = _resolve_experience(
            opportunity=opportunity,
            structured_experience=structured_experience,
            description=raw_description,
        )
        experience_years = experience_min

        normalized_structured_skills = _normalize_structured_skills(structured_skills)
        hard_skills = _find_skills(text_context)
        soft_skills = _find_soft_skills(raw_skill_context)
        skills = _merge_unique([*normalized_structured_skills, *hard_skills, *soft_skills])

        languages_fallback = None if has_structured_languages else _find_languages_fallback(text_context)

        return {
            "salary": salary,
            "experience_min": experience_min,
            "experience_max": experience_max,
            "experience_years": experience_years,
            "skills": skills,
            "languages_fallback": languages_fallback,
        }
    except Exception:
        return defaults
