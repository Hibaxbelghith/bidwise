import hashlib
import json
import logging
import random
import re
import time
import unicodedata
from datetime import date, timedelta
from html import escape
from urllib.parse import urlencode, urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..scraper_base import BaseOpportunityScraper
from ..scraper_utils import SCRAPER_TIMEOUT_DEFAULT, clean_description_for_ml, infer_opportunity_type


logger = logging.getLogger(__name__)


LINKEDIN_PUBLIC_SEARCH_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
LINKEDIN_SEARCH_PAGE_URL = "https://www.linkedin.com/jobs/search"
LINKEDIN_SOURCE_URL = "https://www.linkedin.com/jobs/search"
DEFAULT_KEYWORD = ""
DEFAULT_LOCATION = "Tunisia"
DEFAULT_MAX_PAGES = 10
PAGE_SIZE = 25
MAX_OFFSET = 1000
MAX_PAGES_SAFE = max(1, MAX_OFFSET // PAGE_SIZE)
DEFAULT_TIMEOUT = SCRAPER_TIMEOUT_DEFAULT
DEFAULT_MIN_DELAY = 2.0
DEFAULT_MAX_DELAY = 3.0
DEFAULT_MAX_RETRIES = 3
SOURCE_RELIABILITY = "LOW"
SOURCE_RELIABILITY_REASON = "Unofficial public LinkedIn guest endpoint"
DESCRIPTION_QUALITY_SNIPPET = "EXTRACTED_LISTING_SNIPPET"
DESCRIPTION_QUALITY_METADATA = "ENRICHED_LISTING_METADATA"
DESCRIPTION_QUALITY_DETAIL = "EXTRACTED_DETAIL_DESCRIPTION"

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,fr;q=0.8",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Connection": "keep-alive",
}

WHITESPACE_RE = re.compile(r"\s+")
JOB_ID_RE = re.compile(r"/jobs/view/(\d+)")
TRACKING_QUERY_KEYS = {"trk", "refId", "trackingId", "position", "pageNum"}
DETAIL_NOISE_TEXT = {
    "show more",
    "show less",
    "see more",
    "voir plus",
    "voir moins",
    "... plus",
    "… plus",
}
TITLE_FORBIDDEN_TOKENS = {
    "candidatures",
    "candidature",
    "applicants",
    "promoted",
    "promue",
    "premium",
    "aucune info",
}
DESCRIPTION_STOP_PATTERNS = (
    "nom et prénom",
    "adresse email",
    "mobile",
    "niveau d étude",
    "niveau d'etude",
    "niveau d'étude",
    "années d’expérience",
    "annees d experience",
    "préavis",
    "preavis",
    "upload cv",
    "téléverser votre cv",
    "televerser votre cv",
    "consentement à la conservation des données",
    "consentement a la conservation des donnees",
    "comment postuler",
)
DESCRIPTION_NOISE_PATTERNS = (
    "learn more about us",
    "apply directly",
    "only shortlisted candidates",
    "premium",
    "sign in",
)
DESCRIPTION_SPAM_TOKENS = (
    "recruitment",
    "consulting",
    "management",
    "training",
    "sourcing",
    "jobs offer",
    "internship",
    "morocco",
    "africa",
    "d'abord",
    "tout d'abord",
    "en premier lieu",
    "par ailleurs",
    "en dernier lieu",
)
PREMIUM_TEXT_TOKENS = (
    "premium",
    "essayer premium",
    "premium_job_details",
    "upsell",
)
RELATIVE_TIME_RE = re.compile(
    r"(?:il\s+y\s+a\s*)?(\d+)\s*"
    r"(minute|minutes|heure|heures|hour|hours|jour|jours|day|days|"
    r"semaine|semaines|week|weeks|mois|month|months|an|ans|year|years)"
    r"(?:\s+ago)?",
    re.IGNORECASE,
)
LOCATION_HINT_RE = re.compile(
    r"\b("
    r"tunisie|tunisia|tunis|sousse|sfax|nabeul|ben\s+arous|bizerte|beja|béja|"
    r"zaghouan|gafsa|tozeur|sidi\s+bouzid|gouvernorat|metropolitan\s+area|"
    r"remote|hybride|hybrid|on-site|onsite"
    r")\b",
    re.IGNORECASE,
)
CONTRACT_TYPE_PATTERNS = (
    ("CDI", re.compile(r"\bcdi\b", re.IGNORECASE)),
    ("CDD", re.compile(r"\bcdd\b", re.IGNORECASE)),
    ("Freelance", re.compile(r"\bfreelance\b", re.IGNORECASE)),
    ("Contract", re.compile(r"\bcontract\b|\bcontrat\b", re.IGNORECASE)),
    ("Internship", re.compile(r"\binternship\b", re.IGNORECASE)),
    ("Stage", re.compile(r"\bstage\b", re.IGNORECASE)),
    ("Volunteer", re.compile(r"\bvolunteer\b|\bbenevolat\b|\bbenevolat\b", re.IGNORECASE)),
    ("Alternance", re.compile(r"\balternance\b", re.IGNORECASE)),
    ("SIVP", re.compile(r"\bsivp\b", re.IGNORECASE)),
)
AVAILABILITY_PATTERNS = (
    ("Temps plein", re.compile(r"\btemps\s+plein\b|\bplein\s+temps\b|\bfull[\s-]?time\b", re.IGNORECASE)),
    ("Temps partiel", re.compile(r"\btemps\s+partiel\b|\bpart[\s-]?time\b", re.IGNORECASE)),
    ("Présentiel", re.compile(r"\bpresentiel\b|\bon[\s-]?site\b|\bonsite\b", re.IGNORECASE)),
    ("Hybride", re.compile(r"\bhybride\b|\bhybrid\b", re.IGNORECASE)),
    ("À distance", re.compile(r"\bremote\b|\ba\s+distance\b|\bhome\s+office\b", re.IGNORECASE)),
)
AVAILABILITY_CANONICAL_MAP = {
    "full time": "Temps plein",
    "part time": "Temps partiel",
}
JOB_QUALIFICATIONS_SECTION_HINTS = (
    "profil recherche",
    "profil recherché",
    "exigences",
    "competences",
    "compétences",
    "competences techniques",
    "compétences techniques",
    "qualifications",
    "requirements",
)
EDUCATION_SECTION_HINTS = (
    "niveau academique",
    "niveau académique",
    "formation",
    "education",
    "education level",
)
SECTION_BREAK_HINTS = JOB_QUALIFICATIONS_SECTION_HINTS + EDUCATION_SECTION_HINTS + (
    "responsabilites",
    "responsabilités",
    "missions",
    "pourquoi nous rejoindre",
    "why join",
    "comment postuler",
    "how to apply",
)
DEGREE_PATTERNS = (
    ("Bac+5", re.compile(r"\bbac\s*\+\s*5\b", re.IGNORECASE)),
    ("Bac+4", re.compile(r"\bbac\s*\+\s*4\b", re.IGNORECASE)),
    ("Bac+3", re.compile(r"\bbac\s*\+\s*3\b", re.IGNORECASE)),
    ("Master / Ingénieur", re.compile(r"\bmaster\b|\bing[eé]nieur\b", re.IGNORECASE)),
    ("Licence", re.compile(r"\blicence\b|\bbachelor\b", re.IGNORECASE)),
    ("BTS / Technicien supérieur", re.compile(r"\bbts\b|\btechnicien\s+sup[eé]rieur\b|\bdut\b", re.IGNORECASE)),
)
SKILL_STOPWORDS_RAW = {
    "a",
    "about",
    "after",
    "an",
    "and",
    "are",
    "as",
    "at",
    "au",
    "aux",
    "avec",
    "by",
    "ce",
    "ces",
    "cette",
    "comme",
    "dans",
    "de",
    "des",
    "du",
    "en",
    "et",
    "for",
    "from",
    "in",
    "into",
    "is",
    "la",
    "le",
    "les",
    "of",
    "on",
    "or",
    "our",
    "par",
    "pour",
    "sur",
    "the",
    "their",
    "this",
    "to",
    "un",
    "une",
    "with",
    "without",
    "your",
}
SKILL_CONNECTOR_TOKENS_RAW = {"and", "de", "des", "du", "en", "et", "for", "of", "sur", "to", "with"}
SKILL_NOISE_TERMS_RAW = {
    "ability",
    "activite",
    "activites",
    "avance",
    "avancee",
    "candidate",
    "candidat",
    "competence",
    "competences",
    "company",
    "department",
    "emploi",
    "environnement",
    "environnements",
    "entreprise",
    "equipe",
    "experience",
    "experiences",
    "expertise",
    "fonction",
    "fonctions",
    "framework",
    "frameworks",
    "job",
    "knowledge",
    "langage",
    "maitrise",
    "mission",
    "missions",
    "outil",
    "outils",
    "position",
    "poste",
    "programmation",
    "process",
    "profile",
    "profil",
    "qualite",
    "responsabilite",
    "responsabilites",
    "role",
    "skill",
    "skills",
    "solide",
    "task",
    "tasks",
    "team",
    "traitement",
    "travail",
    "work",
}
SKILL_VERB_BLACKLIST_RAW = {
    "accompagner",
    "animer",
    "assurer",
    "build",
    "collaborer",
    "concevoir",
    "coordinate",
    "coordonner",
    "create",
    "deliver",
    "develop",
    "developper",
    "design",
    "drive",
    "ensure",
    "executer",
    "gerer",
    "implement",
    "implementer",
    "lead",
    "maintain",
    "mettre",
    "oversee",
    "piloter",
    "realiser",
    "support",
    "supporter",
    "suivre",
    "travailler",
}
SKILL_DOMAIN_SIGNALS_RAW = {
    "finance": {
        "analysis",
        "analyse",
        "audit",
        "budget",
        "budgeting",
        "cash",
        "controlling",
        "finance",
        "financial",
        "forecast",
        "forecasting",
        "pnl",
        "reporting",
        "tresorerie",
        "treasury",
    },
    "data": {
        "airflow",
        "analytics",
        "aws",
        "azure",
        "bigquery",
        "data",
        "database",
        "dbt",
        "donnees",
        "elt",
        "etl",
        "gcp",
        "pipeline",
        "python",
        "redshift",
        "scala",
        "snowflake",
        "spark",
        "sql",
        "warehouse",
    },
    "engineering": {
        "api",
        "architecture",
        "backend",
        "cloud",
        "devops",
        "infrastructure",
        "integration",
        "platform",
        "system",
        "systems",
    },
    "hr": {
        "administration",
        "administrative",
        "employee",
        "human",
        "payroll",
        "recruitment",
        "resources",
        "talent",
    },
    "project": {
        "coordination",
        "delivery",
        "planning",
        "project",
        "projet",
        "stakeholder",
    },
    "quality": {
        "bpf",
        "compliance",
        "controle",
        "echantillon",
        "etiquetage",
        "hygiene",
        "laboratoire",
        "prelevement",
        "quality",
    },
}
SKILL_SHORT_TOKENS_RAW = {"api", "aws", "bpf", "crm", "dbt", "elt", "erp", "etl", "gcp", "sap", "sdk", "sql"}
SKILL_ALLOWED_NOUN_TOKENS_RAW = {
    "analysis",
    "architecture",
    "control",
    "engineering",
    "management",
    "pipeline",
    "reporting",
    "resources",
}
SKILL_SINGLETON_GENERIC_TOKENS_RAW = {
    "cloud",
    "data",
    "donnees",
    "engineering",
    "finance",
    "financial",
    "project",
    "projet",
    "system",
    "systems",
}
SKILL_SEGMENT_SPLIT_RE = re.compile(r"[\n\r;,:()\[\]/.!?]|(?:\s[-–]\s)")
SKILL_CUE_RE = re.compile(
    r"\b("
    r"competence|competences|connaissance|connaissances|experience|expertise|"
    r"framework|frameworks|knowledge|maitrise|maitriser|outil|outils|"
    r"proficiency|skill|skills|stack|tool|tools"
    r")\b"
)
SKILL_SOURCE_REPLACEMENTS = (
    (re.compile(r"\bp\s*&\s*l\b", re.IGNORECASE), " pnl "),
    (re.compile(r"\bprofit\s+and\s+loss\b", re.IGNORECASE), " pnl "),
)
SKILL_NORMALIZATION_RULES_RAW = (
    (r"\b(analyse financiere|financial analysis|pnl)\b", "financial analysis"),
    (r"\b(financial reporting|reporting financier|reporting finance|reporting)\b", "reporting"),
    (r"\b(cash management|cash flow management|gestion de tresorerie|tresorerie)\b", "cash management"),
    (r"\b(data pipelines|data pipeline|pipeline de donnees|pipelines de donnees)\b", "data pipeline"),
    (r"\b(prelevement|prelevement echantillon|prelevement echantillons)\b", "prelevement"),
    (r"\b(project management|gestion de projet)\b", "project management"),
    (r"\b(quality control|controle qualite)\b", "quality control"),
)
SKILL_MAX_RESULTS = 10


