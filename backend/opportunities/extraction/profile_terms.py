from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any, Iterable

from opportunities.models import ProfileSuggestionType, TypeOpportunite
from opportunities.normalization.industries import (
    INTEREST_ALIAS_MAP,
    KNOWN_INTEREST_KEYS,
    canonicalize_industry,
    industry_alias_keys_for,
    industry_language,
    is_known_industry,
    normalize_industries,
)
from opportunities.normalization.text import (
    clean_display_text,
    detect_language,
    dedupe_texts,
    normalize_lookup_key,
    title_case_latin,
)


ROLE_MAX_LENGTH = 120
SKILL_MAX_LENGTH = 80
MIN_NORMALIZED_CHARS = 3

ROLE_ALLOWED_TYPES = {TypeOpportunite.EMPLOI, TypeOpportunite.STAGE}


def _key_set(values: Iterable[str]) -> set[str]:
    return {key for value in values if (key := normalize_lookup_key(value))}


SKILL_ALIAS_PAIRS: tuple[tuple[str, str], ...] = (
    ("aws", "AWS"),
    ("amazon web services", "AWS"),
    ("azure", "Azure"),
    ("microsoft azure", "Azure"),
    ("gcp", "Google Cloud"),
    ("google cloud", "Google Cloud"),
    ("google cloud platform", "Google Cloud"),
    ("react", "React"),
    ("reactjs", "React"),
    ("react.js", "React"),
    ("react js", "React"),
    ("vue", "Vue.js"),
    ("vuejs", "Vue.js"),
    ("vue.js", "Vue.js"),
    ("vue js", "Vue.js"),
    ("angular", "Angular"),
    ("nextjs", "Next.js"),
    ("next.js", "Next.js"),
    ("next js", "Next.js"),
    ("tailwind", "Tailwind CSS"),
    ("tailwindcss", "Tailwind CSS"),
    ("tailwind css", "Tailwind CSS"),
    ("node", "Node.js"),
    ("nodejs", "Node.js"),
    ("node.js", "Node.js"),
    ("node js", "Node.js"),
    ("js", "JavaScript"),
    ("javascript", "JavaScript"),
    ("java script", "JavaScript"),
    ("ts", "TypeScript"),
    ("typescript", "TypeScript"),
    ("type script", "TypeScript"),
    ("py", "Python"),
    ("python", "Python"),
    ("css", "CSS"),
    ("css3", "CSS"),
    ("html", "HTML"),
    ("html5", "HTML"),
    ("django", "Django"),
    ("flask", "Flask"),
    ("fastapi", "FastAPI"),
    ("java", "Java"),
    ("c#", "C#"),
    ("c sharp", "C#"),
    ("c++", "C++"),
    ("sql", "SQL"),
    ("mysql", "MySQL"),
    ("postgres", "PostgreSQL"),
    ("postgresql", "PostgreSQL"),
    ("postgre sql", "PostgreSQL"),
    ("mongodb", "MongoDB"),
    ("mongo db", "MongoDB"),
    ("redis", "Redis"),
    ("kafka", "Kafka"),
    ("terraform", "Terraform"),
    ("power bi", "Power BI"),
    ("excel", "Excel"),
    ("microsoft excel", "Excel"),
    ("sap", "SAP"),
    ("sage", "Sage"),
    ("autocad", "AutoCAD"),
    ("docker", "Docker"),
    ("kubernetes", "Kubernetes"),
    ("k8s", "Kubernetes"),
    ("git", "Git"),
    ("github", "GitHub"),
    ("communication", "Communication"),
    ("vente", "Vente"),
    ("sales", "Vente"),
    ("marketing", "Marketing"),
    ("finance", "Finance"),
    ("comptabilite", "Comptabilité"),
    ("comptabilité", "Comptabilité"),
    ("negociation", "Négociation"),
    ("négociation", "Négociation"),
    ("management", "Management"),
    ("gestion", "Gestion"),
    ("maintenance", "Maintenance"),
    ("qualite", "Qualité"),
    ("qualité", "Qualité"),
    ("controle qualite", "Contrôle qualité"),
    ("contrôle qualité", "Contrôle qualité"),
    ("btp", "BTP"),
    ("transport", "Transport"),
    ("logistique", "Logistique"),
    ("formation", "Formation"),
)

