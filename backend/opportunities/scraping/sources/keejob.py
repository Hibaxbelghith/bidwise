import logging
import hashlib
import json
import os
import random
import re
import time
import unicodedata
from datetime import date, timedelta
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..scraper_base import BaseOpportunityScraper
from ..scraper_utils import (
    FETCH_DETAILS,
    MAX_DESCRIPTION_LENGTH,
    SCRAPER_TIMEOUT_DEFAULT,
    canonicalize_source_item_url,
    clean_description_for_ml,
)
from opportunities.utils.images import is_valid_image_url


logger = logging.getLogger(__name__)

DESCRIPTION_ALLOWED_TAGS = {
    "p",
    "ul",
    "li",
    "strong",
    "br",
}
DESCRIPTION_DROP_TAGS = {
    "script",
    "style",
    "iframe",
    "object",
    "embed",
    "form",
    "input",
    "button",
}

EXPIRED_BADGE_LABELS = {
    "expiree",
    "offre expiree",
    "expired",
}

CONTRACT_TYPE_ALLOWED_VALUES = (
    "CDI",
    "CDD",
    "Stage",
    "Saisonnier",
    "SIVP",
    "Stage/PFE",
    "Indépendant/Freelance",
    "Fonction publique",
)

CONTRACT_TYPE_NORMALIZATION_MAP = {
    "cdi": "CDI",
    "cdd": "CDD",
    "stage": "Stage",
    "saisonnier": "Saisonnier",
    "sivp": "SIVP",
    "stage pfe": "Stage/PFE",
    "independant freelance": "Indépendant/Freelance",
    "fonction publique": "Fonction publique",
}

FR_MONTHS = {
    "janvier": 1,
    "fevrier": 2,
    "février": 2,
    "mars": 3,
    "avril": 4,
    "mai": 5,
    "juin": 6,
    "juillet": 7,
    "aout": 8,
    "août": 8,
    "septembre": 9,
    "octobre": 10,
    "novembre": 11,
    "decembre": 12,
    "décembre": 12,
}


def _get_env_int(name, default):
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        logger.warning("Invalid %s=%r, falling back to %s", name, value, default)
        return default


def _get_env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


SCRAPER_TIMEOUT = _get_env_int("SCRAPER_TIMEOUT", SCRAPER_TIMEOUT_DEFAULT)
KEEJOB_MAX_PAGES = _get_env_int("KEEJOB_MAX_PAGES", 1000)
KEEJOB_STAGE_MAX_PAGES = _get_env_int("KEEJOB_STAGE_MAX_PAGES", 1000)
KEEJOB_MAX_RECORDS = _get_env_int("KEEJOB_MAX_RECORDS", 1000)
KEEJOB_STAGE_ONLY = os.getenv("KEEJOB_STAGE_ONLY", "false").strip().lower() in {"1", "true", "yes", "on"}
KEEJOB_STAGE_LISTING_URL = os.getenv(
    "KEEJOB_STAGE_LISTING_URL",
    "https://www.keejob.com/offres-emploi/?keywords=&job_types=9&education_level=0&experience_level=0&sort_by=&page=1",
)
KEEJOB_SAISONNIER_LISTING_URL = os.getenv(
    "KEEJOB_SAISONNIER_LISTING_URL",
    "https://www.keejob.com/offres-emploi/?keywords=saisonnier&page=1",
)
KEEJOB_DIVERSIFIED_FILTERS = _get_env_bool("KEEJOB_DIVERSIFIED_FILTERS", True)


