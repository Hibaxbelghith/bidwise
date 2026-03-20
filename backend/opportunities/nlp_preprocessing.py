import html
import logging
import re
import unicodedata
from typing import Any, Dict


logger = logging.getLogger(__name__)


MIN_TEXT_LENGTH = 30
MAX_TEXT_LENGTH = 1200

HTML_TAG_RE = re.compile(r"<[^>]+>")
URL_RE = re.compile(r"(https?://\S+|www\.\S+)", re.IGNORECASE)
EMAIL_RE = re.compile(r"\b[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}\b", re.IGNORECASE)
WHITESPACE_RE = re.compile(r"\s+")
REPEATED_PUNCT_RE = re.compile(r"([!?.,;:])\1+")
DATE_RE = re.compile(r"\b(\d{2}/\d{2}/\d{4})\b")
LOCATION_MARKER_RE = re.compile(r"\b(?:nat|rep|inter)\s*\./\s*([a-z]{2,5})\b", re.IGNORECASE)
LEADING_CODE_RE = re.compile(r"^\s*\d+\s+[a-z]{1,3}\b", re.IGNORECASE)
TIMESTAMP_RE = re.compile(r"\b\d{2}:\d{2}:\d{2}\b")
PARTIAL_DATE_FRAGMENT_RE = re.compile(r"\b\d{1,2}/\b")

BOILERPLATE_PATTERNS = [
    re.compile(r"\bpostuler\b", re.IGNORECASE),
    re.compile(r"\bcliquez ici\b", re.IGNORECASE),
    re.compile(r"\benvoyer\s+cv\b", re.IGNORECASE),
    re.compile(r"\benvoyer\s+votre\s+cv\b", re.IGNORECASE),
    re.compile(r"\bapply now\b", re.IGNORECASE),
    re.compile(r"\bclick here\b", re.IGNORECASE),
]

TENDER_TYPE_PATTERNS = [
    (re.compile(r"\bavis\s+de\s+consultation\b"), "avis de consultation"),
    (re.compile(r"\bappel\s+d['\s]offres\b"), "appel d offres"),
    (re.compile(r"\bconsultation\b"), "consultation"),
    (re.compile(r"\bappel\s+a\s+candidature\b"), "appel a candidature"),
]

JOB_CONTRACT_KEYWORDS = ("cdi", "stage", "alternance", "freelance")
JOB_LEVEL_KEYWORDS = ("senior", "junior")
JOB_LOCATIONS = (
    "ben arous",
    "monastir",
    "ariana",
    "nabeul",
    "gafsa",
    "sousse",
    "sfax",
    "tunis",
)

_STATS = {
    "cleaned_records": 0,
    "skipped_short_texts": 0,
}


def _increment_cleaned_count() -> None:
    _STATS["cleaned_records"] += 1
    if _STATS["cleaned_records"] % 100 == 0:
        logger.info(
            "NLP preprocessing progress: cleaned_records=%s skipped_short_texts=%s",
            _STATS["cleaned_records"],
            _STATS["skipped_short_texts"],
        )


def _increment_skipped_short() -> None:
    _STATS["skipped_short_texts"] += 1
    logger.info(
        "NLP preprocessing short-text fallback used. cleaned_records=%s skipped_short_texts=%s",
        _STATS["cleaned_records"],
        _STATS["skipped_short_texts"],
    )


def get_preprocessing_stats() -> Dict[str, int]:
    return dict(_STATS)


def reset_preprocessing_stats() -> None:
    _STATS["cleaned_records"] = 0
    _STATS["skipped_short_texts"] = 0


def _strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def _basic_pre_clean(text: str) -> str:
    value = html.unescape(text)
    value = HTML_TAG_RE.sub(" ", value)
    value = URL_RE.sub(" ", value)
    value = EMAIL_RE.sub(" ", value)
    value = unicodedata.normalize("NFKC", value)
    return WHITESPACE_RE.sub(" ", value).strip()


def _normalize_for_matching(text: str) -> str:
    lowered = text.lower().replace("’", "'").replace("`", "'")
    lowered = _strip_accents(lowered)
    lowered = re.sub(r"[^a-z0-9\s'/-]", " ", lowered)
    return WHITESPACE_RE.sub(" ", lowered).strip()