ROLE_ALIAS_PAIRS: tuple[tuple[str, str], ...] = (
    ("front end developer", "Frontend Developer"),
    ("front-end developer", "Frontend Developer"),
    ("frontend developer", "Frontend Developer"),
    ("frontend engineer", "Frontend Developer"),
    ("front end engineer", "Frontend Developer"),
    ("front-end engineer", "Frontend Developer"),
    ("developpeur frontend", "Frontend Developer"),
    ("developpeur front end", "Frontend Developer"),
    ("developpeur front-end", "Frontend Developer"),
    ("développeur frontend", "Frontend Developer"),
    ("développeur front end", "Frontend Developer"),
    ("développeur front-end", "Frontend Developer"),
    ("back end developer", "Backend Developer"),
    ("back-end developer", "Backend Developer"),
    ("backend developer", "Backend Developer"),
    ("backend engineer", "Backend Developer"),
    ("back end engineer", "Backend Developer"),
    ("back-end engineer", "Backend Developer"),
    ("developpeur backend", "Backend Developer"),
    ("developpeur back end", "Backend Developer"),
    ("developpeur back-end", "Backend Developer"),
    ("développeur backend", "Backend Developer"),
    ("développeur back end", "Backend Developer"),
    ("développeur back-end", "Backend Developer"),
    ("full stack developer", "Full Stack Developer"),
    ("full-stack developer", "Full Stack Developer"),
    ("fullstack developer", "Full Stack Developer"),
    ("full stack engineer", "Full Stack Developer"),
    ("full-stack engineer", "Full Stack Developer"),
    ("fullstack engineer", "Full Stack Developer"),
    ("developpeur full stack", "Full Stack Developer"),
    ("developpeur fullstack", "Full Stack Developer"),
    ("developpeur full-stack", "Full Stack Developer"),
    ("développeur full stack", "Full Stack Developer"),
    ("développeur fullstack", "Full Stack Developer"),
    ("développeur full-stack", "Full Stack Developer"),
    ("software engineer", "Software Engineer"),
    ("software developer", "Software Engineer"),
    ("ingenieur logiciel", "Software Engineer"),
    ("ingénieur logiciel", "Software Engineer"),
    ("developpeur logiciel", "Software Engineer"),
    ("développeur logiciel", "Software Engineer"),
    ("web developer", "Web Developer"),
    ("developpeur web", "Web Developer"),
    ("développeur web", "Web Developer"),
    ("data engineer", "Data Engineer"),
    ("data analyst", "Data Analyst"),
    ("business analyst", "Business Analyst"),
    ("quality engineer", "Quality Engineer"),
    ("ingenieur qualite", "Quality Engineer"),
    ("ingénieur qualité", "Quality Engineer"),
    ("graphic designer", "Graphic Designer"),
    ("ui ux designer", "UI/UX Designer"),
    ("ux ui designer", "UI/UX Designer"),
    ("comptable", "Comptable"),
    ("accountant", "Accountant"),
    ("commercial", "Commercial"),
    ("sales executive", "Sales Executive"),
    ("customer success manager", "Customer Success Manager"),
    ("chef de projet", "Chef de Projet"),
    ("project manager", "Project Manager"),
    ("product manager", "Product Manager"),
    ("product owner", "Product Owner"),
    ("scrum master", "Scrum Master"),
    ("مطور واجهات", "Frontend Developer"),
    ("مطوّر واجهات", "Frontend Developer"),
    ("تطوير الواجهات", "Frontend Developer"),
    ("متدرب تطوير واجهات", "Frontend Developer"),
    ("تربص تطوير واجهات", "Frontend Developer"),
    ("مطور ويب", "Web Developer"),
    ("مطوّر ويب", "Web Developer"),
    ("مهندس برمجيات", "Software Engineer"),
    ("مهندس برمجة", "Software Engineer"),
    ("مطور برمجيات", "Software Engineer"),
    ("متدرب برمجة", "Software Engineer"),
    ("تربص في البرمجة", "Software Engineer"),
)