def _clean_text(value):
    if value is None:
        return ""
    return WHITESPACE_RE.sub(" ", str(value)).strip()


def _clean_multiline_text(value):
    if value is None:
        return ""

    lines = []
    seen = set()
    for raw_line in str(value).splitlines():
        line = _clean_text(raw_line)
        if not line:
            continue
        normalized = line.lower()
        if normalized in DETAIL_NOISE_TEXT or normalized in seen:
            continue
        seen.add(normalized)
        lines.append(line)
    return "\n".join(lines).strip()


def _normalize_search_text(value):
    text = _clean_text(value).lower()
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return WHITESPACE_RE.sub(" ", text).strip()


SKILL_STOPWORDS = {_normalize_search_text(item) for item in SKILL_STOPWORDS_RAW if _normalize_search_text(item)}
SKILL_CONNECTOR_TOKENS = {
    _normalize_search_text(item) for item in SKILL_CONNECTOR_TOKENS_RAW if _normalize_search_text(item)
}
SKILL_NOISE_TERMS = {_normalize_search_text(item) for item in SKILL_NOISE_TERMS_RAW if _normalize_search_text(item)}
SKILL_VERB_BLACKLIST = {
    _normalize_search_text(item) for item in SKILL_VERB_BLACKLIST_RAW if _normalize_search_text(item)
}
SKILL_DOMAIN_SIGNALS = {
    domain: {_normalize_search_text(item) for item in values if _normalize_search_text(item)}
    for domain, values in SKILL_DOMAIN_SIGNALS_RAW.items()
}
SKILL_SIGNAL_VOCAB = set().union(*SKILL_DOMAIN_SIGNALS.values())
SKILL_SHORT_TOKENS = {_normalize_search_text(item) for item in SKILL_SHORT_TOKENS_RAW if _normalize_search_text(item)}
SKILL_ALLOWED_NOUN_TOKENS = {
    _normalize_search_text(item) for item in SKILL_ALLOWED_NOUN_TOKENS_RAW if _normalize_search_text(item)
}
SKILL_SINGLETON_GENERIC_TOKENS = {
    _normalize_search_text(item) for item in SKILL_SINGLETON_GENERIC_TOKENS_RAW if _normalize_search_text(item)
}
SKILL_NORMALIZATION_RULES = [
    (re.compile(pattern), canonical)
    for pattern, canonical in SKILL_NORMALIZATION_RULES_RAW
]


def _normalize_fingerprint_text(value):
    return _normalize_search_text(value)


def _nullable(value):
    text = _clean_text(value)
    return text or None


def _node_text(node):
    if node is None:
        return ""
    return _clean_text(node.get_text(" ", strip=True))


def _html_comment_text(node):
    if node is None:
        return ""
    raw_html = str(node)
    comments = re.findall(r"<!--(.*?)-->", raw_html, flags=re.DOTALL)
    return _clean_text(" ".join(comments))


def _first_image_url(image):
    if image is None:
        return ""
    for attr in ("src", "data-delayed-url"):
        value = _clean_text(image.get(attr))
        if value and "static.licdn.com/aero-v1/sc/h/" not in value:
            return value
    return ""


def _is_linkedin_org_href(href):
    value = _clean_text(href).lower()
    return any(segment in value for segment in ["/company/", "/school/"])


def _find_public_detail_root(soup):
    if soup is None:
        return None

    job_id_node = soup.find(id="decoratedJobPostingId")
    if job_id_node is not None:
        detail_root = job_id_node.find_parent("div")
        if detail_root is not None:
            return detail_root

    topcard_title = soup.find(attrs={"data-tracking-control-name": "public_jobs_topcard-title"})
    if topcard_title is not None:
        root = topcard_title
        for _ in range(8):
            if root.parent is None:
                break
            root = root.parent
            if root.find(id="decoratedJobPostingId") is not None:
                return root
        return root

    return soup


def _sanitize_html_fragment(node):
    if node is None:
        return ""

    fragment = BeautifulSoup(str(node), "html.parser")
    root = fragment.find(attrs={"data-testid": "expandable-text-box"}) or fragment
    for noisy_node in root.find_all(["script", "style", "noscript", "svg"]):
        noisy_node.decompose()
    for noisy_node in root.find_all(attrs={"data-testid": "expandable-text-button"}):
        noisy_node.decompose()
    for noisy_node in root.find_all("button"):
        noisy_node.decompose()

    if root is fragment:
        html = "".join(str(child) for child in fragment.contents)
    else:
        html = "".join(str(child) for child in root.contents)
    return html.strip()


def _is_premium_or_upsell_node(node):
    if node is None:
        return False

    href = _clean_text(node.get("href") if hasattr(node, "get") else "")
    if href and ("premium/products" in href.lower() or "upsell" in href.lower()):
        return True

    text = _node_text(node).lower()
    return any(token in text for token in PREMIUM_TEXT_TOKENS)


def _jsonld_objects(value):
    if isinstance(value, list):
        for item in value:
            yield from _jsonld_objects(item)
        return

    if not isinstance(value, dict):
        return

    yield value
    graph = value.get("@graph")
    if isinstance(graph, (list, dict)):
        yield from _jsonld_objects(graph)