def _remove_boilerplate(text: str) -> str:
    cleaned = text
    for pattern in BOILERPLATE_PATTERNS:
        cleaned = pattern.sub(" ", cleaned)
    return cleaned


def _normalize_punctuation(text: str) -> str:
    single = REPEATED_PUNCT_RE.sub(r"\1", text)
    single = re.sub(r"\s*([,;:.!?])\s*", r"\1 ", single)
    return WHITESPACE_RE.sub(" ", single).strip()


def _dedupe_consecutive_words(text: str) -> str:
    tokens = text.split()
    if not tokens:
        return ""

    deduped = [tokens[0]]
    for token in tokens[1:]:
        if token.lower() != deduped[-1].lower():
            deduped.append(token)
    return " ".join(deduped)


def _remove_phrase(text: str, phrase: str) -> str:
    if not text or not phrase:
        return text
    pattern = re.compile(rf"\b{re.escape(phrase)}\b", re.IGNORECASE)
    return pattern.sub(" ", text)


def _normalize_org_candidate(value: str) -> str:
    if not value:
        return ""

    cleaned = WHITESPACE_RE.sub(" ", value).strip(" -:;,.")
    cleaned = re.split(
        r"\b(recrute|lance|publie|annonce|cherche|offre|poste|mission)\b",
        cleaned,
        maxsplit=1,
    )[0].strip(" -:;,.")
    return WHITESPACE_RE.sub(" ", cleaned).strip()


