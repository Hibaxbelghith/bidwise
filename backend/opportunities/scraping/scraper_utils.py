import os
import re
import unicodedata
from urllib.parse import urlparse


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

_ORG_PLACEHOLDERS = {
    "unknown",
    "n a",
    "na",
    "none",
    "tunisie",
    "tun",
    "international",
    "dza",
    "mar",
    "nat",
    "rep",
    "non renseigne",
}

_ORG_ACRONYM_PREFIX_BLACKLIST = {
    "BTP",
    "TND",
    "EUR",
    "USD",
    "HT",
    "TTC",
    "AO",
    "TR",
    "AC",
    "CA",
    "ME",
    "SE",
    "AM",
    "INF",
}

_ORG_TEXT_PATTERNS = (
    r"\b(?:ministere|minist[eè]re)\s+(?:de|du|des|d')\s+[A-Za-zÀ-ÖØ-öø-ÿ'’\-\s]{3,80}",
    r"\b(?:gouvernorat|commissariat|municipalite|municipalit[eé]|universite|universit[eé])\s+(?:de|du|des|d')\s+[A-Za-zÀ-ÖØ-öø-ÿ'’\-\s]{2,80}",
    r"\b(?:tribunal|hopital|h[oô]pital|clinique|ecole|[eé]cole|office)\s+[A-Za-zÀ-ÖØ-öø-ÿ'’\-\s]{2,80}",
    r"\b(?:societe|soci[eé]t[eé]|entreprise)\s+[A-Za-zÀ-ÖØ-öø-ÿ'’\-\s]{2,80}",
)

# Canonical city names used for UX and recommendation filtering.
_CITY_ALIASES = [
    ("ben arous", "Ben Arous"),
    ("sidi bouzid", "Sidi Bouzid"),
    ("kef", "Kef"),
    ("kasserine", "Kasserine"),
    ("kairouan", "Kairouan"),
    ("jendouba", "Jendouba"),
    ("tataouine", "Tataouine"),
    ("medenine", "Medenine"),
    ("medenine", "Medenine"),
    ("monastir", "Monastir"),
    ("mahdia", "Mahdia"),
    ("gafsa", "Gafsa"),
    ("gabes", "Gabes"),
    ("gabes", "Gabes"),
    ("bizerte", "Bizerte"),
    ("beja", "Beja"),
    ("beja", "Beja"),
    ("ariana", "Ariana"),
    ("nabeul", "Nabeul"),
    ("zaghouan", "Zaghouan"),
    ("sousse", "Sousse"),
    ("sfax", "Sfax"),
    ("tozeur", "Tozeur"),
    ("kebili", "Kebili"),
    ("manouba", "Manouba"),
    ("siliana", "Siliana"),
    ("tunis", "Tunis"),
    ("mateur", "Mateur"),
    ("marrakech", "Marrakech"),
    ("casablanca", "Casablanca"),
    ("rabat", "Rabat"),
    ("tanger", "Tanger"),
    ("fes", "Fes"),
    ("agadir", "Agadir"),
    ("paris", "Paris"),
    ("lyon", "Lyon"),
    ("marseille", "Marseille"),
    ("montreal", "Montreal"),
]
_CITY_ALIASES = sorted(_CITY_ALIASES, key=lambda item: len(item[0]), reverse=True)

_CITY_CODE_TO_CANONICAL = {
    "tun": "Tunis",
    "tn": "Tunis",
    "tuneps": "Tunis",
}

_NON_CITY_LOCATION_TOKENS = {
    "dza",
    "mar",
    "international",
    "inter",
    "nat",
    "rep",
    "tunisie",
    "maroc",
    "morocco",
}

_REMOTE_LOCATION_TOKENS = {
    "a distance",
    "distance",
    "remote",
    "teletravail",
    "en ligne",
    "full remote",
    "100 en ligne",
}