def _jsonld_name(value):
    if isinstance(value, str):
        return _clean_text(value)
    if isinstance(value, dict):
        return _clean_text(value.get("name"))
    if isinstance(value, list):
        for item in value:
            name = _jsonld_name(item)
            if name:
                return name
    return ""


def _extract_jobposting_jsonld(soup):
    if soup is None:
        return {}

    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        payload = _clean_text(script.string or script.get_text(" ", strip=True))
        if not payload:
            continue
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError:
            continue

        for item in _jsonld_objects(parsed):
            raw_type = item.get("@type")
            types = raw_type if isinstance(raw_type, list) else [raw_type]
            normalized_types = {_clean_text(type_value).lower() for type_value in types}
            if "jobposting" in normalized_types:
                return item
    return {}


def _extract_jsonld_location(jsonld):
    location = jsonld.get("jobLocation") if isinstance(jsonld, dict) else None
    if isinstance(location, list):
        location = location[0] if location else None
    if not isinstance(location, dict):
        return ""

    address = location.get("address")
    if not isinstance(address, dict):
        return _clean_text(location.get("name"))

    parts = [
        address.get("addressLocality"),
        address.get("addressRegion"),
        address.get("addressCountry"),
    ]
    return _clean_text(", ".join(_clean_text(part) for part in parts if _clean_text(part)))


def _extract_jsonld_logo(jsonld):
    organization = jsonld.get("hiringOrganization") if isinstance(jsonld, dict) else None
    if isinstance(organization, list):
        organization = organization[0] if organization else None
    if not isinstance(organization, dict):
        return ""

    logo = organization.get("logo")
    if isinstance(logo, dict):
        logo = logo.get("url")
    return _clean_text(logo)


def _normalize_contract_type(value):
    text = _clean_text(value)
    if not text:
        return ""
    normalized = _normalize_search_text(text.replace("_", " ").replace("-", " "))
    for label, pattern in CONTRACT_TYPE_PATTERNS:
        if pattern.search(normalized):
            return label
    return ""


def _normalize_availability(value):
    text = _clean_text(value)
    if not text:
        return ""
    normalized = _normalize_search_text(text)
    if normalized in AVAILABILITY_CANONICAL_MAP:
        return AVAILABILITY_CANONICAL_MAP[normalized]
    for _, pattern in AVAILABILITY_PATTERNS:
        if pattern.search(normalized):
            return text
    return ""


def _is_availability_candidate(value):
    text = _normalize_availability(value)
    if not text:
        return False
    normalized = _normalize_search_text(text)
    if not normalized:
        return False
    if re.search(r"[.!?]", text):
        return False
    return len(normalized.split()) <= 5


def _availability_priority(value):
    normalized = _normalize_search_text(value)
    if not normalized:
        return 0
    if re.search(r"\btemps\s+plein\b|\bplein\s+temps\b|\bfull\s*time\b|\btemps\s+partiel\b|\bpart\s*time\b", normalized):
        return 3
    if re.search(r"\bhybride\b|\bhybrid\b|\bremote\b|\ba\s+distance\b|\bpresentiel\b|\bon\s*site\b", normalized):
        return 2
    return 1


def _build_job_fingerprint(title, company, location, description=""):
    base = "|".join(
        part for part in (
            _normalize_fingerprint_text(title),
            _normalize_fingerprint_text(company),
            _normalize_fingerprint_text(location),
            _normalize_fingerprint_text(description)[:200],
        )
        if part
    )
    if not base:
        return ""
    return hashlib.sha1(base.encode("utf-8")).hexdigest()


def _parse_relative_publication_date(text):
    value = _clean_text(text)
    if not value:
        return ""

    match = RELATIVE_TIME_RE.search(value)
    if not match:
        return ""

    amount = int(match.group(1))
    unit = match.group(2).lower()
    if unit.startswith(("minute", "hour", "heure")):
        delta_days = 0
    elif unit.startswith(("jour", "day")):
        delta_days = amount
    elif unit.startswith(("semaine", "week")):
        delta_days = amount * 7
    elif unit.startswith("mois") or unit.startswith("month"):
        delta_days = amount * 30
    elif unit in {"an", "ans"} or unit.startswith("year"):
        delta_days = amount * 365
    else:
        return ""
    return (date.today() - timedelta(days=delta_days)).isoformat()


def _is_title_candidate(text, company_name="", location=""):
    value = _clean_text(text)
    if not value or len(value) < 5 or len(value) > 120:
        return False

    normalized = value.lower()
    if company_name and normalized == _clean_text(company_name).lower():
        return False
    if location and normalized == _clean_text(location).lower():
        return False
    if normalized in {"tunisia", "tunisie", "tunis"}:
        return False
    if any(token in normalized for token in TITLE_FORBIDDEN_TOKENS):
        return False
    if RELATIVE_TIME_RE.search(value):
        return False
    if _normalize_contract_type(value) or _normalize_availability(value):
        return False
    if re.fullmatch(r"[+\d\s]+candidatures?", normalized):
        return False
    if LOCATION_HINT_RE.fullmatch(normalized):
        return False
    blocked_tokens = {
        "apply",
        "postuler",
        "applicant",
        "candidat",
        "linkedin",
        "followers",
        "abonnes",
    }
    return not any(token in normalized for token in blocked_tokens)


def _is_description_stop_line(text):
    line = _clean_text(text).lower()
    if not line:
        return False
    return any(pattern in line for pattern in DESCRIPTION_STOP_PATTERNS)


def _is_description_noise_line(text):
    line = _clean_text(text)
    if not line:
        return True

    normalized = line.lower()
    if normalized in DETAIL_NOISE_TEXT:
        return True
    if any(pattern in normalized for pattern in DESCRIPTION_NOISE_PATTERNS):
        return True

    spam_hits = sum(1 for token in DESCRIPTION_SPAM_TOKENS if token in normalized)
    if spam_hits >= 4:
        return True

    return False


def _render_description_html(lines):
    if not lines:
        return ""

    html_parts = []
    bullet_buffer = []

    def flush_bullets():
        nonlocal bullet_buffer
        if not bullet_buffer:
            return
        bullet_items = "".join(f"<li>{escape(item)}</li>" for item in bullet_buffer)
        html_parts.append(f"<ul>{bullet_items}</ul>")
        bullet_buffer = []

    for line in lines:
        if line.startswith("- "):
            bullet_buffer.append(line[2:].strip())
            continue
        flush_bullets()
        html_parts.append(f"<p>{escape(line)}</p>")

    flush_bullets()
    return "".join(html_parts)


def _extract_detail_description_container(soup):
    if soup is None:
        return None

    for selector in [
        "[data-testid='expandable-text-box']",
        ".show-more-less-html__markup",
        ".description__text",
        "[data-max-lines]",
    ]:
        node = soup.select_one(selector)
        if node is not None and not _is_premium_or_upsell_node(node):
            return node
    return None


def _extract_description_lines(container):
    if container is None:
        return []

    fragment = BeautifulSoup(str(container), "html.parser")
    for noisy_node in fragment.select("script, style, noscript, svg, button"):
        noisy_node.decompose()

    for anchor in fragment.select("a"):
        anchor.replace_with(anchor.get_text(" ", strip=True))

    lines = []
    seen = set()
    for raw_line in fragment.get_text("\n", strip=True).splitlines():
        line = _clean_text(raw_line)
        if not line:
            continue
        if _is_description_stop_line(line):
            break
        if _is_description_noise_line(line):
            continue
        normalized = _normalize_search_text(line)
        if normalized in seen:
            continue
        seen.add(normalized)
        lines.append(line)
    return lines


def _normalize_label_token(value):
    return _normalize_search_text(_clean_text(value).rstrip(":"))


def _extract_multiline_labeled_value(lines, labels):
    if not lines:
        return ""

    normalized_labels = tuple(_normalize_label_token(label) for label in labels)
    for index, line in enumerate(lines):
        normalized_line = _normalize_label_token(line)
        for label in normalized_labels:
            if not label:
                continue
            prefix = f"{label} "
            if normalized_line == label and index + 1 < len(lines):
                return _clean_text(lines[index + 1])
            if normalized_line.startswith(prefix):
                return _clean_text(line[len(line.split(":", 1)[0]) :].lstrip(": ").strip())
            line_match = re.match(rf"^\s*{re.escape(label)}\s*:\s*(.+)$", normalized_line, flags=re.IGNORECASE)
            if line_match:
                return _clean_text(line_match.group(1))
    return ""


def _is_section_heading(line):
    normalized = _normalize_label_token(line)
    if not normalized:
        return False
    if normalized in {_normalize_label_token(hint) for hint in SECTION_BREAK_HINTS}:
        return True
    if len(normalized.split()) <= 4 and not re.search(r"[.!?]", line):
        return normalized.endswith(("recherche", "recherché", "academique", "académique", "missions", "exigences"))
    return False