def extract_organization(text: str) -> str:
    if text is None:
        return ""

    raw = _basic_pre_clean(str(text))
    if not raw:
        return ""

    normalized = _normalize_for_matching(raw)
    if not normalized:
        return ""

    def _sanitize_candidate(candidate: str) -> str:
        cleaned = WHITESPACE_RE.sub(" ", candidate).strip(" -:;,.")
        if not cleaned:
            return ""

        # Trim clauses that usually indicate description, not entity names.
        cleaned = re.split(
            r"\b(?:qui|dont|pour|avec|afin|sur|depuis|deadline|date|reference|ref|contact|"
            r"email|tel|telephone|adresse|mission|poste|profil|experience|salaire)\b",
            cleaned,
            maxsplit=1,
        )[0].strip(" -:;,.")
        cleaned = re.split(
            r"\b(?:filiale\s+de|editeur\s+de|éditeur\s+de|leader\s+de|specialise\s+dans|"
            r"spécialisé\s+dans|specialisee\s+dans|spécialisée\s+dans)\b",
            cleaned,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0].strip(" -:;,.")

        # Remove trailing address fragments.
        cleaned = re.split(
            r"\b(?:rue|avenue|boulevard|immeuble|appartement|etage|bp|b\.p|code|postal)\b",
            cleaned,
            maxsplit=1,
        )[0].strip(" -:;,.")
        cleaned = re.split(r"\s+\d{2,}", cleaned, maxsplit=1)[0].strip(" -:;,.")

        # Strip leading non-entity glue words.
        cleaned = re.sub(
            r"^(?:de|du|des|d'|la|le|les|l'|notre|nos|votre|vos|son|sa|ses)\s+",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )
        cleaned = WHITESPACE_RE.sub(" ", cleaned).strip(" -:;,.")

        tokens = cleaned.split()
        while tokens and (len(tokens[-1]) == 1 or tokens[-1].lower() in {"et", "and"}):
            tokens.pop()

        if len(tokens) >= 2:
            first_two = f"{tokens[0].lower()} {tokens[1].lower()}"
            if first_two in JOB_LOCATIONS and len(tokens) >= 3:
                tokens = tokens[2:]
            elif tokens[0].lower() in JOB_LOCATIONS:
                tokens = tokens[1:]

        cleaned = " ".join(tokens)
        return WHITESPACE_RE.sub(" ", cleaned).strip(" -:;,.")

    def _is_valid_candidate(candidate: str) -> bool:
        if not candidate:
            return False
        if len(candidate) < 2 or len(candidate) > 70:
            return False
        if URL_RE.search(candidate) or EMAIL_RE.search(candidate):
            return False
        if DATE_RE.search(candidate) or PARTIAL_DATE_FRAGMENT_RE.search(candidate):
            return False
        if re.search(r"\d{4,}", candidate):
            return False

        candidate_lower = candidate.lower()
        if re.fullmatch(r"(?:bank|banque|company|societe|groupe|group|office|agence|ministry|ministere)", candidate_lower):
            return False
        if candidate_lower.startswith(("nous ", "vous ", "notre ", "votre ", "son ", "sa ")):
            return False
        if re.search(r"\b(?:mon|ma|mes|ton|ta|tes)\b", candidate_lower):
            return False

        bad_phrases = (
            "de son equipe",
            "son developpement",
            "vous etes",
            "mission principale",
            "poste base",
            "poste basee",
        )
        if any(phrase in candidate_lower for phrase in bad_phrases):
            return False

        verb_noise = re.compile(
            r"\b(?:recrute|hiring|hire|cherche|recherche|lance|annonce|publie|deadline|"
            r"poste|mission|profil|experience|salaire|candidature|cv)\b",
            re.IGNORECASE,
        )
        if verb_noise.search(candidate):
            return False

        tokens = re.findall(r"[a-z0-9][a-z0-9&'\-]*", candidate_lower)
        if not tokens:
            return False
        if not (1 <= len(tokens) <= 6):
            return False
        if not any(re.search(r"[a-z]", token) for token in tokens):
            return False
        if all(token in {"de", "du", "des", "la", "le", "les", "l"} for token in tokens):
            return False

        connectors = {"de", "du", "des", "la", "le", "les", "l", "d", "of", "and"}
        institution_heads = {
            "ministere",
            "ministry",
            "office",
            "agence",
            "banque",
            "bank",
            "universite",
            "university",
            "institut",
            "institution",
            "hopital",
            "hospital",
            "societe",
            "company",
            "groupe",
            "group",
        }
        positive_markers = institution_heads | {"holding", "telecom", "services", "labs", "lab"}
        lexical_noise = {
            "dynamique",
            "innovante",
            "specialise",
            "specialisee",
            "specialized",
            "leader",
            "marche",
            "vente",
            "cadre",
            "network",
            "profile",
            "prepare",
            "offshore",
            "basee",
            "activites",
            "developpement",
            "recrutons",
            "sommes",
            "poste",
            "mission",
            "contrat",
            "contract",
            "job",
            "emploi",
            "stage",
            "alternance",
            "senior",
            "junior",
            "analyst",
            "engineer",
            "developer",
            "responsable",
            "charge",
            "etudes",
            "actif",
            "actifs",
            "actives",
            "signe",
            "signes",
            "your",
            "our",
            "their",
            "is",
            "are",
            "the",
            "with",
            "dans",
            "pour",
            "nous",
            "vous",
            "une",
            "un",
            "equipe",
            "dossiers",
            "clients",
            "francais",
            "homologue",
            "compte",
            "ans",
            "notre",
            "votre",
            "stes",
            "ste",
            "societes",
            "metal",
            "designer",
            "evenementiel",
        }
        if any(token in lexical_noise for token in tokens):
            return False

        meaningful_tokens = [token for token in tokens if token not in connectors]
        if not meaningful_tokens:
            return False
        if len(meaningful_tokens) > 4:
            return False

        if any(token.isdigit() for token in tokens):
            return False

        if len(tokens) == 1 and len(tokens[0]) < 3:
            return False
        if len(tokens) == 1 and tokens[0] in {"societe", "societes", "company", "bank", "banque", "group", "groupe"}:
            return False
        if len(tokens) == 1:
            token = tokens[0]
            if token in JOB_LOCATIONS:
                return False
            # Generalized location-like rejection for single-word candidates.
            if re.search(rf"\b(?:a|au|en|sur|basee?\s+a)\s+{re.escape(token)}\b", normalized):
                if not re.search(
                    rf"\b{re.escape(token)}\s+(?:recrute|recruits|hiring|hire|embauche|cherche|recherche)\b",
                    normalized,
                ):
                    return False
        if any(len(token) == 1 and token not in {"l", "d"} for token in tokens):
            return False

        if len(tokens) > 6:
            return False

        if len(tokens) >= 3 and not (
            meaningful_tokens[0] in institution_heads or any(token in positive_markers for token in meaningful_tokens)
        ):
            high_risk_joiners = {"et", "and", "dans", "pour", "avec", "with", "from"}
            if any(token in high_risk_joiners for token in tokens):
                return False
            connector_count = sum(token in connectors for token in tokens)
            if connector_count > 2:
                return False
        return True

    org_word = r"[a-z0-9][a-z0-9&'\-]{0,24}"
    org_phrase = rf"{org_word}(?:\s+{org_word}){{0,5}}"
    org_phrase_short = rf"{org_word}(?:\s+{org_word}){{0,3}}"
    search_text = normalized[:260]
    title_slice = normalized[:260]

    patterns = [
        (rf"\b(?:poste|offre|opportunite)\s+chez\s+({org_phrase})\b", search_text),
        (rf"\bchez\s+({org_phrase})\b", search_text),
        (
            rf"\b({org_word}(?:\s+{org_word}){{0,2}})\s+"
            rf"(?:editeur|éditeur|leader|specialise|spécialisé|specialisee|spécialisée|filiale)\b",
            search_text,
        ),
        (rf"\b(?:entreprise|groupe|societe|company|organisation|organization)\s+({org_phrase})\b", search_text),
        (
            rf"\b((?:ministere|ministry|office|agence|banque|bank|universite|university|institut|"
            rf"institution|hopital|hospital)\s+{org_phrase})\b",
            search_text,
        ),
        (
            rf"\b({org_phrase_short})\s+(?:recrute|recruits|hiring|hire|embauche|cherche|recherche|lance|"
            rf"annonce|publie)\b",
            title_slice,
        ),
    ]

    for pattern, target_text in patterns:
        for match in re.finditer(pattern, target_text, flags=re.IGNORECASE):
            candidate = _sanitize_candidate(match.group(1))
            candidate = _normalize_org_candidate(candidate)
            if _is_valid_candidate(candidate):
                return candidate

    return ""