def _normalize_alias_pairs(pairs: Iterable[tuple[str, str]]) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for alias, canonical in pairs:
        alias_key = normalize_lookup_key(alias)
        canonical_key = normalize_lookup_key(canonical)
        if alias_key:
            aliases[alias_key] = canonical
        if canonical_key:
            aliases.setdefault(canonical_key, canonical)
    return aliases


SKILL_ALIAS_MAP = _normalize_alias_pairs(SKILL_ALIAS_PAIRS)
ROLE_ALIAS_MAP = _normalize_alias_pairs(ROLE_ALIAS_PAIRS)

KNOWN_SKILL_KEYS = set(SKILL_ALIAS_MAP) | _key_set(SKILL_ALIAS_MAP.values())
KNOWN_ROLE_KEYS = set(ROLE_ALIAS_MAP) | _key_set(ROLE_ALIAS_MAP.values())

PROFILE_TERM_HARD_SKILL = "HARD_SKILL"
PROFILE_TERM_ROLE = "ROLE"
PROFILE_TERM_DOMAIN = "DOMAIN"
PROFILE_TERM_SOFT_TOPIC = "SOFT_TOPIC"
PROFILE_TERM_NOISE = "NOISE"

DOMAIN_TERM_KEYS = _key_set(
    {
        "sante",
        "santé",
        "health",
        "healthcare",
        "machines",
        "machine",
        "commercial",
        "commerce",
        "sales",
        "industrie",
        "industry",
        "secteur",
        "sector",
        "transport",
        "logistique",
        "finance",
        "marketing",
    }
) | set(INTEREST_ALIAS_MAP) | _key_set(INTEREST_ALIAS_MAP.values())

SOFT_TOPIC_TERM_KEYS = _key_set(
    {
        "communication",
        "management",
        "gestion",
        "formation",
        "maintenance",
        "qualite",
        "qualité",
        "vente",
        "negociation",
        "négociation",
        "leadership",
        "organisation",
    }
)

NOISE_PROFILE_TERM_KEYS = _key_set(
    {
        "mission",
        "missions",
        "poste",
        "postes",
        "profil",
        "profile",
        "candidate",
        "candidat",
        "candidats",
        "h f",
        "f h",
        "m f",
        "hf",
        "fh",
        "remote",
        "urgent",
    }
)

NON_HARD_SKILL_KEYS = DOMAIN_TERM_KEYS | SOFT_TOPIC_TERM_KEYS | NOISE_PROFILE_TERM_KEYS

SKILL_BOUNDARY_ALIASES = tuple(
    sorted(SKILL_ALIAS_MAP.items(), key=lambda item: len(item[0]), reverse=True)
)

GENERIC_ROLE_KEYS = _key_set(
    {
        "developer",
        "developpeur",
        "développeur",
        "engineer",
        "ingenieur",
        "ingénieur",
        "manager",
        "senior",
        "junior",
        "consultant",
        "specialist",
        "spécialiste",
        "technician",
        "technicien",
        "responsable",
    }
)

PARTIAL_ROLE_FRAGMENT_KEYS = _key_set(
    {
        "front",
        "frontend",
        "front end",
        "back",
        "backend",
        "back end",
        "fullstack",
        "full stack",
        "dev",
        "software",
        "web",
    }
)