def _extract_description_section(lines, headings, max_lines=8):
    if not lines:
        return []

    normalized_headings = tuple(_normalize_label_token(heading) for heading in headings)
    for index, line in enumerate(lines):
        normalized_line = _normalize_label_token(line)
        if not any(heading and heading in normalized_line for heading in normalized_headings):
            continue

        section_lines = []
        for candidate in lines[index + 1 :]:
            if _is_section_heading(candidate):
                break
            section_lines.append(candidate)
            if len(section_lines) >= max_lines:
                break
        if section_lines:
            return section_lines
    return []


def _extract_detail_job_criteria(soup):
    if soup is None:
        return {}

    criteria = {}
    for item in soup.select(".description__job-criteria-list .description__job-criteria-item"):
        label_node = item.select_one(".description__job-criteria-subheader, h3, dt, strong")
        label = _clean_text(_node_text(label_node))
        if not label:
            continue

        value = ""
        for candidate in item.select(".description__job-criteria-text, span, p, a, dd"):
            candidate_value = _node_text(candidate)
            if not candidate_value or candidate_value == label:
                continue
            value = candidate_value
            break

        if value:
            criteria[_normalize_label_token(label)] = value
    return criteria


def _criteria_value(criteria_map, labels):
    normalized_labels = tuple(_normalize_label_token(label) for label in labels)
    for key, value in criteria_map.items():
        if any(label and label in key for label in normalized_labels):
            return _clean_text(value)
    return ""


def _normalize_skill_source_text(value):
    text = _clean_text(value).lower()
    if not text:
        return ""
    for pattern, replacement in SKILL_SOURCE_REPLACEMENTS:
        text = pattern.sub(replacement, text)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("&", " and ")
    text = text.replace("+", " ")
    text = re.sub(r"[^a-z0-9\s-]", " ", text)
    return WHITESPACE_RE.sub(" ", text).strip()


def _iter_skill_segments(raw_text):
    cleaned_text = _clean_multiline_text(raw_text)
    if not cleaned_text:
        return []

    segments = []
    for raw_line in cleaned_text.splitlines():
        for part in SKILL_SEGMENT_SPLIT_RE.split(raw_line):
            segment = _clean_text(part)
            if segment:
                segments.append(segment)
    return segments


def _normalize_skill_phrase(value):
    normalized = _normalize_skill_source_text(value)
    if not normalized:
        return ""

    tokens = normalized.split()
    if len(tokens) > 1 and len(tokens[-1]) > 4:
        if tokens[-1].endswith("ies"):
            tokens[-1] = f"{tokens[-1][:-3]}y"
        elif tokens[-1].endswith("s") and not tokens[-1].endswith(("is", "ss")):
            tokens[-1] = tokens[-1][:-1]
        normalized = " ".join(tokens)

    for pattern, canonical in SKILL_NORMALIZATION_RULES:
        if pattern.search(normalized):
            return canonical
    return normalized


def _skill_core_tokens(value):
    return [token for token in value.split() if token and token not in SKILL_CONNECTOR_TOKENS]


def _is_noise_skill_token(token):
    if not token:
        return True
    if token in SKILL_STOPWORDS or token in SKILL_NOISE_TERMS or token in SKILL_VERB_BLACKLIST:
        return True
    if token.isdigit():
        return True
    if len(token) < 3 and token not in SKILL_SHORT_TOKENS:
        return True
    return False


def _build_skill_candidate(tokens):
    if not tokens:
        return None
    if tokens[0] in SKILL_STOPWORDS or tokens[-1] in SKILL_STOPWORDS:
        return None

    core_tokens = [token for token in tokens if token not in SKILL_CONNECTOR_TOKENS]
    if not core_tokens or any(_is_noise_skill_token(token) for token in core_tokens):
        return None
    if len(core_tokens) > 1 and all(token in SKILL_SHORT_TOKENS for token in core_tokens):
        return None
    if len(core_tokens) > 1 and any(token in SKILL_CONNECTOR_TOKENS for token in tokens):
        if all(token in SKILL_SIGNAL_VOCAB for token in core_tokens):
            return None

    canonical = _normalize_skill_phrase(" ".join(tokens))
    canonical_tokens = _skill_core_tokens(canonical)
    if not canonical_tokens or any(_is_noise_skill_token(token) for token in canonical_tokens):
        return None

    if len(canonical_tokens) == 1 and canonical_tokens[0] in SKILL_SINGLETON_GENERIC_TOKENS:
        return None

    signal_strength = len(set(canonical_tokens) & SKILL_SIGNAL_VOCAB)
    if signal_strength == 0:
        if len(canonical_tokens) == 1:
            return None
    if len(canonical_tokens) > 1:
        non_signal_tokens = [token for token in canonical_tokens if token not in SKILL_SIGNAL_VOCAB]
        if non_signal_tokens and any(token not in SKILL_ALLOWED_NOUN_TOKENS for token in non_signal_tokens):
            return None

    return {
        "label": canonical,
        "tokens": tuple(canonical_tokens),
        "signal_strength": signal_strength,
    }


def _skill_position_weight(position):
    if position < 20:
        return 1.0
    if position < 60:
        return 0.7
    if position < 120:
        return 0.4
    return 0.2


def _is_duplicate_skill_candidate(candidate, selected):
    candidate_set = set(candidate["tokens"])
    for item in selected:
        selected_set = set(item["tokens"])
        if candidate["label"] == item["label"]:
            return True
        if candidate_set == selected_set:
            return True
        if candidate_set.issubset(selected_set) or selected_set.issubset(candidate_set):
            return True
    return False


def _extract_skill_keywords(*texts):
    ranked_candidates = {}
    position_offset = 0

    for text_index, raw_text in enumerate(texts):
        source_weight = 1.25 if text_index else 1.0
        segments = _iter_skill_segments(raw_text)
        for segment in segments:
            normalized_segment = _normalize_skill_source_text(segment)
            if not normalized_segment:
                continue

            tokens = normalized_segment.split()
            if not tokens:
                continue

            segment_has_cue = bool(SKILL_CUE_RE.search(normalized_segment))
            segment_signal_count = len(set(tokens) & SKILL_SIGNAL_VOCAB)

            for start in range(len(tokens)):
                for size in (1, 2, 3):
                    phrase_tokens = tokens[start : start + size]
                    if len(phrase_tokens) != size:
                        continue

                    candidate = _build_skill_candidate(phrase_tokens)
                    if candidate is None:
                        continue

                    occurrence_score = (
                        source_weight
                        + _skill_position_weight(position_offset + start)
                        + 0.35 * candidate["signal_strength"]
                        + 0.1 * min(segment_signal_count, 4)
                        + (0.25 if segment_has_cue else 0.0)
                        + 0.15 * max(0, len(candidate["tokens"]) - 1)
                    )
                    record = ranked_candidates.setdefault(
                        candidate["label"],
                        {
                            "label": candidate["label"],
                            "tokens": candidate["tokens"],
                            "score": 0.0,
                            "frequency": 0,
                            "position": position_offset + start,
                        },
                    )
                    record["score"] += occurrence_score
                    record["frequency"] += 1
                    record["position"] = min(record["position"], position_offset + start)

            position_offset += len(tokens)

    ranked = sorted(
        ranked_candidates.values(),
        key=lambda item: (-item["score"], -len(item["tokens"]), item["position"], item["label"]),
    )

    selected = []
    for candidate in ranked:
        if _is_duplicate_skill_candidate(candidate, selected):
            continue
        selected.append(candidate)
        if len(selected) >= SKILL_MAX_RESULTS:
            break

    return [item["label"] for item in selected]


def _clean_description_container(container):
    if container is None:
        return "", ""

    fragment = BeautifulSoup(str(container), "html.parser")
    for noisy_node in fragment.select("script, style, noscript, svg, button"):
        noisy_node.decompose()

    for anchor in fragment.select("a"):
        anchor.replace_with(anchor.get_text(" ", strip=True))

    for span in fragment.select("span"):
        if not span.get_text(" ", strip=True):
            span.decompose()

    for li in fragment.select("li"):
        li.insert(0, "- ")

    raw_text = fragment.get_text("\n", strip=True)
    cleaned_lines = []
    seen = set()
    pending_bullet = False

    for raw_line in raw_text.splitlines():
        line = _clean_text(raw_line)
        if not line:
            continue
        if line in {"-", "•", "*"}:
            pending_bullet = True
            continue
        if pending_bullet:
            line = f"- {line}"
            pending_bullet = False
        if _is_description_stop_line(line):
            break
        if _is_description_noise_line(line):
            continue
        dedup_key = line.lower()
        if dedup_key in seen:
            continue
        seen.add(dedup_key)
        cleaned_lines.append(line)

    text_lines = [re.sub(r"^-+\s*", "", line).strip() for line in cleaned_lines]
    description_text = " ".join(text_lines).strip()
    description_html = _render_description_html(cleaned_lines)
    return description_text, description_html


def _iter_context_roots(node):
    seen = set()
    current = node
    for _ in range(5):
        if current is None:
            break
        current = current.parent
        if current is None:
            break
        marker = id(current)
        if marker in seen:
            continue
        seen.add(marker)
        yield current