# Arabic aliases are represented with unicode escapes to keep this file ASCII.
_ARABIC_CITY_ALIASES = [
    ("\u0628\u0646\u0632\u0631\u062a", "Bizerte"),
    ("\u062a\u0648\u0646\u0633", "Tunis"),
    ("\u0635\u0641\u0627\u0642\u0633", "Sfax"),
    ("\u0633\u0648\u0633\u0629", "Sousse"),
    ("\u0642\u0627\u0628\u0633", "Gabes"),
    ("\u0642\u0641\u0635\u0629", "Gafsa"),
    ("\u0627\u0644\u0645\u0647\u062f\u064a\u0629", "Mahdia"),
    ("\u0627\u0644\u0642\u064a\u0631\u0648\u0627\u0646", "Kairouan"),
    ("\u0627\u0644\u0643\u0627\u0641", "Kef"),
    ("\u0628\u0627\u062c\u0629", "Beja"),
    ("\u062c\u0646\u062f\u0648\u0628\u0629", "Jendouba"),
    ("\u0645\u062f\u0646\u064a\u0646", "Medenine"),
    ("\u062a\u0637\u0627\u0648\u064a\u0646", "Tataouine"),
    ("\u0646\u0627\u0628\u0644", "Nabeul"),
    ("\u0645\u0646\u0648\u0628\u0629", "Manouba"),
    ("\u0628\u0646 \u0639\u0631\u0648\u0633", "Ben Arous"),
]

_GENERIC_LISTING_PATHS = {
    "",
    "/",
    "/offres-emploi",
    "/offres-emploi/",
    "/internships",
    "/internships/",
    "/appels-offres",
    "/appels-doffres",
    "/recherche-jobs-tunisie",
    "/recherche-jobs-tunisie/stage",
}
_GENERIC_LISTING_SEGMENTS = (
    "/tag/",
    "/category/",
    "/search",
    "/recherche",
    "/page/",
)

_STAGE_KEYWORDS_RE = re.compile(
    r"\b(stage|stagiaire|internship|intern|alternance|apprentissage|pfe|fin d etudes|fin d etude|stage ete|trainee)\b",
    flags=re.IGNORECASE,
)

_CLOSED_KEYWORDS = {
    "cloture",
    "cloturee",
    "concours cloture",
    "appel cloture",
    "termine",
    "terminee",
    "expired",
    "close",
    "closed",
}


def _normalize_for_match(value):
    cleaned = "" if value is None else str(value)
    cleaned = unicodedata.normalize("NFKD", cleaned)
    cleaned = "".join(ch for ch in cleaned if not unicodedata.combining(ch))
    cleaned = cleaned.lower()
    cleaned = re.sub(r"[^a-z0-9\s]", " ", cleaned)
    return _WHITESPACE_RE.sub(" ", cleaned).strip()


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
    return cleaned, raw_description


def clean_location_for_ml(text):
    location_raw = "" if text is None else str(text).strip()
    if not location_raw:
        return ""
    location = location_raw.lower()
    if "www" in location or ".tn" in location:
        return ""

    normalized = _normalize_for_match(location_raw)
    if not normalized:
        return ""

    mapped = _CITY_CODE_TO_CANONICAL.get(normalized)
    if mapped:
        return mapped

    if normalized in _NON_CITY_LOCATION_TOKENS:
        return ""

    inferred = infer_city_from_text(location_raw)
    if inferred:
        return inferred

    if len(normalized) < 3:
        return ""
    cleaned = _WHITESPACE_RE.sub(" ", location_raw).strip()
    return cleaned.title()