ROLE_LEVEL_TOKENS = _key_set(
    {
        "senior",
        "junior",
        "middle",
        "mid level",
        "graduate",
        "lead",
        "principal",
        "debutant",
        "débutant",
        "stagiaire",
        "stage",
        "intern",
        "internship",
        "trainee",
        "alternance",
        "متدرب",
        "متدربة",
        "تربص",
    }
)

ROLE_SUFFIX_TOKENS = _key_set(
    {
        "tunis",
        "sfax",
        "sousse",
        "ariana",
        "ben arous",
        "nabeul",
        "monastir",
        "kairouan",
        "gabes",
        "gabès",
        "gafsa",
        "medenine",
        "médenine",
        "bizerte",
        "rades",
        "radès",
        "remote",
        "tunisia",
        "tunisie",
        "international",
    }
)

LOCATION_ONLY_KEYS = ROLE_SUFFIX_TOKENS | _key_set(
    {
        "france",
        "usa",
        "united states",
        "etats unis",
        "états unis",
        "paris",
        "lyon",
        "marseille",
        "casablanca",
        "rabat",
        "alger",
    }
)

OPPORTUNITY_NOISE_KEYS = _key_set(
    {
        "urgent",
        "hiring",
        "apply now",
        "remote",
        "recrutement",
        "offre emploi",
        "offre d emploi",
        "job offer",
        "job",
        "emploi",
        "poste vacant",
        "candidature",
        "rejoignez nous",
        "appel offres",
        "avis consultation",
        "acquisition",
        "equipements",
        "équipements",
        "travaux",
        "amenagement",
        "aménagement",
        "maintenance des pistes",
        "consultation",
        "اقتناء",
        "اشغال",
        "تهيئة",
        "صيانة",
        "دراسة",
    }
)

STOPWORD_TOKENS = _key_set(
    {
        "a",
        "an",
        "and",
        "or",
        "of",
        "for",
        "to",
        "the",
        "in",
        "on",
        "with",
        "de",
        "des",
        "du",
        "la",
        "le",
        "les",
        "et",
        "ou",
        "pour",
        "dans",
        "avec",
        "en",
        "في",
        "من",
        "الى",
        "على",
        "و",
        "ال",
    }
)

COMPANY_SUFFIX_KEYS = _key_set(
    {
        "inc",
        "llc",
        "ltd",
        "limited",
        "sarl",
        "sa",
        "sas",
        "gmbh",
        "company",
        "corp",
        "corporation",
        "group",
        "groupe",
        "startup",
        "start up",
        "société",
        "societe",
        "entreprise",
    }
)

TITLE_CODE_RE = re.compile(r"\((?:h/f|f/h|m/f|h\s*f|f\s*h|[a-z]-[a-z0-9]{4,})\)", re.IGNORECASE)
TITLE_GENDER_RE = re.compile(r"\b(?:h/f|f/h|m/f|h\s*f|f\s*h)\b", re.IGNORECASE)
MULTI_SEPARATOR_RE = re.compile(r"\s+[-–—|]\s+")


@dataclass(frozen=True)
class ExtractedProfileTerm:
    term_type: str
    canonical: str
    aliases: tuple[str, ...] = field(default_factory=tuple)
    confidence: float = 0.0
    language: str = "unknown"
    source: str = ""


def _term_type_value(value: str) -> str:
    return value.value if hasattr(value, "value") else str(value)


def canonicalize_known_skill(value: Any) -> str | None:
    return SKILL_ALIAS_MAP.get(normalize_lookup_key(value))


def canonicalize_known_role(value: Any) -> str | None:
    key = normalize_lookup_key(value)
    if not key:
        return None
    return ROLE_ALIAS_MAP.get(key) or ROLE_ALIAS_MAP.get(_remove_role_levels(key))


def is_known_skill(value: Any) -> bool:
    return normalize_lookup_key(value) in KNOWN_SKILL_KEYS


def is_known_role(value: Any) -> bool:
    key = normalize_lookup_key(value)
    return key in KNOWN_ROLE_KEYS or bool(canonicalize_known_role(key))


