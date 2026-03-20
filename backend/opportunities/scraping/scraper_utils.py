import os
import re


def get_env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def get_env_int(name, default):
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


FETCH_DETAILS = get_env_bool("FETCH_DETAILS", False)
MAX_DESCRIPTION_LENGTH = get_env_int("MAX_DESCRIPTION_LENGTH", 400)
SCRAPER_TIMEOUT_DEFAULT = get_env_int("SCRAPER_TIMEOUT", 10)

_WHITESPACE_RE = re.compile(r"\s+")


def clean_description_for_ml(text):
    cleaned = "" if text is None else str(text).strip()
    if not cleaned:
        return "", ""

    raw_description = cleaned
    boilerplate_patterns = [
        r"\bhaicop\b",
        r"\brepublique tunisienne\b",
        r"\bpresidence du gouvernement\b",
    ]
    for pattern in boilerplate_patterns:
        cleaned = re.sub(pattern, " ", cleaned, flags=re.IGNORECASE)

    cleaned = _WHITESPACE_RE.sub(" ", cleaned).strip()
    if len(cleaned) > MAX_DESCRIPTION_LENGTH:
        return cleaned[:MAX_DESCRIPTION_LENGTH].strip(), raw_description
    return cleaned, ""


def clean_location_for_ml(text):
    location = "" if text is None else str(text).strip().lower()
    if not location:
        return ""
    if "www" in location or ".tn" in location:
        return ""
    if len(location) < 3:
        return ""
    location = _WHITESPACE_RE.sub(" ", location).strip()
    return location.title()