def detect_content_type(text: str) -> str:
    if text is None:
        return "job"

    raw = _basic_pre_clean(str(text))
    if not raw:
        return "job"

    normalized = _normalize_for_matching(raw)
    for pattern, _ in TENDER_TYPE_PATTERNS:
        if pattern.search(normalized):
            return "tender"

    # Tender portals often include country marker tokens even without explicit tender type.
    if LOCATION_MARKER_RE.search(raw):
        return "tender"

    tender_context_re = re.compile(r"\b(acquisition|consultation|appel|candidature|offres?)\b")
    if len(DATE_RE.findall(raw)) >= 2 and tender_context_re.search(normalized):
        return "tender"

    return "job"


def extract_tender_structure(text: str) -> Dict[str, str]:
    empty = {
        "tender_type": "",
        "publication_date": "",
        "deadline": "",
        "location": "",
    }
    if text is None:
        return empty

    raw = _basic_pre_clean(str(text))
    if not raw:
        return empty

    normalized = _normalize_for_matching(raw)

    tender_type = ""
    for pattern, label in TENDER_TYPE_PATTERNS:
        if pattern.search(normalized):
            tender_type = label
            break

    dates = DATE_RE.findall(raw)
    publication_date = dates[0] if dates else ""
    deadline = dates[-1] if len(dates) > 1 and dates[-1] != dates[0] else ""

    location_match = LOCATION_MARKER_RE.search(raw.lower())
    location = location_match.group(1).lower() if location_match else ""

    return {
        "tender_type": tender_type,
        "publication_date": publication_date,
        "deadline": deadline,
        "location": location,
    }