def classify_profile_term(value: Any) -> str:
    key = normalize_lookup_key(value)
    if not key:
        return PROFILE_TERM_NOISE

    if key in NOISE_PROFILE_TERM_KEYS or key in OPPORTUNITY_NOISE_KEYS:
        return PROFILE_TERM_NOISE
    if key in LOCATION_ONLY_KEYS:
        return PROFILE_TERM_NOISE
    if key in KNOWN_ROLE_KEYS or canonicalize_known_role(key):
        return PROFILE_TERM_ROLE
    if key in DOMAIN_TERM_KEYS:
        return PROFILE_TERM_DOMAIN
    if key in KNOWN_INTEREST_KEYS or canonicalize_industry(key):
        return PROFILE_TERM_DOMAIN
    if key in SOFT_TOPIC_TERM_KEYS:
        return PROFILE_TERM_SOFT_TOPIC
    if key in KNOWN_SKILL_KEYS and key not in NON_HARD_SKILL_KEYS:
        return PROFILE_TERM_HARD_SKILL
    return ""


def _compact_length(key: str) -> int:
    return len(key.replace(" ", ""))


def _has_text_signal(key: str) -> bool:
    return any(char.isalpha() for char in key)


def _is_numeric_heavy(key: str) -> bool:
    compact = key.replace(" ", "").replace("+", "").replace("#", "")
    if not compact:
        return False
    digits = sum(char.isdigit() for char in compact)
    letters = sum(char.isalpha() for char in compact)
    return bool(digits) and (digits >= max(letters, 1) or digits / len(compact) > 0.35)


def _is_stopword_only(key: str) -> bool:
    tokens = key.split()
    return bool(tokens) and all(token in STOPWORD_TOKENS for token in tokens)


def _looks_like_company_name(key: str, organization_keys: set[str]) -> bool:
    if key in organization_keys:
        return True
    tokens = key.split()
    return 1 < len(tokens) <= 5 and bool(COMPANY_SUFFIX_KEYS.intersection(tokens))


def _opportunity_company_keys(opportunity: Any) -> set[str]:
    names = [
        getattr(opportunity, "organisation_nom", ""),
        getattr(opportunity, "company_name", ""),
    ]
    extra_data = getattr(opportunity, "extra_data", None)
    if isinstance(extra_data, dict):
        names.extend(
            str(extra_data.get(key, ""))
            for key in (
                "company",
                "company_name",
                "organisation",
                "organization",
                "organisation_nom",
                "hiring_company",
            )
        )
    return _key_set(names)