def _extract_detail_company_anchor(soup):
    if soup is None:
        return None
    for anchor in soup.find_all("a", href=True):
        if _is_premium_or_upsell_node(anchor):
            continue
        href = _clean_text(anchor.get("href"))
        if not _is_linkedin_org_href(href):
            continue
        text = _node_text(anchor)
        if text:
            return anchor
    return None


def _extract_detail_title(soup, company_name="", location="", jsonld=None):
    jsonld = jsonld or {}
    company_anchor = _extract_detail_company_anchor(soup)
    roots = list(_iter_context_roots(company_anchor)) if company_anchor else []
    roots.append(soup)

    for root in roots:
        if root is None:
            continue
        for selector in [
            "h1",
            "h2.topcard__title",
            "a[data-tracking-control-name='public_jobs_topcard-title'] h1",
            "a[data-tracking-control-name='public_jobs_topcard-title'] h2",
            "[data-tracking-control-name='public_jobs_topcard-title']",
        ]:
            node = root.select_one(selector)
            text = _node_text(node)
            if _is_title_candidate(text, company_name=company_name, location=location):
                return text

    for root in roots:
        if root is None:
            continue
        for node in root.find_all(["h1", "h2", "h3", "p", "span"]):
            if _is_premium_or_upsell_node(node):
                continue
            text = _node_text(node)
            if _is_title_candidate(text, company_name=company_name, location=location):
                return text

    return _clean_text(jsonld.get("title"))


def _extract_detail_company_name(soup, jsonld=None):
    jsonld = jsonld or {}
    anchor = _extract_detail_company_anchor(soup)
    if anchor is not None:
        text = _node_text(anchor)
        if text:
            return text

    organization = jsonld.get("hiringOrganization") if isinstance(jsonld, dict) else None
    return _jsonld_name(organization)


def _extract_detail_company_logo(soup, job_url="", jsonld=None):
    candidates = []
    jsonld = jsonld or {}
    if soup is not None:
        for selector in [
            "a[data-tracking-control-name='public_jobs_topcard_logo'] img",
            ".top-card-layout__card img",
            ".sub-nav-cta__image",
        ]:
            for image in soup.select(selector):
                src = _first_image_url(image)
                if src:
                    candidates.append(src)

        company_anchor = _extract_detail_company_anchor(soup)
        if company_anchor is not None:
            for root in _iter_context_roots(company_anchor):
                for image in root.find_all("img"):
                    src = _first_image_url(image)
                    if src:
                        candidates.append(src)

        for image in soup.find_all("img"):
            src = _first_image_url(image)
            if not src:
                continue
            alt = _clean_text(image.get("alt")).lower()
            src_lower = src.lower()
            if "company-logo" in src_lower or "media.licdn.com" in src_lower or "logo" in alt:
                candidates.append(src)

    jsonld_logo = _extract_jsonld_logo(jsonld)
    if jsonld_logo:
        candidates.append(jsonld_logo)

    for candidate in candidates:
        absolute_url = _clean_text(urljoin(job_url, candidate))
        if absolute_url:
            return absolute_url
    return ""


def _location_from_text(text):
    value = _clean_text(text)
    if not value:
        return ""

    candidates = [value]
    if "·" in value:
        candidates = [_clean_text(part) for part in value.split("·")]
    if "|" in value:
        candidates = [_clean_text(part) for part in value.split("|")]
    if "·" in value:
        candidates = [_clean_text(part) for part in value.split("·")]

    for candidate in candidates:
        if not candidate or len(candidate) > 100:
            continue

        normalized = candidate.lower()
        noisy_tokens = {
            "applicant",
            "candidat",
            "followers",
            "abonnes",
            "full-time",
            "part-time",
            "temps plein",
            "temps partiel",
            "postuler",
            "recruteur",
            "recruiter",
            "recrutement",
            "hired",
            "premium",
        }
        if any(token in normalized for token in noisy_tokens):
            continue
        if RELATIVE_TIME_RE.search(candidate) or _normalize_contract_type(candidate) or _normalize_availability(candidate):
            continue
        if re.search(r"[A-Za-z]", candidate) and ("," in candidate or LOCATION_HINT_RE.search(candidate)):
            return candidate
    return ""


def _extract_detail_location(soup, jsonld=None):
    if soup is not None:
        for node in soup.find_all(["span", "p"]):
            if _is_premium_or_upsell_node(node):
                continue
            location = _location_from_text(_node_text(node))
            if location:
                return location
    return _extract_jsonld_location(jsonld or {})


def _extract_labeled_value(soup, labels):
    if soup is None:
        return ""

    normalized_labels = tuple(_clean_text(label).lower().rstrip(":") for label in labels)
    for label_node in soup.find_all(["h3", "dt", "strong", "span", "p"]):
        if _is_premium_or_upsell_node(label_node):
            continue
        label_text = _clean_text(label_node.get_text(" ", strip=True)).lower().rstrip(":")
        if not any(label in label_text for label in normalized_labels):
            continue

        search_roots = [
            label_node.find_parent(["li", "dl", "div", "section"]),
            label_node.parent,
            label_node.find_next_sibling(),
        ]
        for root in search_roots:
            if root is None:
                continue
            for candidate in root.find_all(["span", "dd", "p", "div"], recursive=True):
                if candidate is label_node or _is_premium_or_upsell_node(candidate):
                    continue
                value = _node_text(candidate)
                value_key = value.lower().rstrip(":")
                if not value or value_key == label_text:
                    continue
                if any(label in value_key for label in normalized_labels):
                    continue
                return value

            value = _node_text(root)
            if value and label_text in value.lower():
                value = _clean_text(value.replace(_node_text(label_node), "", 1))
                if value:
                    return value

    return ""


def _extract_detail_contract_type(soup, jsonld=None):
    labeled_value = _extract_labeled_value(
        soup,
        ["Type d’emploi", "Type d'emploi", "Employment type", "Job type"],
    )
    contract_type = _normalize_contract_type(labeled_value)
    if contract_type:
        return contract_type

    if soup is not None:
        for node in soup.find_all(["span", "a", "p", "li"]):
            if _is_premium_or_upsell_node(node):
                continue
            contract_type = _normalize_contract_type(_node_text(node))
            if contract_type:
                return contract_type

    employment_type = (jsonld or {}).get("employmentType")
    if isinstance(employment_type, list):
        employment_type = employment_type[0] if employment_type else ""
    return _normalize_contract_type(employment_type)


def _extract_detail_publication_date(soup, jsonld=None):
    if soup is not None:
        for node in soup.find_all("time"):
            datetime_value = _clean_text(node.get("datetime"))
            if len(datetime_value) >= 10:
                return datetime_value[:10]

            parsed_relative = _parse_relative_publication_date(_node_text(node))
            if parsed_relative:
                return parsed_relative

        for node in soup.find_all(["span", "p"]):
            if _is_premium_or_upsell_node(node):
                continue
            parsed_relative = _parse_relative_publication_date(_node_text(node))
            if parsed_relative:
                return parsed_relative

    date_posted = _clean_text((jsonld or {}).get("datePosted"))
    if len(date_posted) >= 10:
        return date_posted[:10]
    return ""


def _extract_detail_deadline(jsonld=None):
    valid_through = _clean_text((jsonld or {}).get("validThrough"))
    if len(valid_through) < 10:
        return ""
    candidate = valid_through[:10]
    try:
        return date.fromisoformat(candidate).isoformat()
    except ValueError:
        return ""


def _extract_detail_status(soup):
    if soup is None:
        return "ACTIVE"

    normalized_text = _normalize_search_text(soup.get_text(" ", strip=True))
    closed_messages = (
        "les candidatures ne sont plus acceptees",
        "applications are no longer accepted",
        "no longer accepting applications",
    )
    if any(message in normalized_text for message in closed_messages):
        return "EXPIREE"
    return "ACTIVE"


def _extract_detail_description(soup, jsonld=None):
    description_node = soup.find(attrs={"data-testid": "expandable-text-box"}) if soup is not None else None
    if description_node is not None:
        description_text, description_html = _clean_description_container(description_node)
        if description_text:
            return description_text, description_html

    fallback_markup = soup.select_one(".show-more-less-html__markup") if soup is not None else None
    if fallback_markup is not None:
        description_text, description_html = _clean_description_container(fallback_markup)
        if description_text:
            return description_text, description_html

    if soup is not None:
        for heading in soup.find_all(["h2", "h3", "p"]):
            if _is_premium_or_upsell_node(heading):
                continue
            heading_text = _node_text(heading).lower()
            if not any(token in heading_text for token in ["description", "about the job", "about the role"]):
                continue

            for sibling in heading.find_next_siblings():
                if _is_premium_or_upsell_node(sibling):
                    continue
                text, html = _clean_description_container(sibling)
                if text:
                    return text, html

        for node in soup.select("[data-max-lines], .show-more-less-html__markup"):
            if _is_premium_or_upsell_node(node):
                continue
            text, html = _clean_description_container(node)
            if text:
                return text, html

    jsonld_description = _clean_text((jsonld or {}).get("description"))
    if jsonld_description:
        text, html = _clean_description_container(BeautifulSoup(jsonld_description, "html.parser"))
        return text or jsonld_description, html or jsonld_description

    return "", ""