def clean_tender_text(text: str) -> str:
    if text is None:
        return ""

    cleaned = _basic_pre_clean(str(text))
    if not cleaned:
        return ""

    # Protect valid full dates first, then remove broken fragments like "19/".
    full_dates = DATE_RE.findall(cleaned)
    date_placeholders = {}
    for idx, full_date in enumerate(full_dates):
        placeholder = f"__full_date_{idx}__"
        date_placeholders[placeholder] = full_date
        cleaned = cleaned.replace(full_date, placeholder, 1)

    cleaned = _strip_accents(cleaned.lower())
    cleaned = LEADING_CODE_RE.sub(" ", cleaned)
    cleaned = LOCATION_MARKER_RE.sub(" ", cleaned)
    cleaned = TIMESTAMP_RE.sub(" ", cleaned)
    cleaned = PARTIAL_DATE_FRAGMENT_RE.sub(" ", cleaned)
    for placeholder, full_date in date_placeholders.items():
        cleaned = cleaned.replace(placeholder, full_date)
    cleaned = _remove_boilerplate(cleaned)
    cleaned = _dedupe_consecutive_words(cleaned)
    return _normalize_punctuation(cleaned)


def clean_job_text(text: str) -> str:
    if text is None:
        return ""

    cleaned = _basic_pre_clean(str(text))
    if not cleaned:
        return ""

    cleaned = _strip_accents(cleaned.lower())
    cleaned = _remove_boilerplate(cleaned)
    cleaned = _dedupe_consecutive_words(cleaned)
    return _normalize_punctuation(cleaned)


def _extract_keyword(text: str, keywords) -> str:
    for keyword in keywords:
        pattern = re.compile(rf"\b{re.escape(keyword)}\b", re.IGNORECASE)
        if pattern.search(text):
            return keyword
    return ""


def _extract_job_title(text: str, contract: str, location: str) -> str:
    title_source = text
    if contract:
        title_source = _remove_phrase(title_source, contract)
    if location:
        title_source = _remove_phrase(title_source, location)
    title_source = re.sub(r"\(\s*\)", " ", title_source)
    title_source = re.sub(r"\b(nous recrutons|poste|mission)\b", " ", title_source, flags=re.IGNORECASE)
    title_source = _normalize_punctuation(title_source)

    segments = [segment.strip() for segment in re.split(r"[.:;|]", title_source) if segment.strip()]
    primary_segment = segments[0] if segments else title_source

    raw_tokens = re.findall(r"[a-z0-9]+(?:/[a-z0-9]+)?", primary_segment.lower())
    if not raw_tokens:
        return ""

    deduped_tokens = []
    for token in raw_tokens:
        if not deduped_tokens or token != deduped_tokens[-1]:
            deduped_tokens.append(token)

    hard_noise = {
        "nous",
        "recrutons",
        "poste",
        "mission",
        "plan",
        "en",
        "au",
        "aux",
        "sur",
        "h/f",
        "hf",
        "f/h",
    }
    filtered_tokens = [token for token in deduped_tokens if token not in hard_noise]
    if not filtered_tokens:
        filtered_tokens = deduped_tokens

    connectors = {"de", "du", "des", "la", "le", "les", "et", "d"}
    title_tokens = filtered_tokens[:3]
    for token in filtered_tokens[3:]:
        if len(title_tokens) >= 5:
            break
        if token in connectors:
            continue
        title_tokens.append(token)

    while title_tokens and title_tokens[-1] in connectors:
        title_tokens.pop()

    if len(title_tokens) < 3:
        title_tokens = filtered_tokens[:5]

    return " ".join(title_tokens).strip()


def enrich_job_text(text: str) -> str:
    if text is None:
        return ""

    cleaned = clean_job_text(text)
    if not cleaned:
        return ""

    words = cleaned.split()
    if len(words) < 3:
        return cleaned

    contract = _extract_keyword(cleaned, JOB_CONTRACT_KEYWORDS)
    location = _extract_keyword(cleaned, JOB_LOCATIONS)
    level = _extract_keyword(cleaned, JOB_LEVEL_KEYWORDS)
    title = _extract_job_title(cleaned, contract=contract, location=location)

    # Keep neutral behavior for generic short metadata-like strings.
    if not contract and not location and not level and len(words) < 5:
        return cleaned

    parts = []
    if contract:
        parts.append(f"contract: {contract}")
    if location:
        parts.append(f"location: {location}")
    if level:
        parts.append(f"level: {level}")
    normalized_title = _normalize_punctuation(title).lower().strip()
    normalized_cleaned = _normalize_punctuation(cleaned).lower().strip()
    cleaned_payload = cleaned
    if title and normalized_title and normalized_title in normalized_cleaned:
        cleaned_payload = _normalize_punctuation(_remove_phrase(cleaned_payload, title))
    if title:
        parts.append(f"title: {title}")
    parts.append(cleaned_payload or cleaned)

    enriched = " ".join(part for part in parts if part).strip()
    enriched = _dedupe_consecutive_words(enriched)
    return _normalize_punctuation(enriched)