def _term_rejection_reason(
    value: Any,
    *,
    term_type: str,
    organization_keys: set[str] | None = None,
) -> str | None:
    term_type = _term_type_value(term_type)
    text = clean_display_text(value)
    key = normalize_lookup_key(text)
    if not text or not key:
        return "empty"

    category = classify_profile_term(key)

    if (
        term_type == ProfileSuggestionType.SKILL.value
        and key in SKILL_ALIAS_MAP
        and category == PROFILE_TERM_HARD_SKILL
    ):
        return None
    if term_type == ProfileSuggestionType.ROLE.value and canonicalize_known_role(key):
        return None
    if term_type == ProfileSuggestionType.INTEREST.value and canonicalize_industry(key):
        return None

    if not _has_text_signal(key):
        return "punctuation"
    if _compact_length(key) < MIN_NORMALIZED_CHARS:
        return "too_short"
    if _is_numeric_heavy(key):
        return "numeric_heavy"
    if _is_stopword_only(key):
        return "stopword_only"
    if key in OPPORTUNITY_NOISE_KEYS:
        return "opportunity_noise"
    if key in LOCATION_ONLY_KEYS:
        return "location_only"
    if _looks_like_company_name(key, organization_keys or set()):
        return "company_name"

    if term_type == ProfileSuggestionType.ROLE.value:
        if category == PROFILE_TERM_HARD_SKILL or key in KNOWN_SKILL_KEYS:
            return "known_skill"
        if category in {PROFILE_TERM_DOMAIN, PROFILE_TERM_SOFT_TOPIC, PROFILE_TERM_NOISE}:
            return category.lower()
        if key in GENERIC_ROLE_KEYS:
            return "generic_role"
        if key in PARTIAL_ROLE_FRAGMENT_KEYS:
            return "role_fragment"
        if key in ROLE_LEVEL_TOKENS:
            return "role_level"
    elif term_type == ProfileSuggestionType.SKILL.value:
        if category == PROFILE_TERM_ROLE or key in KNOWN_ROLE_KEYS or canonicalize_known_role(key):
            return "known_role"
        if category in {PROFILE_TERM_DOMAIN, PROFILE_TERM_SOFT_TOPIC, PROFILE_TERM_NOISE}:
            return category.lower()
        if key in GENERIC_ROLE_KEYS:
            return "generic_role"
    elif term_type == ProfileSuggestionType.INTEREST.value:
        if category == PROFILE_TERM_HARD_SKILL or key in KNOWN_SKILL_KEYS:
            return "known_skill"
        if category == PROFILE_TERM_ROLE or key in KNOWN_ROLE_KEYS or canonicalize_known_role(key):
            return "known_role"
        if category in {PROFILE_TERM_SOFT_TOPIC, PROFILE_TERM_NOISE}:
            return category.lower()
        if not canonicalize_industry(key):
            return "unknown_interest"

    return None


def is_rejected_profile_term(
    term_type: str,
    value: Any,
    *,
    organization_names: Iterable[str] = (),
) -> bool:
    return _term_rejection_reason(
        value,
        term_type=term_type,
        organization_keys=_key_set(organization_names),
    ) is not None


def _remove_key_phrase(value: str, phrase_key: str) -> str:
    if not phrase_key:
        return value
    return re.sub(rf"(^|\s){re.escape(phrase_key)}(\s|$)", " ", value)


def _remove_role_levels(value: str) -> str:
    key = normalize_lookup_key(value)
    for token in sorted(ROLE_LEVEL_TOKENS, key=len, reverse=True):
        key = _remove_key_phrase(key, token)
    return re.sub(r"\s+", " ", key).strip()


def _role_is_skill_specialization(key: str) -> bool:
    remaining = key
    touched = False
    for skill_key in sorted(KNOWN_SKILL_KEYS, key=len, reverse=True):
        next_value = _remove_key_phrase(remaining, skill_key)
        if next_value != remaining:
            touched = True
            remaining = next_value
    if not touched:
        return False

    remaining_tokens = [
        token
        for token in normalize_lookup_key(remaining).split()
        if token not in GENERIC_ROLE_KEYS and token not in ROLE_LEVEL_TOKENS
    ]
    return not remaining_tokens


def _strip_role_title_noise(title: str) -> str:
    text = TITLE_CODE_RE.sub(" ", title)
    text = TITLE_GENDER_RE.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip(" -:;,.")
    return text


def _remove_opportunity_noise(value: str) -> str:
    key = normalize_lookup_key(value)
    for noise_key in sorted(OPPORTUNITY_NOISE_KEYS, key=len, reverse=True):
        key = _remove_key_phrase(key, noise_key)
    return re.sub(r"\s+", " ", key).strip()