def _extract_detail_contract_type_refined(description_lines, criteria_map, jsonld=None):
    labeled_value = _extract_multiline_labeled_value(
        description_lines,
        ["Type de Contrat", "Type de contrat", "Contract type", "Type contrat"],
    )
    contract_type = _normalize_contract_type(labeled_value)
    if contract_type:
        return contract_type

    criteria_value = _criteria_value(
        criteria_map,
        ["Type dâ€™emploi", "Type d'emploi", "Employment type", "Job type"],
    )
    if criteria_value and not _normalize_availability(criteria_value):
        contract_type = _normalize_contract_type(criteria_value)
        if contract_type:
            return contract_type

    for line in description_lines[:8]:
        contract_type = _normalize_contract_type(line)
        if contract_type:
            return contract_type

    employment_type = (jsonld or {}).get("employmentType")
    if isinstance(employment_type, list):
        employment_type = employment_type[0] if employment_type else ""
    return _normalize_contract_type(employment_type)


def _extract_detail_availability(description_lines, criteria_map, soup=None):
    labeled_value = _extract_multiline_labeled_value(
        description_lines,
        ["DisponibilitÃ©", "Disponibilité", "Disponibilite", "Availability"],
    )
    availability = _normalize_availability(labeled_value)
    if availability:
        return availability

    criteria_value = _criteria_value(
        criteria_map,
        ["Type dâ€™emploi", "Type d'emploi", "Employment type", "Job type"],
    )
    if _is_availability_candidate(criteria_value):
        return _normalize_availability(criteria_value)

    for line in description_lines[:8]:
        if _is_availability_candidate(line):
            return _normalize_availability(line)

    if soup is not None:
        best_candidate = ""
        best_priority = 0
        for node in soup.find_all(["a", "span", "p", "li"]):
            if _is_premium_or_upsell_node(node):
                continue
            value = _node_text(node)
            if _is_availability_candidate(value):
                priority = _availability_priority(value)
                if priority > best_priority:
                    best_priority = priority
                    best_candidate = _normalize_availability(value)
        if best_candidate:
            return best_candidate
    return ""


def _extract_detail_publication_date_refined(soup, jsonld=None):
    if soup is not None:
        for selector in [".posted-time-ago__text", ".topcard__flavor--metadata"]:
            for node in soup.select(selector):
                if _is_premium_or_upsell_node(node):
                    continue
                parsed_relative = _parse_relative_publication_date(_node_text(node))
                if parsed_relative:
                    return parsed_relative
    return _extract_detail_publication_date(soup, jsonld=jsonld)


def _extract_detail_description_refined(soup, jsonld=None):
    description_node = _extract_detail_description_container(soup)
    if description_node is not None:
        description_text, description_html = _clean_description_container(description_node)
        if description_text:
            return description_text, description_html, description_node

    description_text, description_html = _extract_detail_description(soup, jsonld=jsonld)
    return description_text, description_html, description_node


def _extract_detail_education_level(description_lines):
    if not description_lines:
        return ""

    candidate_blocks = [
        _extract_description_section(description_lines, EDUCATION_SECTION_HINTS, max_lines=6),
        _extract_description_section(description_lines, JOB_QUALIFICATIONS_SECTION_HINTS, max_lines=6),
        description_lines,
    ]
    for block in candidate_blocks:
        combined = " ".join(block)
        for label, pattern in DEGREE_PATTERNS:
            if pattern.search(combined):
                return label
    return ""


def _extract_detail_job_qualifications(description_lines):
    section_lines = _extract_description_section(
        description_lines,
        JOB_QUALIFICATIONS_SECTION_HINTS,
        max_lines=8,
    )
    if not section_lines:
        return ""
    return "\n".join(section_lines)


def _extract_detail_company_sector(criteria_map):
    return _criteria_value(criteria_map, ["Secteurs", "Sector", "Sectors"])


def _extract_detail_apply_url(soup, job_url=""):
    if soup is not None:
        safety_links = []
        apply_links = []
        job_links = []
        for anchor in soup.find_all("a", href=True):
            if _is_premium_or_upsell_node(anchor):
                continue
            href = _clean_text(anchor.get("href"))
            href_lower = href.lower()
            absolute_href = urljoin(job_url, href)
            if "linkedin.com/safety/go" in href_lower:
                safety_links.append(absolute_href)
            elif "/apply/" in href_lower or href_lower.rstrip("/").endswith("/apply"):
                apply_links.append(absolute_href)
            elif "/jobs/view/" in href_lower:
                job_links.append(absolute_href)

        if safety_links:
            return safety_links[0]
        if apply_links:
            return _canonicalize_job_url(apply_links[0])
        if job_links:
            return _canonicalize_job_url(job_links[0])

    return _canonicalize_job_url(job_url) or _clean_text(job_url)


def parse_linkedin_job_detail_html(html, job_url=""):
    """
    Parse LinkedIn detail HTML using stable structure, attributes, text, and URLs.
    CSS class names are intentionally ignored because LinkedIn obfuscates them.
    """
    soup = BeautifulSoup(html or "", "html.parser")
    jsonld = _extract_jobposting_jsonld(soup)
    detail_root = _find_public_detail_root(soup)

    company_name = _extract_detail_company_name(detail_root, jsonld=jsonld)
    location = _extract_detail_location(detail_root, jsonld=jsonld)
    title = _extract_detail_title(detail_root, company_name=company_name, location=location, jsonld=jsonld)
    company_logo = _extract_detail_company_logo(detail_root, job_url=job_url, jsonld=jsonld)
    criteria_map = _extract_detail_job_criteria(detail_root)
    description_text, description_html, description_node = _extract_detail_description_refined(detail_root, jsonld=jsonld)
    description_lines = _extract_description_lines(description_node) if description_node is not None else []
    if not description_lines and description_text:
        description_lines = [line for line in _clean_multiline_text(description_text).splitlines() if line]
    contract_type = _extract_detail_contract_type_refined(description_lines, criteria_map, jsonld=jsonld)
    availability = _extract_detail_availability(description_lines, criteria_map, soup=detail_root)
    if not contract_type and availability:
        # LinkedIn often exposes only "Type d'emploi: Temps plein/partiel" without
        # a stronger contractual signal (CDI/CDD/Freelance). Keep that value in
        # contract_type as a fallback so the UI does not lose the employment type.
        contract_type = availability
    publication_date = _extract_detail_publication_date_refined(detail_root, jsonld=jsonld)
    deadline = _extract_detail_deadline(jsonld=jsonld)
    status = _extract_detail_status(soup)
    education_level = _extract_detail_education_level(description_lines)
    job_qualifications = _extract_detail_job_qualifications(description_lines)
    company_sector = _extract_detail_company_sector(criteria_map)
    skills = _extract_skill_keywords(description_text, job_qualifications)
    apply_url = _extract_detail_apply_url(detail_root, job_url=job_url)

    if not title or not description_text:
        logger.warning(
            "LinkedIn extraction incomplete for job_url=%s title_present=%s description_present=%s",
            job_url,
            bool(title),
            bool(description_text),
        )

    return {
        "title": _nullable(title),
        "company_name": _nullable(company_name),
        "company_logo": _nullable(company_logo),
        "location": _nullable(location),
        "contract_type": _nullable(contract_type),
        "availability": _nullable(availability),
        "publication_date": _nullable(publication_date),
        "deadline": _nullable(deadline),
        "status": status,
        "description_text": _nullable(description_text),
        "description_html": description_html or None,
        "education_level": _nullable(education_level),
        "job_qualifications": _nullable(job_qualifications),
        "company_sector": _nullable(company_sector),
        "skills": skills or None,
        "apply_url": _nullable(apply_url),
    }


def parse_linkedin_job(html: str) -> dict:
    return parse_linkedin_job_detail_html(html)


def _build_session():
    session = requests.Session()
    session.headers.update(REQUEST_HEADERS)

    retry_strategy = Retry(
        total=DEFAULT_MAX_RETRIES,
        backoff_factor=1,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET", "HEAD", "OPTIONS"}),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def _rate_limit_delay(min_delay=DEFAULT_MIN_DELAY, max_delay=DEFAULT_MAX_DELAY):
    time.sleep(random.uniform(min_delay, max_delay))


def _canonicalize_job_url(url):
    value = _clean_text(url)
    if not value:
        return ""

    try:
        parsed = urlparse(value)
    except Exception:
        return ""

    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""

    filtered_query = []
    if parsed.query:
        for raw_part in parsed.query.split("&"):
            if not raw_part:
                continue
            key = raw_part.split("=", 1)[0].strip()
            if key in TRACKING_QUERY_KEYS:
                continue
            filtered_query.append(raw_part)

    query = "&".join(filtered_query)
    return urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path.rstrip("/"), "", query, ""))


