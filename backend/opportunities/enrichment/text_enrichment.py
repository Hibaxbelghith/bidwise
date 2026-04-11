import re
from typing import Any


SKILLS = [
    "python",
    "java",
    "sql",
    "excel",
    "power bi",
    "django",
    "react",
    "node",
    "aws",
    "docker",
    "sage",
    "sap",
    "linux",
]


_RANGE_SALARY_RE = re.compile(r"\d{3,4}\s*(?:à|-)\s*\d{3,4}\s*(?:DT|TND)", flags=re.IGNORECASE)
_SINGLE_SALARY_RE = re.compile(r"\d{3,4}\s*(?:DT|TND)", flags=re.IGNORECASE)
_EXPERIENCE_RANGE_RE = re.compile(
    r"(?:entre\s*)?(\d+)\s*(?:à|a|-|et)\s*(\d+)\s*(?:ans|years)\b",
    flags=re.IGNORECASE,
)
_EXPERIENCE_SINGLE_RE = re.compile(r"(\d+)\s*(?:ans|years)\b", flags=re.IGNORECASE)


_LANGUAGE_PATTERNS = {
    "français": re.compile(r"\bfran(?:c|ç)ais\b", flags=re.IGNORECASE),
    "anglais": re.compile(r"\banglais\b", flags=re.IGNORECASE),
    "arabe": re.compile(r"\barabe\b", flags=re.IGNORECASE),
}


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


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).replace("\xa0", " ")).strip()


def _find_salary(text: str) -> str | None:
    match = _RANGE_SALARY_RE.search(text)
    if match:
        return _normalize_text(match.group(0))

    match = _SINGLE_SALARY_RE.search(text)
    if match:
        return _normalize_text(match.group(0))

    return None


def _find_experience_bounds(text: str) -> tuple[int | None, int | None]:
    range_match = _EXPERIENCE_RANGE_RE.search(text)
    if range_match:
        try:
            first = int(range_match.group(1))
            second = int(range_match.group(2))
            return min(first, second), max(first, second)
        except (TypeError, ValueError):
            pass

    match = _EXPERIENCE_SINGLE_RE.search(text)
    if not match:
        return None, None

    try:
        years = int(match.group(1))
        return years, years
    except (TypeError, ValueError):
        return None, None


def _find_skills(text: str) -> list[str]:
    found: list[str] = []
    for skill in SKILLS:
        pattern = r"\b" + re.escape(skill).replace(r"\ ", r"\s+") + r"\b"
        if re.search(pattern, text, flags=re.IGNORECASE):
            found.append(skill)
    return found


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
        description = _normalize_text(_get_value(opportunity, "description"))
        structured_experience = _normalize_text(_get_value(opportunity, "experience"))
        structured_salary = _normalize_text(_get_value(opportunity, "salary"))

        if not description and not structured_experience and not structured_salary:
            return defaults

        structured_languages = _get_value(opportunity, "languages")
        has_structured_languages = isinstance(structured_languages, list) and len(structured_languages) > 0

        salary = _find_salary(structured_salary) if structured_salary else None
        if salary is None and structured_salary:
            salary = structured_salary
        if salary is None:
            salary = _find_salary(description)

        experience_min, experience_max = _find_experience_bounds(
            f"{structured_experience} {description}".strip()
        )
        experience_years = experience_min
        skills = _find_skills(description)
        languages_fallback = None if has_structured_languages else _find_languages_fallback(description)

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