def normalize_organization_name(text):
    org = "" if text is None else str(text).strip()
    if not org:
        return ""

    # Remove obvious timestamp/date noise appended by some sources.
    org = re.sub(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b.*$", "", org).strip(" -|:;,.")
    org = re.sub(r"\b\d{2}:\d{2}(?::\d{2})?\b.*$", "", org).strip(" -|:;,.")
    if not org:
        return ""

    normalized = _normalize_for_match(org)
    if not normalized or normalized in _ORG_PLACEHOLDERS:
        return ""
    if re.fullmatch(r"[A-Z]{2,4}", org):
        return org.strip()
    if len(normalized) < 2:
        return org.strip()
    if len(normalized) < 3:
        return ""
    return org


def infer_organization_from_title(title):
    cleaned = "" if title is None else str(title).strip()
    if not cleaned:
        return ""

    patterns = (
        r"^(.{3,120}?)\s+recrute\b",
        r"^(.{3,120}?)\s+(?:is looking for|hiring|embauche)\b",
    )
    for pattern in patterns:
        match = re.match(pattern, cleaned, flags=re.IGNORECASE)
        if match:
            return normalize_organization_name(match.group(1))

    normalized = _normalize_for_match(cleaned)
    concours_match = re.search(
        r"\bconcours\s+(.{3,120}?)\s+pour\s+le\s+recrutement\b",
        normalized,
        flags=re.IGNORECASE,
    )
    if concours_match:
        candidate = concours_match.group(1).strip(" -_:;,. ")
        return normalize_organization_name(candidate.title())

    return ""


def infer_organization_from_text(*texts):
    candidates = [str(text).strip() for text in texts if text]
    if not candidates:
        return ""

    for text in candidates:
        acronym_match = re.match(r"\s*\d{1,2}\s*/\s*/?([A-Z]{3,10})\b", text)
        if acronym_match:
            acronym = acronym_match.group(1).strip()
            if acronym not in _ORG_ACRONYM_PREFIX_BLACKLIST:
                return normalize_organization_name(acronym) or acronym

    raw_blob = _WHITESPACE_RE.sub(" ", " ".join(candidates)).strip()
    if not raw_blob:
        return ""

    for pattern in _ORG_TEXT_PATTERNS:
        match = re.search(pattern, raw_blob, flags=re.IGNORECASE)
        if not match:
            continue
        phrase = _WHITESPACE_RE.sub(" ", match.group(0)).strip(" -_:;,.")
        normalized = normalize_organization_name(phrase)
        if normalized:
            return normalized

    return ""


def infer_city_from_text(*texts):
    candidates = [str(text) for text in texts if text]
    if not candidates:
        return ""

    raw_blob = " ".join(candidates).lower()
    for alias, canonical in _ARABIC_CITY_ALIASES:
        if alias in raw_blob:
            return canonical

    normalized_blob = _normalize_for_match(" ".join(candidates))

    if any(token in normalized_blob for token in _REMOTE_LOCATION_TOKENS):
        return "Remote"

    for alias, canonical in _CITY_ALIASES:
        if re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", normalized_blob):
            return canonical

    # Handle patterns like "region de bizerte" and "a tunis".
    location_match = re.search(
        r"\b(?:region de|gouvernorat de|a|de|en|sur)\s+([a-z][a-z\-\s]{2,40})",
        normalized_blob,
    )
    if location_match:
        candidate = location_match.group(1).strip()
        for alias, canonical in _CITY_ALIASES:
            if candidate.startswith(alias):
                return canonical

    return ""


def classify_source_item_url(url):
    value = "" if url is None else str(url).strip()
    if not value:
        return "missing"

    try:
        parsed = urlparse(value)
    except Exception:
        return "invalid"

    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return "invalid"

    path = (parsed.path or "").strip().lower()
    if path in _GENERIC_LISTING_PATHS:
        return "generic_listing"
    if any(segment in path for segment in _GENERIC_LISTING_SEGMENTS):
        return "generic_listing"

    return "detail_like"


def infer_opportunity_type(*texts, default="EMPLOI"):
    candidates = [str(text) for text in texts if text]
    if not candidates:
        return default

    normalized_blob = _normalize_for_match(" ".join(candidates))
    if _STAGE_KEYWORDS_RE.search(normalized_blob):
        return "STAGE"
    return default


def looks_closed_opportunity(*texts):
    candidates = [str(text) for text in texts if text]
    if not candidates:
        return False

    normalized_blob = _normalize_for_match(" ".join(candidates))
    if not normalized_blob:
        return False

    return any(token in normalized_blob for token in _CLOSED_KEYWORDS)