def _is_valid_url(url):
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _extract_job_id(url, card):
    href = _clean_text(url)
    match = JOB_ID_RE.search(href)
    if match:
        return match.group(1)

    entity_urn = _clean_text(card.get("data-entity-urn"))
    if entity_urn and ":" in entity_urn:
        return entity_urn.rsplit(":", 1)[-1]
    return ""


def _extract_publication_date(card):
    time_node = card.select_one("time[datetime]")
    if time_node:
        raw_value = _clean_text(time_node.get("datetime"))
        if len(raw_value) >= 10:
            return raw_value[:10]

    time_text = _clean_text(card.select_one("time").get_text(" ", strip=True)) if card.select_one("time") else ""
    if not time_text:
        return date.today().isoformat()

    parsed_relative = _parse_relative_publication_date(time_text)
    if parsed_relative:
        return parsed_relative

    return date.today().isoformat()


def _extract_text(card, selectors):
    for selector in selectors:
        node = card.select_one(selector)
        if not node:
            continue
        text = _clean_text(node.get_text(" ", strip=True))
        if text:
            return text
    return ""


def _extract_listing_cards(soup):
    if soup is None:
        return []

    cards = []
    for node in soup.find_all(attrs={"data-entity-urn": True}):
        entity_urn = _clean_text(node.get("data-entity-urn")).lower()
        if "jobposting" not in entity_urn:
            continue
        if node.find("a", href=lambda href: href and "/jobs/view/" in href):
            cards.append(node)
    if cards:
        return cards

    fallback_cards = soup.select("div.base-card, div.base-search-card")
    if fallback_cards:
        return fallback_cards

    return [
        node
        for node in soup.select("li")
        if node.select_one("a.base-card__full-link, a[href*='/jobs/view/']")
    ]


def _extract_listing_title(card, link_node=None, company_name="", location=""):
    candidates = []

    for selector in [".base-search-card__title", "h3.base-search-card__title", "h3", "p"]:
        for node in card.select(selector):
            text = _node_text(node)
            if text:
                candidates.append(text)

    if link_node is not None:
        sr_only = link_node.select_one(".sr-only")
        sr_title = _node_text(sr_only) or _node_text(link_node)
        if sr_title:
            candidates.append(sr_title)

    comment_title = _html_comment_text(card)
    if comment_title:
        candidates.append(comment_title)

    seen = set()
    normalized_location = _clean_text(location).lower()
    for candidate in candidates:
        key = candidate.lower()
        if key in seen:
            continue
        seen.add(key)
        if normalized_location and key == normalized_location:
            continue
        if _is_title_candidate(candidate, company_name=company_name, location=location):
            return candidate

    return ""


def _extract_listing_company(card):
    for anchor in card.find_all("a", href=True):
        if _is_premium_or_upsell_node(anchor):
            continue
        if not _is_linkedin_org_href(anchor.get("href")):
            continue
        text = _node_text(anchor)
        if text:
            return text

    return _extract_text(
        card,
        [
            ".base-search-card__subtitle",
            "h4.base-search-card__subtitle",
            ".hidden-nested-link",
        ],
    )


def _extract_listing_location(card):
    location = _extract_text(card, [".job-search-card__location"])
    if location:
        return location

    for node in card.find_all(["span", "p"]):
        if _is_premium_or_upsell_node(node):
            continue
        location = _location_from_text(_node_text(node))
        if location:
            return location
    return ""


def _extract_listing_logo(card, job_url=""):
    for image in card.find_all("img"):
        src = _first_image_url(image)
        if not src:
            continue
        src_lower = src.lower()
        alt = _clean_text(image.get("alt")).lower()
        if "company-logo" in src_lower or "img-crop" in src_lower or "media.licdn.com" in src_lower or "logo" in alt:
            return _clean_text(urljoin(job_url, src))
    return ""


def _build_description(title, organization, location, snippet, keyword=""):
    snippet_text = _clean_text(snippet)
    if snippet_text:
        cleaned_description, _ = clean_description_for_ml(snippet_text)
        if cleaned_description:
            return cleaned_description, DESCRIPTION_QUALITY_SNIPPET

    facts = []
    title = _clean_text(title)
    organization = _clean_text(organization)
    location = _clean_text(location)
    keyword = _clean_text(keyword)

    if title:
        facts.append(f"Role: {title}.")
    if organization:
        facts.append(f"Company: {organization}.")
    if location:
        facts.append(f"Location: {location}.")
    if keyword:
        facts.append(f"Search keyword: {keyword}.")

    enriched_description = " ".join(facts)
    cleaned_description, _ = clean_description_for_ml(enriched_description)
    if cleaned_description:
        return cleaned_description, DESCRIPTION_QUALITY_METADATA
    return "", ""


def _infer_linkedin_opportunity_type(title, contract_type="", keyword=""):
    return infer_opportunity_type(title, contract_type, keyword, default="EMPLOI")


def _merge_detail_data(record, detail_data, keyword=""):
    if not detail_data:
        return record

    merged = dict(record)
    title = _clean_text(detail_data.get("title")) or merged.get("title", "")
    organization = _clean_text(detail_data.get("company_name")) or merged.get("organization", "")
    location = _clean_text(detail_data.get("location")) or merged.get("location", "")
    description_text = _clean_multiline_text(detail_data.get("description_text"))
    description_html = detail_data.get("description_html")
    contract_type = _clean_text(detail_data.get("contract_type"))
    availability = _clean_text(detail_data.get("availability"))
    company_logo = _clean_text(detail_data.get("company_logo"))
    publication_date = _clean_text(detail_data.get("publication_date"))
    deadline = _clean_text(detail_data.get("deadline"))
    detail_status = _clean_text(detail_data.get("status"))
    education_level = _clean_text(detail_data.get("education_level"))
    job_qualifications = _clean_multiline_text(detail_data.get("job_qualifications"))
    company_sector = _clean_text(detail_data.get("company_sector"))
    skills = detail_data.get("skills") if isinstance(detail_data.get("skills"), list) else []
    apply_url = _clean_text(detail_data.get("apply_url"))

    if description_text:
        description = description_text
        description_quality = DESCRIPTION_QUALITY_DETAIL
    elif merged.get("description_quality") == DESCRIPTION_QUALITY_METADATA:
        description, description_quality = _build_description(
            title,
            organization,
            location,
            "",
            keyword=keyword,
        )
    else:
        description = merged.get("description", "")
        description_quality = merged.get("description_quality", "")

    if title:
        merged["title"] = title
    if organization:
        merged["organization"] = organization
        merged["company_name"] = organization
    if location:
        merged["location"] = location
    if description:
        merged["description"] = description
        merged["description_quality"] = description_quality
    if description_text:
        merged["raw_description"] = description_text
    if description_html:
        merged["description_html"] = description_html
    if contract_type:
        merged["contract_type"] = contract_type
        merged["type_contrat"] = contract_type
    if availability:
        merged["availability"] = availability
    if company_logo:
        merged["company_logo"] = company_logo
        merged["logo_url"] = company_logo
    if publication_date:
        merged["publication_date"] = publication_date
        merged["date_publication"] = publication_date
    if deadline:
        merged["deadline"] = deadline
        merged["date_limite"] = deadline
    if detail_status == "EXPIREE":
        merged["status"] = "EXPIREE"
        merged["statut"] = "EXPIREE"
    if education_level:
        merged["education_level"] = education_level
    if job_qualifications:
        merged["job_qualifications"] = job_qualifications
    if company_sector:
        merged["company_sector"] = company_sector
    if skills:
        existing_skills = merged.get("skills") if isinstance(merged.get("skills"), list) else []
        cleaned_existing_skills = [_clean_text(skill) for skill in existing_skills if _clean_text(skill)]
        cleaned_new_skills = [_clean_text(skill) for skill in skills if _clean_text(skill)]
        merged["skills"] = list(dict.fromkeys(cleaned_existing_skills + cleaned_new_skills))
    if apply_url:
        merged["apply_url"] = apply_url

    fingerprint = _build_job_fingerprint(
        merged.get("title"),
        merged.get("organization"),
        merged.get("location"),
        merged.get("description"),
    )
    if fingerprint:
        merged["external_id"] = fingerprint

    inferred_type = _infer_linkedin_opportunity_type(
        merged.get("title"),
        merged.get("contract_type"),
        keyword,
    )
    merged["type_opportunite"] = inferred_type
    merged["opportunity_type"] = inferred_type
    return merged