class KeejobScraper(BaseOpportunityScraper):
    source_name = "Keejob"
    source_url = "https://www.keejob.com/offres-emploi/"
    source_type = "SITE_EMPLOI"
    STAGE_LISTING_URL = KEEJOB_STAGE_LISTING_URL

    DEFAULT_TIMEOUT = SCRAPER_TIMEOUT

    JOB_CARD_SELECTORS = [
        "article",
    ]
    JOB_LINK_SELECTORS = [
        "h2 a[href*='/offres-emploi/']",
        "article h2 a",
    ]
    TITLE_SELECTORS = [
        "h2 a",
    ]
    COMPANY_SELECTORS = [
        "p a",
    ]
    DESCRIPTION_SELECTORS = [
        "div.mb-3 p",
    ]
    LOCATION_SELECTORS = [
        "i.fa-map-marker-alt + span",
    ]
    PUBLICATION_DATE_SELECTORS = [
        "i.fa-clock + span",
        "i.fa-calendar-alt + span",
        "i.fas.fa-calendar-alt + span",
    ]

    def __init__(
        self,
        timeout=DEFAULT_TIMEOUT,
        min_delay=0.8,
        max_delay=1.5,
        fetch_details=FETCH_DETAILS,
        max_pages=None,
        max_records=KEEJOB_MAX_RECORDS,
        stage_only=KEEJOB_STAGE_ONLY,
    ):
        self.timeout = timeout
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.fetch_details = fetch_details
        self.stage_only = bool(stage_only)
        default_pages = KEEJOB_STAGE_MAX_PAGES if self.stage_only else KEEJOB_MAX_PAGES
        resolved_max_pages = default_pages if max_pages is None else int(max_pages)
        self.max_pages = max(1, resolved_max_pages)
        self.max_records = max_records if max_records and int(max_records) > 0 else None
        self.listing_url = self.STAGE_LISTING_URL if self.stage_only else self.source_url
        self.seasonal_listing_url = KEEJOB_SAISONNIER_LISTING_URL
        self.diversified_filters = bool(KEEJOB_DIVERSIFIED_FILTERS)
        self.listing_roots = self._build_listing_roots()
        self.max_description_length = MAX_DESCRIPTION_LENGTH
        self.blocked = False
        self.last_page_failed = False
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
            }
        )
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=frozenset(["GET", "HEAD", "OPTIONS"]),
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def fetch_raw_records(self):
        records = []
        for page_records in self.fetch_raw_record_pages():
            records.extend(page_records)
        return records

    def fetch_raw_record_pages(self):
        records = []
        seen_urls = set()
        skipped_records = 0

        for listing_root in self.listing_roots:
            empty_pages_count = 0
            failure_count = 0
            for page_number in range(1, self.max_pages + 1):
                page_records = []
                self.last_page_failed = False
                listing_url = self._build_listing_url(page_number, listing_root)
                soup = self._safe_get_soup(listing_url)
                if self.blocked:
                    return
                if soup is None:
                    self.last_page_failed = True
                    failure_count += 1
                    logger.warning("No HTML returned for source URL: %s", listing_url)
                    yield page_records
                    if failure_count >= 3:
                        logger.info("[keejob] stopping due to failures")
                        break
                    if page_number > 1:
                        break
                    continue
                failure_count = 0

                cards = self._extract_cards(soup)
                logger.info(
                    "Keejob scraper listing=%s page=%s detected %s candidate job cards",
                    listing_root,
                    page_number,
                    len(cards),
                )

                if not cards:
                    yield page_records
                    break

                for card in cards:
                    url = self._extract_url(card)
                    canonical_url = canonicalize_source_item_url(url)
                    if not canonical_url or canonical_url in seen_urls:
                        skipped_records += 1
                        if canonical_url in seen_urls:
                            logger.info("Skipping duplicate URL in same run: %s", canonical_url)
                        continue
                    seen_urls.add(canonical_url)

                    listing_title = self._extract_first_text(card, self.TITLE_SELECTORS)
                    publication_date_text = self._extract_first_text(card, self.PUBLICATION_DATE_SELECTORS)

                    detail_soup = self._safe_get_soup(url)
                    if self.blocked:
                        yield page_records
                        return
                    if detail_soup is None:
                        skipped_records += 1
                        continue

                    publication_date = self._extract_detail_publication_date(detail_soup)
                    if not publication_date:
                        publication_date = self._normalize_publication_date(publication_date_text)

                    detail_title = self._extract_detail_title(detail_soup)
                    detail_company = self._extract_detail_company(detail_soup)
                    detail_company_logo = self._extract_detail_company_logo(
                        detail_soup,
                        canonical_url,
                        detail_company,
                    )
                    detail_description_html = self._extract_detail_description_html(detail_soup)
                    detail_description = self._extract_detail_description(detail_soup, detail_description_html)
                    detail_location = self._extract_detail_location(detail_soup)
                    if not detail_location:
                        detail_location = self._extract_header_location(detail_soup)
                    detail_contract_type = self._extract_detail_contract_type(detail_soup)
                    structured_fields = self._extract_structured_detail_fields(detail_soup)
                    detail_deadline = (structured_fields or {}).get("deadline")
                    detail_status = self._extract_detail_status(detail_soup)
                    structured_payload = {
                        "reference": (structured_fields or {}).get("reference") or None,
                        "published_at": (structured_fields or {}).get("published_at") or None,
                        "deadline": detail_deadline or None,
                        "date_limite": detail_deadline or None,
                        "experience": (structured_fields or {}).get("experience") or None,
                        "education_level": (structured_fields or {}).get("education_level") or None,
                        "availability": (structured_fields or {}).get("availability") or None,
                        "salary": (structured_fields or {}).get("salary") or None,
                        "languages": (structured_fields or {}).get("languages") or None,
                        "company_sector": (structured_fields or {}).get("company_sector") or None,
                        "company_size": (structured_fields or {}).get("company_size") or None,
                    }

                    raw_title = detail_title or listing_title
                    title = re.sub(r"\s+", " ", (raw_title or "").replace("/", " ")).strip()
                    raw_company = (detail_company or "").strip()
                    organization_normalized = self._normalize_company(raw_company)
                    description = detail_description
                    location = self._clean_location(detail_location)
                    description, raw_description = self._clean_description(description)
                    location = self._enrich_location_from_description(location, description)

                    inferred_type = self._map_contract_to_opportunity_type(
                        detail_contract_type,
                        title,
                        description,
                    )

                    if self.stage_only and inferred_type != "STAGE":
                        skipped_records += 1
                        continue

                    if not raw_company:
                        logger.debug("Keejob detail has empty company for url=%s", url)
                    if not detail_company_logo:
                        logger.debug("[SCRAPER] No logo found for %s", title or canonical_url)

                    record = {
                        "title": title,
                        "description": description,
                        "organization": raw_company,
                        "organization_normalized": organization_normalized,
                        "company_logo": detail_company_logo or None,
                        "logo_url": detail_company_logo or None,
                        "location": location,
                        "publication_date": publication_date,
                        "description_html": detail_description_html or None,
                        "contract_type": detail_contract_type or None,
                        "type_contrat": detail_contract_type or None,
                        **structured_payload,
                        "type_opportunite": inferred_type,
                        "type": inferred_type,
                        "statut": detail_status,
                        "status": detail_status,
                        "source_name": self.source_name,
                        "source_url": self.source_url,
                        "source_type": self.source_type,
                        "source_listing_url": listing_url,
                        "url": canonical_url,
                        "external_id": hashlib.sha1(canonical_url.encode("utf-8")).hexdigest(),
                    }
                    if raw_description:
                        record["raw_description"] = raw_description
                    if not self._is_valid_record(record):
                        skipped_records += 1
                        continue

                    records.append(record)
                    page_records.append(record)

                    if self.max_records and len(records) >= self.max_records:
                        logger.info("Reached max_records=%s, stopping early", self.max_records)
                        logger.info(
                            "Keejob scraper extracted %s records (skipped: %s, pages scanned: %s)",
                            len(records),
                            skipped_records,
                            page_number,
                        )
                        yield page_records
                        return
                yield page_records
                if page_records:
                    empty_pages_count = 0
                else:
                    empty_pages_count += 1
                    if empty_pages_count >= 2:
                        logger.info("[keejob] stopping early at page=%s (no new data)", page_number)
                        break

        logger.info(
            "Keejob scraper extracted %s records (skipped: %s)",
            len(records),
            skipped_records,
        )

    def _build_listing_roots(self):
        if self.stage_only:
            return [self.STAGE_LISTING_URL]

        roots = [self.source_url]
        if self.diversified_filters:
            roots.append(self.STAGE_LISTING_URL)
            roots.append(self.seasonal_listing_url)

        deduped = []
        seen = set()
        for root in roots:
            raw_root = (root or "").strip()
            normalized_key = canonicalize_source_item_url(raw_root) or raw_root
            if not raw_root or normalized_key in seen:
                continue
            seen.add(normalized_key)
            deduped.append(raw_root)

        return deduped or [self.source_url]

    def _build_listing_url(self, page_number, listing_root=None):
        base_url = (listing_root or self.listing_url or self.source_url).strip()
        parsed = urlsplit(base_url)

        if page_number <= 1 and not parsed.query:
            return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", parsed.fragment))

        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        query["page"] = str(max(1, int(page_number)))
        encoded_query = urlencode(query, doseq=True)
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, encoded_query, parsed.fragment))

    def _safe_get_soup(self, url):
        try:
            self._rate_limit_delay()
            response = self.session.get(url, timeout=self.timeout)
            if response.status_code == 403:
                self.blocked = True
                logger.warning("[keejob] blocked (403), stopping")
                return None
            if response.status_code != 200:
                logger.warning("Request failed for %s status=%s", url, response.status_code)
                return None
            response.raise_for_status()
            return BeautifulSoup(response.text, "html.parser")
        except requests.RequestException as exc:
            logger.warning("Request failed for %s: %s", url, exc)
            return None

    def _extract_cards(self, soup):
        cards = []
        for selector in self.JOB_CARD_SELECTORS:
            selected = soup.select(selector)
            if selected:
                cards.extend(selected)

        # Keep only article blocks that look like real job cards.
        filtered = []
        for card in cards:
            if any(card.select_one(link_selector) for link_selector in self.JOB_LINK_SELECTORS):
                filtered.append(card)
        logger.debug(
            "Candidate cards: %s, filtered cards with links: %s",
            len(cards),
            len(filtered),
        )
        return filtered

    def _extract_url(self, card):
        for selector in self.JOB_LINK_SELECTORS:
            node = card.select_one(selector)
            if not node:
                continue
            href = node.get("href")
            if not href:
                continue
            return urljoin(self.source_url, href.strip())
        return ""

    def _extract_first_text(self, card, selectors):
        for selector in selectors:
            node = card.select_one(selector)
            if node:
                text = self._clean_text(node.get_text(" ", strip=True))
                if text:
                    return text
        return ""

    def _extract_detail_title(self, detail_soup):
        if detail_soup is None:
            return ""
        node = detail_soup.select_one("h1")
        if node is None:
            return ""
        return self._clean_text(node.get_text(" ", strip=True))

    def _extract_detail_company(self, detail_soup):
        if detail_soup is None:
            return ""

        node = detail_soup.select_one("a[href*='/offres-emploi/companies/']")
        if node is not None:
            text = self._sanitize_company_candidate(node.get_text(" ", strip=True))
            if text and not text.lower().startswith("voir toutes les offres"):
                return text

        title_node = detail_soup.select_one("h1")
        if title_node is not None:
            title_text = self._clean_text(title_node.get_text(" ", strip=True))
            allowed_tags = {"a", "span", "p", "div"}

            for sibling in title_node.find_next_siblings():
                sibling_name = sibling.name or ""
                if sibling_name in {"h1", "h2", "h3"}:
                    break
                if sibling_name not in allowed_tags:
                    continue

                candidate_nodes = [sibling]
                candidate_nodes.extend(sibling.find_all(["a", "span", "p", "div"]))

                for candidate_node in candidate_nodes:
                    candidate_text = self._sanitize_company_candidate(candidate_node.get_text(" ", strip=True))
                    if not candidate_text:
                        continue
                    if len(candidate_text) >= 100:
                        continue
                    if title_text and self._normalize_label(candidate_text) == self._normalize_label(title_text):
                        continue
                    if candidate_text.lower().startswith("voir toutes les offres"):
                        continue
                    return candidate_text

        return self._extract_company_from_jsonld(detail_soup)

    def _extract_company_from_jsonld(self, detail_soup):
        if detail_soup is None:
            return ""

        for script in detail_soup.find_all("script", attrs={"type": "application/ld+json"}):
            payload = self._parse_jsonld_payload(script)
            if not payload:
                continue

            for item in payload:
                if not isinstance(item, dict):
                    continue

                hiring_org = item.get("hiringOrganization")
                if isinstance(hiring_org, dict):
                    name = self._sanitize_company_candidate(hiring_org.get("name"))
                    if name:
                        return name

                item_type = self._normalize_label(item.get("@type"))
                if item_type == "organization":
                    name = self._sanitize_company_candidate(item.get("name"))
                    if name:
                        return name

        return ""

    def _parse_jsonld_payload(self, script_node):
        raw_content = ""
        if script_node is not None:
            raw_content = script_node.string or script_node.get_text() or ""

        cleaned_content = re.sub(r"[\x00-\x1f]+", " ", str(raw_content)).strip()
        if not cleaned_content:
            return []

        try:
            parsed = json.loads(cleaned_content)
        except (TypeError, ValueError):
            return []

        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict):
            return [parsed]
        return []

    def _extract_detail_company_logo(self, detail_soup, detail_url, company_name=""):
        if detail_soup is None:
            return None

        entreprise_heading = None
        for heading in detail_soup.find_all("h2"):
            if self._normalize_label(heading.get_text(" ", strip=True)) == "entreprise":
                entreprise_heading = heading
                break

        if entreprise_heading is None:
            return None

        heading_block = entreprise_heading.find_parent("div")
        search_blocks = []
        if heading_block is not None:
            search_blocks.append(heading_block)
            parent_block = heading_block.find_parent("div")
            if parent_block is not None:
                search_blocks.append(parent_block)

        image = None
        for block in search_blocks:
            image = block.find("img")
            if image is not None:
                break
        if image is None:
            return None

        src = self._clean_text(image.get("src"))
        if not src or "/media/recruiter/" not in src:
            return None

        absolute_logo_url = urljoin(detail_url or self.source_url, src)
        if not self._is_valid_url(absolute_logo_url) or not is_valid_image_url(absolute_logo_url):
            return None

        return absolute_logo_url


    def _extract_detail_description_html(self, detail_soup):
        if detail_soup is None:
            return ""

        selectors = [
            "div.prose",
            "div[class*='prose']",
            "article div.prose",
            "main div.prose",
        ]

        for selector in selectors:
            prose_node = detail_soup.select_one(selector)
            if prose_node is None:
                continue

            raw_html = prose_node.decode_contents(formatter="html")
            cleaned = self._sanitize_description_html(raw_html)
            if cleaned:
                return cleaned

        # Fallback: keep the first meaningful content block after "Description" heading.
        for heading in detail_soup.find_all(["h2", "h3", "h4"]):
            label = self._normalize_label(heading.get_text(" ", strip=True))
            if "description" not in label and "mission" not in label:
                continue

            sibling = heading.find_next_sibling()
            while sibling is not None and getattr(sibling, "name", "") not in {"h2", "h3", "h4"}:
                raw_html = sibling.decode_contents(formatter="html") if hasattr(sibling, "decode_contents") else ""
                cleaned = self._sanitize_description_html(raw_html)
                if cleaned:
                    return cleaned
                sibling = sibling.find_next_sibling()

        return ""

    def _sanitize_description_html(self, html_fragment):
        raw_html = self._clean_text(html_fragment)
        if not raw_html:
            return ""

        soup = BeautifulSoup(f"<div>{html_fragment}</div>", "html.parser")
        wrapper = soup.find("div")
        if wrapper is None:
            return ""

        for node in wrapper.find_all(DESCRIPTION_DROP_TAGS):
            node.decompose()

        for node in list(wrapper.find_all(True)):
            tag_name = (node.name or "").lower()

            # Keep semantic emphasis while enforcing a minimal allowlist.
            if tag_name in {"b", "h1", "h2", "h3", "h4", "h5", "h6"}:
                node.name = "strong"
                tag_name = "strong"

            if tag_name == "ol":
                node.name = "ul"
                tag_name = "ul"

            if tag_name not in DESCRIPTION_ALLOWED_TAGS:
                node.unwrap()
                continue

            for attr_name in list(node.attrs.keys()):
                del node.attrs[attr_name]

        cleaned_html = wrapper.decode_contents(formatter="html")
        return self._clean_text(cleaned_html)

    def _extract_detail_status(self, detail_soup):
        if detail_soup is None:
            return "ACTIVE"

        # Mark EXPIREE only on explicit red/status badge evidence.
        selectors = [
            "div.bg-red-100",
            "div[class*='bg-red']",
            "span.badge",
            "div.badge",
            "span[class*='status']",
            "div[class*='status']",
            "span[class*='text-red']",
            "div[class*='text-red']",
            "div[class*='dark:text-red']",
            "p[class*='text-red']",
        ]

        for selector in selectors:
            for node in detail_soup.select(selector):
                if self._is_explicit_expired_badge(node):
                    return "EXPIREE"

        return "ACTIVE"

    def _is_explicit_expired_badge(self, node):
        if node is None:
            return False

        text = self._normalize_label(node.get_text(" ", strip=True))
        if text not in EXPIRED_BADGE_LABELS:
            return False

        class_blob = self._normalize_label(" ".join(node.get("class") or []))
        has_status_hint = any(
            token in class_blob
            for token in ("text red", "bg red", "badge", "status")
        )
        return has_status_hint

    def _parse_date_value(self, value):
        text = self._clean_text(value)
        if not text:
            return None

        iso_match = re.search(r"(\d{4})-(\d{2})-(\d{2})", text)
        if iso_match:
            yyyy, mm, dd = iso_match.groups()
            try:
                return date(int(yyyy), int(mm), int(dd))
            except ValueError:
                return None

        day_first_match = re.search(r"(\d{2})[/-](\d{2})[/-](\d{4})", text)
        if day_first_match:
            dd, mm, yyyy = day_first_match.groups()
            try:
                return date(int(yyyy), int(mm), int(dd))
            except ValueError:
                return None

        long_match = re.search(
            r"(\d{1,2})\s+(janvier|fevrier|février|mars|avril|mai|juin|juillet|aout|août|septembre|octobre|novembre|decembre|décembre)\s+(\d{4})",
            text,
            flags=re.IGNORECASE,
        )
        if long_match:
            day_token, month_token, year_token = long_match.groups()
            month = FR_MONTHS.get(month_token.lower())
            if month is None:
                return None
            try:
                return date(int(year_token), int(month), int(day_token))
            except ValueError:
                return None

        return None

    def _html_to_description_parts(self, description_html):
        html = self._clean_text(description_html)
        if not html:
            return []

        soup = BeautifulSoup(f"<div>{description_html}</div>", "html.parser")
        wrapper = soup.find("div")
        if wrapper is None:
            return []

        parts = []
        for node in wrapper.find_all(["h2", "h3", "h4", "p", "li"]):
            # Avoid duplicates when list items already wrap paragraph nodes.
            if node.name == "p" and node.find_parent("li") is not None:
                continue

            text = self._clean_text(node.get_text(" ", strip=True))
            if not text:
                continue

            if node.name == "li":
                text = f"- {text}"

            if parts and text == parts[-1]:
                continue
            parts.append(text)

        if parts:
            return parts

        fallback_parts = []
        for text_node in wrapper.stripped_strings:
            text = self._clean_text(text_node)
            if not text:
                continue
            if fallback_parts and text == fallback_parts[-1]:
                continue
            fallback_parts.append(text)
        return fallback_parts

    def _extract_detail_description(self, detail_soup, description_html=""):
        if detail_soup is None:
            return ""

        html_payload = description_html or self._extract_detail_description_html(detail_soup)
        parts = self._html_to_description_parts(html_payload)
        return self._deduplicate_description_parts(parts)

    def _extract_detail_location(self, detail_soup):
        return self._extract_labeled_value(detail_soup, "Lieu de travail", preferred_tags=("p", "span", "div"))

    def _extract_header_location(self, detail_soup):
        if detail_soup is None:
            return ""

        selectors = [
            "h1 + div i.fa-map-marker-alt + span",
            "h1 + div i.fa-location-dot + span",
            "div.flex.flex-wrap.items-center.gap-4.mt-2 i.fa-map-marker-alt + span",
            "div.flex.flex-wrap.items-center.gap-4.mt-2 i.fa-location-dot + span",
            "i.fa-map-marker-alt + span",
            "i.fa-location-dot + span",
        ]

        for selector in selectors:
            node = detail_soup.select_one(selector)
            if node is None:
                continue
            text = self._clean_text(node.get_text(" ", strip=True))
            if text:
                return text

        return ""

    def _extract_detail_contract_type(self, detail_soup):
        sidebar = self._find_detail_sidebar_container(detail_soup)
        if sidebar is None and detail_soup is None:
            return ""

        search_root = sidebar or detail_soup
        for label_node in search_root.find_all("h3"):
            label_text = self._clean_text(label_node.get_text(" ", strip=True))
            if not self._label_contains(label_text, "Type de contrat"):
                continue

            for sibling in label_node.next_siblings:
                sibling_name = getattr(sibling, "name", "")
                if sibling_name == "h3":
                    break
                if sibling_name in {"p", "span", "div"}:
                    value = self._clean_text(sibling.get_text(" ", strip=True))
                    normalized = self._normalize_contract_type_value(value)
                    if normalized:
                        return normalized

            block = label_node.find_parent("div")
            if block is None:
                return ""

            for child in block.find_all(["p", "span", "div"], recursive=False):
                if child == label_node or child.find("h3") is not None:
                    continue
                value = self._clean_text(child.get_text(" ", strip=True))
                normalized = self._normalize_contract_type_value(value)
                if normalized:
                    return normalized

            return ""

        return ""

    def _normalize_contract_type_value(self, value):
        normalized = self._normalize_label(value)
        if not normalized:
            return ""

        candidate = CONTRACT_TYPE_NORMALIZATION_MAP.get(normalized, "")
        if candidate not in CONTRACT_TYPE_ALLOWED_VALUES:
            return ""
        return candidate

    def _extract_detail_publication_date(self, detail_soup):
        if detail_soup is None:
            return ""

        candidates = []

        sidebar_date = self._extract_sidebar_label_value(detail_soup, "Date de publication")
        if sidebar_date:
            candidates.append(sidebar_date)

        jsonld_date = self._extract_publication_date_from_jsonld(detail_soup)
        if jsonld_date:
            candidates.append(jsonld_date)

        title_node = detail_soup.select_one("h1")
        title_context = title_node.find_parent(["section", "article", "main"]) if title_node is not None else None
        title_parent = title_node.parent if title_node is not None else None
        search_roots = [root for root in [title_context, title_parent, title_node] if root is not None]
        if not search_roots:
            search_roots = [detail_soup]

        selectors = [
            "i.fa-calendar-alt + span",
            "i.fas.fa-calendar-alt + span",
            "i.fa-calendar + span",
            "i[class*='calendar'] + span",
        ]
        for root in search_roots:
            for selector in selectors:
                for node in root.select(selector):
                    text = self._clean_text(node.get_text(" ", strip=True))
                    if text:
                        candidates.append(text)

        page_text = self._clean_text(" ".join(root.get_text(" ", strip=True) for root in search_roots))
        if page_text:
            page_text = re.split(r"offres?\s+similaires", page_text, maxsplit=1, flags=re.IGNORECASE)[0]
            match = re.search(
                r"publi[ée]e?\s+le\s+(\d{1,2}\s+(?:janvier|fevrier|février|mars|avril|mai|juin|juillet|aout|août|septembre|octobre|novembre|decembre|décembre)\s+\d{4})",
                page_text,
                flags=re.IGNORECASE,
            )
            if match:
                candidates.append(match.group(1))

        for candidate in candidates:
            parsed = self._parse_date_value(candidate)
            if parsed is not None:
                return parsed.isoformat()

        return ""

    def _extract_publication_date_from_jsonld(self, detail_soup):
        if detail_soup is None:
            return ""

        for script in detail_soup.find_all("script", attrs={"type": "application/ld+json"}):
            payload = self._parse_jsonld_payload(script)
            if not payload:
                continue

            for item in payload:
                if not isinstance(item, dict):
                    continue

                candidate = self._clean_text(item.get("datePosted") or item.get("datePublished"))
                if candidate:
                    return candidate

        return ""

    def _deduplicate_description_parts(self, parts):
        if not parts:
            return ""

        seen = set()
        cleaned_parts = []
        for part in parts:
            text = self._clean_text(part)
            if not text:
                continue
            if text in seen:
                continue
            seen.add(text)
            cleaned_parts.append(text)

        return "\n".join(cleaned_parts).strip()

    def _extract_structured_detail_fields(self, detail_soup):
        return {
            "reference": self._extract_sidebar_label_value(detail_soup, "Référence"),
            "published_at": self._extract_sidebar_label_value(detail_soup, "Date de publication"),
            "deadline": (
                self._extract_sidebar_label_value(detail_soup, "Date limite")
                or self._extract_sidebar_label_value(detail_soup, "Date d'expiration")
                or self._extract_sidebar_label_value(detail_soup, "Date d’expiration")
            ),
            "experience": self._extract_sidebar_label_value(detail_soup, "Expérience"),
            "education_level": self._extract_sidebar_label_value(detail_soup, "Niveau d'études"),
            "availability": self._extract_sidebar_label_value(detail_soup, "Disponibilité"),
            "salary": (
                self._extract_sidebar_label_value(detail_soup, "Salaire")
                or self._extract_sidebar_label_value(detail_soup, "Salaire proposé")
            ),
            "languages": self._extract_sidebar_languages(detail_soup),
            "company_sector": self._extract_company_info_value(detail_soup, "Secteur"),
            "company_size": self._extract_company_info_value(detail_soup, "Taille"),
        }

    def _find_detail_sidebar_container(self, detail_soup):
        if detail_soup is None:
            return None

        containers = detail_soup.select("div.p-6.space-y-4")
        if not containers:
            return None

        for container in containers:
            if container.find("h3") is not None:
                return container

        return containers[0]

    def _label_contains(self, text, expected_label):
        if not text or not expected_label:
            return False

        label_text = self._clean_text(text).lower().replace("’", "'")
        target = self._clean_text(expected_label).lower().replace("’", "'")
        return target in label_text

    def _extract_sidebar_label_value(self, detail_soup, label):
        sidebar = self._find_detail_sidebar_container(detail_soup)
        if sidebar is None:
            return None

        for label_node in sidebar.find_all("h3"):
            label_text = self._clean_text(label_node.get_text(" ", strip=True))
            if not self._label_contains(label_text, label):
                continue

            parent_div = label_node.find_parent("div")
            if parent_div is None:
                return None

            for candidate_tag in ("p", "span", "div"):
                value_node = parent_div.find(candidate_tag)
                if value_node is None or value_node == label_node:
                    continue
                value = self._clean_text(value_node.get_text(" ", strip=True))
                if value and self._normalize_label(value) != self._normalize_label(label_text):
                    return value

            parent_text = self._clean_text(parent_div.get_text(" ", strip=True))
            label_clean = self._clean_text(label_text)
            if parent_text and label_clean and parent_text.startswith(label_clean):
                remainder = self._clean_text(parent_text[len(label_clean):])
                if remainder:
                    return remainder

            return None

        return None

    def _extract_sidebar_languages(self, detail_soup):
        sidebar = self._find_detail_sidebar_container(detail_soup)
        if sidebar is None:
            return None

        for label_node in sidebar.find_all("h3"):
            label_text = self._clean_text(label_node.get_text(" ", strip=True))
            if not self._label_contains(label_text, "Langues"):
                continue

            parent_div = label_node.find_parent("div")
            if parent_div is None:
                return None

            value_node = parent_div.find("p")
            if value_node is None:
                return None

            languages = []
            for span_node in value_node.find_all("span"):
                language = self._clean_text(span_node.get_text(" ", strip=True))
                if language:
                    languages.append(language)

            return languages or None

        return None

    def _extract_company_info_value(self, detail_soup, label):
        if detail_soup is None:
            return None

        for span_node in detail_soup.find_all("span"):
            span_text = self._clean_text(span_node.get_text(" ", strip=True))
            if not self._label_contains(span_text, label):
                continue

            sibling_value = self._extract_inline_sibling_text(span_node)
            if sibling_value:
                return sibling_value

        return None

    def _extract_inline_sibling_text(self, node):
        if node is None:
            return None

        for sibling in node.next_siblings:
            sibling_name = getattr(sibling, "name", "")
            if sibling_name == "span":
                break

            if hasattr(sibling, "get_text"):
                value = self._clean_text(sibling.get_text(" ", strip=True))
            else:
                value = self._clean_text(sibling)

            if value:
                return value

        return None

    def _map_contract_to_opportunity_type(self, contract_value, title, description):
        normalized_contract = self._normalize_label(contract_value)
        normalized_title = self._normalize_label(title)
        normalized_description = self._normalize_label(description)

        # Strict policy: SAISONNIER is assigned only from explicit contract type.
        if normalized_contract == "saisonnier":
            return "SAISONNIER"

        combined_text = " ".join(
            part for part in (normalized_contract, normalized_title, normalized_description) if part
        )

        if "stage" in combined_text:
            return "STAGE"

        if not normalized_contract:
            logger.debug("Keejob contract type missing for title=%s", self._clean_text(title))

        # Keejob business rule: only STAGE or EMPLOI for opportunities.
        return "EMPLOI"

    def _extract_labeled_value(self, detail_soup, label, preferred_tags=("p", "span", "div")):
        if detail_soup is None:
            return ""

        target = self._normalize_label(label)
        if not target:
            return ""

        for header in detail_soup.find_all("h3"):
            header_label = self._normalize_label(header.get_text(" ", strip=True))
            if header_label != target:
                continue

            sibling = header.find_next_sibling()
            while sibling is not None:
                if getattr(sibling, "name", "") == "h3":
                    break
                value = self._extract_text_from_node(sibling, preferred_tags)
                if value:
                    return value
                sibling = sibling.find_next_sibling()

            for node in header.find_all_next():
                node_name = getattr(node, "name", "")
                if node_name == "h3":
                    break
                if node_name in preferred_tags:
                    value = self._clean_text(node.get_text(" ", strip=True))
                    if value:
                        return value

        return ""

    def _extract_text_from_node(self, node, preferred_tags):
        if node is None:
            return ""

        node_name = getattr(node, "name", "")
        if node_name in preferred_tags:
            text = self._clean_text(node.get_text(" ", strip=True))
            if text:
                return text

        for tag_name in preferred_tags:
            child = node.find(tag_name)
            if child is None:
                continue
            text = self._clean_text(child.get_text(" ", strip=True))
            if text:
                return text

        return ""

    def _normalize_label(self, value):
        cleaned = self._clean_text(value).lower()
        cleaned = unicodedata.normalize("NFKD", cleaned)
        cleaned = "".join(ch for ch in cleaned if not unicodedata.combining(ch))
        cleaned = re.sub(r"[^a-z0-9]+", " ", cleaned)
        return re.sub(r"\s+", " ", cleaned).strip()

    def _sanitize_company_candidate(self, value):
        text = self._clean_text(value)
        if not text:
            return ""

        # Keejob fallback blocks can append location/date after the company.
        text = re.split(r"\bpubli[ée]e?\s+le\b", text, maxsplit=1, flags=re.IGNORECASE)[0]
        text = text.strip(" -|,;")

        normalized = self._normalize_label(text)
        if normalized.startswith("entreprise anonyme"):
            return "Entreprise Anonyme"

        return text

    def _is_valid_record(self, record):
        title = self._clean_text(record.get("title"))
        description = self._clean_text(record.get("description"))
        url = self._clean_text(record.get("url"))

        if not title:
            logger.info("Skipping record with invalid title: %r", title)
            return False
        if not description:
            logger.info("Skipping record with empty description (url=%s)", url or "N/A")
            return False
        if not url:
            logger.info("Skipping record with invalid URL: %r", url)
            return False
        return True

    def _is_valid_url(self, value):
        if not value:
            return False
        parsed = urlparse(value)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)

    def _rate_limit_delay(self):
        delay = random.uniform(self.min_delay, self.max_delay)
        time.sleep(delay)

    def _normalize_publication_date(self, raw_value):
        text = self._clean_text(raw_value).lower()
        today = date.today()

        if not text:
            return today.isoformat()

        if "aujourd" in text:
            return today.isoformat()
        if "hier" in text:
            return (today - timedelta(days=1)).isoformat()

        day_match = re.search(r"(\d+)\s*jour", text)
        if day_match:
            days = int(day_match.group(1))
            return (today - timedelta(days=days)).isoformat()

        month_match = re.search(r"(\d+)\s*mois", text)
        if month_match:
            months = int(month_match.group(1))
            return (today - timedelta(days=months * 30)).isoformat()

        year_match = re.search(r"(\d+)\s*an", text)
        if year_match:
            years = int(year_match.group(1))
            return (today - timedelta(days=years * 365)).isoformat()

        parsed_absolute = self._parse_date_value(text)
        if parsed_absolute is not None:
            return parsed_absolute.isoformat()

        # Absolute date formats
        absolute_patterns = [
            r"(\d{4})-(\d{2})-(\d{2})",
            r"(\d{2})/(\d{2})/(\d{4})",
            r"(\d{2})-(\d{2})-(\d{4})",
        ]
        for pattern in absolute_patterns:
            match = re.search(pattern, text)
            if not match:
                continue

            if pattern.startswith(r"(\d{4})"):
                yyyy, mm, dd = match.groups()
                return f"{yyyy}-{mm}-{dd}"

            dd, mm, yyyy = match.groups()
            return f"{yyyy}-{mm}-{dd}"

        return today.isoformat()

    def _clean_text(self, value):
        if value is None:
            return ""
        text = str(value).replace("\xa0", " ")
        return re.sub(r"\s+", " ", text).strip()

    def _normalize_company(self, name):
        normalized = "" if name is None else str(name).replace("\xa0", " ").strip()
        if not normalized:
            return ""
        normalized = re.sub(r"[/|\\]+", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip().lower()
        return normalized

    def _clean_description(self, text):
        cleaned, raw = clean_description_for_ml(text)
        return cleaned, raw

    def _clean_location(self, location):
        text = self._clean_text(location)
        if not text:
            return ""

        parts = [part.strip() for part in text.split(",") if part and part.strip()]
        filtered_parts = []
        for part in parts:
            normalized = self._normalize_label(part)
            if normalized in {"tunisie", "tunisia", "tn"}:
                continue
            filtered_parts.append(part)

        if filtered_parts:
            return ", ".join(filtered_parts)
        return text

    def _enrich_location_from_description(self, location, description):
        base_location = self._clean_text(location)
        if not base_location or "," in base_location:
            return base_location

        text = self._clean_text(description)
        if not text:
            return base_location

        city_pattern = re.escape(base_location)
        patterns = [
            rf"\bzone\s+industrielle\s+([A-Za-zÀ-ÖØ-öø-ÿ'’\-]{{2,}})\s+{city_pattern}\b",
            rf"\b(?:poste|offre)\s+bas[ée]e?\s+[aà]\s+(?:la\s+)?(?:zone\s+industrielle\s+)?([A-Za-zÀ-ÖØ-öø-ÿ'’\-]{{2,}})\s+{city_pattern}\b",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if not match:
                continue

            locality = self._clean_text(match.group(1))
            if not locality:
                continue

            if self._normalize_label(locality) == self._normalize_label(base_location):
                continue

            return f"{locality.title()}, {base_location}"

        return base_location