def build_embedding_text(text: str) -> str:
    structured = extract_tender_structure(text)
    cleaned_text = clean_tender_text(text)

    # Avoid duplicated structured phrases in the natural text payload.
    cleaned_text = _remove_phrase(cleaned_text, structured.get("tender_type", ""))
    cleaned_text = _remove_phrase(cleaned_text, structured.get("publication_date", ""))
    cleaned_text = _remove_phrase(cleaned_text, structured.get("deadline", ""))
    cleaned_text = _dedupe_consecutive_words(cleaned_text)
    cleaned_text = _normalize_punctuation(cleaned_text)

    parts = []
    if structured["tender_type"]:
        parts.append(f"type: {structured['tender_type']}")
    if structured["publication_date"]:
        parts.append(f"publication date: {structured['publication_date']}")
    if structured["deadline"]:
        parts.append(f"deadline: {structured['deadline']}")
    if structured["location"]:
        parts.append(f"location: {structured['location']}")
    if cleaned_text:
        parts.append(cleaned_text)

    enriched = " ".join(part for part in parts if part).strip()
    return _normalize_punctuation(enriched)


def prepare_text_for_nlp(text: str) -> str:
    if text is None:
        _increment_skipped_short()
        return ""

    raw_value = str(text)
    pre_clean = _basic_pre_clean(raw_value)
    if not pre_clean:
        _increment_skipped_short()
        return ""

    content_type = detect_content_type(pre_clean)
    if content_type == "tender":
        value = build_embedding_text(pre_clean)
        if not value:
            value = clean_tender_text(pre_clean)
    else:
        value = enrich_job_text(pre_clean)
        if not value:
            value = clean_job_text(pre_clean) or pre_clean

    organization = extract_organization(pre_clean)
    if organization:
        org_prefix = f"organization: {organization}"
        normalized_org_prefix = _normalize_for_matching(org_prefix)
        if normalized_org_prefix not in _normalize_for_matching(value):
            value = f"{org_prefix} {value}".strip()

    value = _normalize_punctuation(value)
    if len(value) > MAX_TEXT_LENGTH:
        value = value[:MAX_TEXT_LENGTH].rstrip()

    # Critical fix: never drop meaningful short content.
    if len(value) < MIN_TEXT_LENGTH:
        _increment_skipped_short()
        if value:
            _increment_cleaned_count()
            return value

        fallback = clean_job_text(pre_clean) if content_type == "job" else clean_tender_text(pre_clean)
        fallback = _normalize_punctuation(fallback)
        if fallback:
            _increment_cleaned_count()
            return fallback[:MAX_TEXT_LENGTH].rstrip()

        raw_fallback = _normalize_punctuation(_strip_accents(pre_clean.lower()))
        if raw_fallback:
            _increment_cleaned_count()
            return raw_fallback[:MAX_TEXT_LENGTH].rstrip()
        return ""

    _increment_cleaned_count()
    return value


def _get_attr(obj: Any, *names: str) -> str:
    for name in names:
        if isinstance(obj, dict):
            value = obj.get(name)
        else:
            value = getattr(obj, name, None)
        if value is not None and str(value).strip():
            return str(value)
    return ""


def prepare_combined_text(opportunity: Any) -> str:
    title = _get_attr(opportunity, "titre", "title")
    description = _get_attr(opportunity, "description")
    organization = _get_attr(opportunity, "organisation_nom", "organization", "organisation")
    location = _get_attr(opportunity, "location")

    combined = " ".join(part for part in [title, description, organization, location] if part).strip()
    return prepare_text_for_nlp(combined)