def _fetch_detail_data(session, url, timeout, min_delay, max_delay):
    try:
        _rate_limit_delay(min_delay=min_delay, max_delay=max_delay)
        response = session.get(url, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("LinkedIn detail scrape failed for url=%s: %s", url, exc)
        return {}

    return parse_linkedin_job_detail_html(response.text, job_url=url)


def _parse_job_card(card, keyword="", location="", source_listing_url="", metrics=None):
    link_node = card.select_one("a.base-card__full-link, a[href*='/jobs/view/']")
    raw_url = _clean_text(link_node.get("href")) if link_node else ""
    canonical_url = _canonicalize_job_url(urljoin(LINKEDIN_SOURCE_URL, raw_url))
    if not canonical_url or not _is_valid_url(canonical_url):
        return None

    organization = _extract_listing_company(card)
    job_location = _extract_listing_location(card)
    title = _extract_listing_title(
        card,
        link_node=link_node,
        company_name=organization,
        location=job_location or location,
    )
    if not title:
        if metrics is not None:
            metrics["empty_title"] += 1
        return None

    company_logo = _extract_listing_logo(card, job_url=canonical_url)
    snippet = _extract_text(
        card,
        [
            ".job-search-card__snippet",
            ".base-search-card__metadata-container p",
            ".base-search-card__metadata-container",
        ],
    )

    publication_date = _extract_publication_date(card)
    description, description_quality = _build_description(
        title,
        organization,
        job_location,
        snippet,
        keyword=keyword,
    )
    if not description:
        if metrics is not None:
            metrics["empty_description"] += 1
        return None

    job_id = _extract_job_id(canonical_url, card)
    fingerprint = _build_job_fingerprint(title, organization, job_location or location, description)
    inferred_type = _infer_linkedin_opportunity_type(title, "", keyword)

    return {
        "title": title,
        "description": description,
        "description_quality": description_quality,
        "source_reliability_reason": SOURCE_RELIABILITY_REASON,
        "organization": organization,
        "company_name": organization,
        "company_logo": company_logo or None,
        "logo_url": company_logo or None,
        "location": job_location or _clean_text(location),
        "type_opportunite": inferred_type,
        "opportunity_type": inferred_type,
        "statut": "ACTIVE",
        "status": "ACTIVE",
        "publication_date": publication_date,
        "date_publication": publication_date,
        "date_limite": None,
        "deadline": None,
        "url": canonical_url,
        "source_item_url": canonical_url,
        "apply_url": canonical_url,
        "source_listing_url": source_listing_url,
        "source_record_id": job_id or None,
        "external_id": fingerprint or None,
        "source_name": "LinkedIn",
        "source_url": LINKEDIN_SOURCE_URL,
        "source_type": "SITE_EMPLOI",
        "source_reliability": SOURCE_RELIABILITY,
    }


def scrape_linkedin_jobs(
    keyword=DEFAULT_KEYWORD,
    location=DEFAULT_LOCATION,
    pages=DEFAULT_MAX_PAGES,
    timeout=DEFAULT_TIMEOUT,
    min_delay=DEFAULT_MIN_DELAY,
    max_delay=DEFAULT_MAX_DELAY,
    fetch_details=False,
):
    """
    Experimental LinkedIn source:
    - public guest endpoint only
    - fail-safe: never raises to the caller
    - detail extraction is opt-in because LinkedIn detail pages are rate-limit sensitive
    """
    try:
        max_pages = max(1, int(pages or DEFAULT_MAX_PAGES))
    except (TypeError, ValueError):
        max_pages = DEFAULT_MAX_PAGES
    if max_pages > MAX_PAGES_SAFE:
        logger.info(
            "LinkedIn pagination capped at pages=%s (requested=%s max_offset=%s page_size=%s).",
            MAX_PAGES_SAFE,
            max_pages,
            MAX_OFFSET,
            PAGE_SIZE,
        )
        max_pages = MAX_PAGES_SAFE
    try:
        timeout = max(1, int(timeout or DEFAULT_TIMEOUT))
    except (TypeError, ValueError):
        timeout = DEFAULT_TIMEOUT
    try:
        min_delay = max(0.0, float(min_delay if min_delay is not None else DEFAULT_MIN_DELAY))
    except (TypeError, ValueError):
        min_delay = DEFAULT_MIN_DELAY
    try:
        max_delay = max(min_delay, float(max_delay if max_delay is not None else DEFAULT_MAX_DELAY))
    except (TypeError, ValueError):
        max_delay = max(min_delay, DEFAULT_MAX_DELAY)

    session = _build_session()
    search_keyword = _clean_text(keyword)
    search_location = _clean_text(location) or DEFAULT_LOCATION
    results = []
    seen_keys = set()
    pages_succeeded = 0
    pages_failed = 0
    details_succeeded = 0
    details_failed = 0
    metrics = {
        "empty_title": 0,
        "empty_description": 0,
        "duplicates_detected": 0,
    }

    try:
        for page_index in range(max_pages):
            start = page_index * PAGE_SIZE
            if start >= MAX_OFFSET:
                logger.info("LinkedIn pagination stopped at start=%s (limit reached).", start)
                break
            params = {
                "keywords": search_keyword,
                "location": search_location,
                "start": start,
            }
            public_params = {
                "keywords": search_keyword,
                "location": search_location,
                "geoId": "",
                "trk": "public_jobs_jobs-search-bar_search-submit",
                "position": "1",
                "pageNum": str(page_index),
            }
            source_listing_url = f"{LINKEDIN_SEARCH_PAGE_URL}?{urlencode(public_params)}"

            try:
                _rate_limit_delay(min_delay=min_delay, max_delay=max_delay)
                response = session.get(
                    LINKEDIN_PUBLIC_SEARCH_URL,
                    params=params,
                    timeout=timeout,
                )
                response.raise_for_status()
            except requests.RequestException as exc:
                pages_failed += 1
                status_code = getattr(getattr(exc, "response", None), "status_code", None)
                if status_code == 400:
                    logger.warning(
                        "LinkedIn pagination blocked at start=%s (status code 400); stopping.",
                        params["start"],
                    )
                    break

                logger.warning(
                    "LinkedIn experimental scrape failed for page=%s start=%s keyword=%r location=%r: %s",
                    page_index + 1,
                    params["start"],
                    search_keyword,
                    search_location,
                    exc,
                )
                continue

            soup = BeautifulSoup(response.text, "html.parser")
            cards = _extract_listing_cards(soup)
            if not cards:
                logger.info(
                    "LinkedIn experimental page=%s returned no cards, stopping pagination early.",
                    page_index + 1,
                )
                break

            page_added = 0
            for card in cards:
                parsed = _parse_job_card(
                    card,
                    keyword=search_keyword,
                    location=search_location,
                    source_listing_url=source_listing_url,
                    metrics=metrics,
                )
                if not parsed:
                    continue

                if fetch_details:
                    detail_data = _fetch_detail_data(
                        session,
                        parsed["url"],
                        timeout=timeout,
                        min_delay=min_delay,
                        max_delay=max_delay,
                    )
                    if detail_data:
                        details_succeeded += 1
                        parsed = _merge_detail_data(parsed, detail_data, keyword=search_keyword)
                    else:
                        details_failed += 1

                dedup_key = parsed.get("external_id") or parsed.get("source_record_id") or parsed["url"]
                if dedup_key in seen_keys:
                    metrics["duplicates_detected"] += 1
                    continue
                seen_keys.add(dedup_key)

                results.append(parsed)
                page_added += 1

            pages_succeeded += 1
            logger.info(
                "LinkedIn experimental page=%s scraped=%s jobs (total=%s)",
                page_index + 1,
                page_added,
                len(results),
            )

        requested_pages = max_pages
        success_rate = (pages_succeeded / requested_pages) if requested_pages else 0.0
        logger.info(
            (
                "LinkedIn experimental scrape finished: jobs=%s, pages_requested=%s, "
                "pages_succeeded=%s, pages_failed=%s, details_succeeded=%s, "
                "details_failed=%s, success_rate=%.2f, empty_title=%s, "
                "empty_description=%s, duplicates_detected=%s"
            ),
            len(results),
            requested_pages,
            pages_succeeded,
            pages_failed,
            details_succeeded,
            details_failed,
            success_rate,
            metrics["empty_title"],
            metrics["empty_description"],
            metrics["duplicates_detected"],
        )
        return results
    except Exception:
        logger.exception("LinkedIn experimental scraper failed unexpectedly")
        return []
    finally:
        session.close()


class LinkedInScraper(BaseOpportunityScraper):
    source_name = "LinkedIn"
    source_url = LINKEDIN_SOURCE_URL
    source_type = "SITE_EMPLOI"

    def __init__(
        self,
        keyword=DEFAULT_KEYWORD,
        location=DEFAULT_LOCATION,
        pages=DEFAULT_MAX_PAGES,
        max_pages=None,
        timeout=DEFAULT_TIMEOUT,
        min_delay=DEFAULT_MIN_DELAY,
        max_delay=DEFAULT_MAX_DELAY,
        fetch_details=False,
    ):
        self.keyword = _clean_text(keyword)
        self.location = _clean_text(location) or DEFAULT_LOCATION
        self.pages = max_pages if max_pages is not None else pages
        self.timeout = timeout
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.fetch_details = bool(fetch_details)

    def fetch_raw_records(self):
        return scrape_linkedin_jobs(
            self.keyword,
            self.location,
            pages=self.pages,
            timeout=self.timeout,
            min_delay=self.min_delay,
            max_delay=self.max_delay,
            fetch_details=self.fetch_details,
        )