def _clean_role_title(value: Any, *, organization_keys: set[str] | None = None) -> str:
    title = clean_display_text(value, max_length=ROLE_MAX_LENGTH)
    if not title:
        return ""

    title = _strip_role_title_noise(title)
    parts = [part.strip(" -:;,.") for part in MULTI_SEPARATOR_RE.split(title) if part.strip()]
    while len(parts) > 1 and normalize_lookup_key(parts[-1]) in (ROLE_SUFFIX_TOKENS | OPPORTUNITY_NOISE_KEYS):
        parts.pop()
    title = parts[0] if parts else title

    key = normalize_lookup_key(title)
    key = _remove_opportunity_noise(key)
    if not key:
        return ""

    key_without_levels = _remove_role_levels(key)
    mapped = ROLE_ALIAS_MAP.get(key_without_levels) or ROLE_ALIAS_MAP.get(key)
    if mapped:
        return mapped

    candidate_key = key_without_levels or key
    if len(candidate_key.split()) > 8:
        return ""
    if _role_is_skill_specialization(candidate_key):
        return ""
    if _term_rejection_reason(
        candidate_key,
        term_type=ProfileSuggestionType.ROLE,
        organization_keys=organization_keys,
    ):
        return ""

    return title_case_latin(candidate_key)


def extract_role_terms(opportunity: Any) -> list[ExtractedProfileTerm]:
    opportunity_type = getattr(opportunity, "type_opportunite", "")
    if opportunity_type not in ROLE_ALLOWED_TYPES:
        return []

    raw_title = clean_display_text(getattr(opportunity, "titre", ""), max_length=ROLE_MAX_LENGTH)
    organization_keys = _opportunity_company_keys(opportunity)
    canonical = _clean_role_title(raw_title, organization_keys=organization_keys)
    if not canonical:
        return []

    aliases = tuple(dedupe_texts([raw_title, canonical]))
    return [
        ExtractedProfileTerm(
            term_type=ProfileSuggestionType.ROLE,
            canonical=canonical,
            aliases=aliases,
            confidence=0.9 if canonical != raw_title else 0.78,
            language=detect_language(raw_title),
            source="title",
        )
    ]


def _canonical_from_alias(value: str, alias_map: dict[str, str]) -> str:
    key = normalize_lookup_key(value)
    mapped = alias_map.get(key)
    if mapped:
        return mapped
    return title_case_latin(clean_display_text(value, max_length=160))


def _clean_skill(value: Any, *, organization_keys: set[str] | None = None) -> str:
    text = clean_display_text(value, max_length=SKILL_MAX_LENGTH)
    if not text:
        return ""
    key = normalize_lookup_key(text)
    mapped = SKILL_ALIAS_MAP.get(key)
    if mapped and not _term_rejection_reason(
        key,
        term_type=ProfileSuggestionType.SKILL,
        organization_keys=organization_keys,
    ):
        return mapped
    if len(key.split()) > 4:
        return ""
    if _term_rejection_reason(
        key,
        term_type=ProfileSuggestionType.SKILL,
        organization_keys=organization_keys,
    ):
        return ""
    return _canonical_from_alias(text, SKILL_ALIAS_MAP)


def _extract_structured_skills(opportunity: Any) -> Iterable[ExtractedProfileTerm]:
    organization_keys = _opportunity_company_keys(opportunity)
    for raw_skill in getattr(opportunity, "skills", None) or []:
        canonical = _clean_skill(raw_skill, organization_keys=organization_keys)
        if not canonical:
            continue
        alias = clean_display_text(raw_skill, max_length=SKILL_MAX_LENGTH)
        yield ExtractedProfileTerm(
            term_type=ProfileSuggestionType.SKILL,
            canonical=canonical,
            aliases=tuple(dedupe_texts([alias, canonical])),
            confidence=0.95,
            language=detect_language(alias),
            source="structured_skills",
        )


def _blob_contains_alias(blob_key: str, alias_key: str) -> bool:
    if not alias_key:
        return False
    return bool(re.search(rf"(?<!\w){re.escape(alias_key)}(?!\w)", blob_key))


def _extract_alias_skills(opportunity: Any) -> Iterable[ExtractedProfileTerm]:
    parts = [
        getattr(opportunity, "titre", ""),
        getattr(opportunity, "description", ""),
    ]
    extra_data = getattr(opportunity, "extra_data", None)
    if isinstance(extra_data, dict):
        parts.append(extra_data.get("job_qualifications", ""))
        parts.append(extra_data.get("company_sector", ""))

    blob = " ".join(clean_display_text(part) for part in parts if part)
    blob_key = normalize_lookup_key(blob)
    if not blob_key:
        return

    for alias_key, canonical in SKILL_BOUNDARY_ALIASES:
        if is_rejected_profile_term(ProfileSuggestionType.SKILL, canonical):
            continue
        if _blob_contains_alias(blob_key, alias_key):
            yield ExtractedProfileTerm(
                term_type=ProfileSuggestionType.SKILL,
                canonical=canonical,
                aliases=tuple(dedupe_texts([canonical, alias_key])),
                confidence=0.74,
                language=detect_language(blob),
                source="text_alias",
            )


def extract_skill_terms(opportunity: Any) -> list[ExtractedProfileTerm]:
    terms = list(_extract_structured_skills(opportunity))
    structured_keys = {normalize_lookup_key(term.canonical) for term in terms}

    for term in _extract_alias_skills(opportunity):
        if normalize_lookup_key(term.canonical) in structured_keys:
            continue
        terms.append(term)

    return terms


def extract_interest_terms(opportunity: Any) -> list[ExtractedProfileTerm]:
    extra_data = getattr(opportunity, "extra_data", None)
    company_sector = extra_data.get("company_sector") if isinstance(extra_data, dict) else ""
    raw_values = [
        getattr(opportunity, "normalized_industries", None),
        company_sector,
        getattr(opportunity, "company_sector", ""),
    ]
    canonical_values = normalize_industries(raw_values)

    terms: list[ExtractedProfileTerm] = []
    for canonical in canonical_values:
        aliases = dedupe_texts(
            [
                canonical,
                company_sector,
                *industry_alias_keys_for(canonical),
            ]
        )
        terms.append(
            ExtractedProfileTerm(
                term_type=ProfileSuggestionType.INTEREST,
                canonical=canonical,
                aliases=tuple(aliases),
                confidence=0.96 if getattr(opportunity, "normalized_industries", None) else 0.84,
                language=industry_language(company_sector or canonical),
                source="company_sector",
            )
        )
    return terms


def extract_profile_terms(opportunity: Any) -> list[ExtractedProfileTerm]:
    role_terms = extract_role_terms(opportunity)
    skill_terms = extract_skill_terms(opportunity)
    interest_terms = extract_interest_terms(opportunity)
    skill_keys = {normalize_lookup_key(term.canonical) for term in skill_terms}
    role_keys = {normalize_lookup_key(term.canonical) for term in role_terms}
    role_terms = [
        term
        for term in role_terms
        if normalize_lookup_key(term.canonical) not in skill_keys
        and normalize_lookup_key(term.canonical) not in KNOWN_SKILL_KEYS
    ]
    interest_terms = [
        term
        for term in interest_terms
        if normalize_lookup_key(term.canonical) not in skill_keys
        and normalize_lookup_key(term.canonical) not in role_keys
        and not is_known_skill(term.canonical)
        and not is_known_role(term.canonical)
    ]
    return [*role_terms, *skill_terms, *interest_terms]


__all__ = [
    "ExtractedProfileTerm",
    "INTEREST_ALIAS_MAP",
    "KNOWN_INTEREST_KEYS",
    "KNOWN_ROLE_KEYS",
    "KNOWN_SKILL_KEYS",
    "ROLE_ALIAS_MAP",
    "SKILL_ALIAS_MAP",
    "canonicalize_industry",
    "canonicalize_known_role",
    "canonicalize_known_skill",
    "classify_profile_term",
    "extract_profile_terms",
    "extract_interest_terms",
    "extract_role_terms",
    "extract_skill_terms",
    "is_known_industry",
    "is_known_role",
    "is_known_skill",
    "is_rejected_profile_term",
]
