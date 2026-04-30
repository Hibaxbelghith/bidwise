import json
import logging
import os
import random
import re
import time
import unicodedata
from datetime import date, datetime
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..scraper_base import BaseOpportunityScraper
from ..scraper_utils import (
    FETCH_DETAILS,
    MAX_DESCRIPTION_LENGTH,
    SCRAPER_TIMEOUT_DEFAULT,
    clean_description_for_ml,
    clean_location_for_ml,
    infer_opportunity_type,
)


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


def _get_env_int(name, default):
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        logger.warning("Invalid %s=%r, falling back to %s", name, value, default)
        return default


def _get_env_float(name, default):
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        logger.warning("Invalid %s=%r, falling back to %s", name, value, default)
        return default


def _get_env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


SCRAPER_TIMEOUT = _get_env_int("SCRAPER_TIMEOUT", SCRAPER_TIMEOUT_DEFAULT)
SCRAPER_MIN_DELAY = _get_env_float("SCRAPER_MIN_DELAY", 0.8)
SCRAPER_MAX_DELAY = _get_env_float("SCRAPER_MAX_DELAY", 1.5)
EMPLOITUNISIE_MAX_PAGES = _get_env_int("EMPLOITUNISIE_MAX_PAGES", 1000)
EMPLOITUNISIE_MAX_RECORDS = _get_env_int("EMPLOITUNISIE_MAX_RECORDS", 1000)
EMPLOITUNISIE_PAGE_SIZE = _get_env_int("EMPLOITUNISIE_PAGE_SIZE", 20)
EMPLOITUNISIE_STAGE_ONLY = _get_env_bool("EMPLOITUNISIE_STAGE_ONLY", False)


class EmploiTunisieScraper(BaseOpportunityScraper):
    source_name = "EmploiTunisie"
    source_url = "https://www.emploitunisie.com"
    source_type = "SITE_EMPLOI"

    LISTING_BASE_URL = "https://www.emploitunisie.com/recherche-jobs-tunisie"
    STAGE_LISTING_BASE_URL = "https://www.emploitunisie.com/recherche-jobs-tunisie/stage"
    DEFAULT_TIMEOUT = SCRAPER_TIMEOUT
    DEFAULT_MAX_PAGES = EMPLOITUNISIE_MAX_PAGES

    LISTING_CARD_SELECTORS = [
        "div.card.card-job",
        "div.card-job",
        "div.card[data-href*='/offre-emploi-tunisie/']",
    ]
    JOB_LINK_SELECTORS = [
        "div.card-job-detail h3 a[href*='/offre-emploi-tunisie/']",
        "h3 a[href*='/offre-emploi-tunisie/']",
    ]
    TITLE_SELECTORS = [
        "div.card-job-detail h3 a",
        "h3 a",
    ]
    COMPANY_SELECTORS = [
        "a.card-job-company.company-name",
        "a.card-job-company",
        "div.card-job-detail a.company-name",
    ]
    LISTING_DESCRIPTION_SELECTORS = [
        "div.card-job-description p",
        ".card-job-description p",
    ]
    DETAIL_DESCRIPTION_SELECTORS = [
        "article.page-application-content section .job-description",
        "article.page-application-content .job-description",
        ".page-application-content .job-description",
    ]
    DETAIL_TITLE_SELECTORS = [
        "article.page-application-content section h3.job-title",
        "h3.job-title",
    ]
    DETAIL_COMPANY_SELECTORS = [
        "div.card-block-company h3 a",
    ]

    SUMMARY_EXPERIENCE_CLASS_TOKENS = ("chart",)
    SUMMARY_EDUCATION_CLASS_TOKENS = ("graduation",)
    SUMMARY_CONTRACT_CLASS_TOKENS = ("file signature", "signature")
    SUMMARY_LOCATION_CLASS_TOKENS = ("map marker", "marker", "location", "pin")
    SUMMARY_JOB_CATEGORY_CLASS_TOKENS = ("briefcase", "suitcase", "industry", "metier")

    def __init__(
        self,
        max_pages=DEFAULT_MAX_PAGES,
        timeout=DEFAULT_TIMEOUT,
        min_delay=SCRAPER_MIN_DELAY,
        max_delay=SCRAPER_MAX_DELAY,
        max_records=EMPLOITUNISIE_MAX_RECORDS,
        fetch_details=FETCH_DETAILS,
        page_size=EMPLOITUNISIE_PAGE_SIZE,
        stage_only=EMPLOITUNISIE_STAGE_ONLY,
    ):
        self.max_pages = max(1, int(max_pages))
        self.timeout = timeout
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.max_records = max_records if max_records and max_records > 0 else None
        self.fetch_details = fetch_details
        self.page_size = max(1, int(page_size))
        self.stage_only = bool(stage_only)
        self.listing_base_url = self.STAGE_LISTING_BASE_URL if self.stage_only else self.LISTING_BASE_URL
        self.max_description_length = MAX_DESCRIPTION_LENGTH
        self.blocked = False
        self.last_page_failed = False

        if self.min_delay > self.max_delay:
            self.min_delay, self.max_delay = self.max_delay, self.min_delay

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
        empty_pages_count = 0
        failure_count = 0

        for page_index in range(self.max_pages):
            page_records = []
            self.last_page_failed = False
            listing_url = self._build_listing_url(page_index)
            listing_soup = self._safe_get_soup(listing_url)
            if self.blocked:
                return
            if listing_soup is None:
                self.last_page_failed = True
                failure_count += 1
                logger.warning("No listing HTML for page=%s url=%s", page_index + 1, listing_url)
                yield page_records
                if failure_count >= 3:
                    logger.info("[emploi_tn] stopping due to failures")
                    break
                continue
            failure_count = 0

            cards = self._extract_listing_cards(listing_soup)
            logger.info(
                "EmploiTunisie page=%s detected %s candidate cards",
                page_index + 1,
                len(cards),
            )

            for card in cards:
                url = self._extract_url(card)
                if not url:
                    skipped_records += 1
                    logger.info("Skipping listing card without job URL")
                    continue
                if url in seen_urls:
                    skipped_records += 1
                    logger.info("Skipping duplicate URL in same run: %s", url)
                    continue
                seen_urls.add(url)

                # NEW
                structured = self._extract_structured_fields(card)

                listing_title = self._extract_title(card, None)
                listing_description = self._extract_listing_description(card)
                listing_organization = self._extract_organization(card, None)
                # NEW
                listing_location = self._extract_location(card, None) or structured["location"]
                listing_publication_date, listing_date_confidence = self._extract_publication_date(card, None)

                # Structured extraction for EmploiTunisie depends on detail page blocks.
                detail_soup = None
                needs_details = True
                if needs_details:
                    detail_soup = self._safe_get_soup(url)
                    if self.blocked:
                        yield page_records
                        return
                    if detail_soup is None and self.fetch_details:
                        skipped_records += 1
                        logger.warning("Skipping URL because detail page is unavailable: %s", url)
                        continue

                detail_description_html = self._extract_detail_description_html(detail_soup)
                detail_structured = self._extract_detail_structured_fields(detail_soup)
                company_meta = self._extract_company_metadata(detail_soup)
                detail_qualifications = self._extract_detail_qualifications(detail_soup)

                title = self._extract_title(card, detail_soup) or listing_title
                description = self._extract_detail_description(detail_soup, detail_description_html) or listing_description
                organization = self._extract_organization(card, detail_soup) or listing_organization
                location = self._clean_location(
                    self._first_non_empty(
                        self._extract_location(card, detail_soup),
                        listing_location,
                        detail_structured["city"],
                        detail_structured["location_region"],
                    )
                )
                publication_date, date_confidence = self._extract_publication_date(card, detail_soup)
                if not publication_date:
                    publication_date = listing_publication_date
                    date_confidence = listing_date_confidence
                description, raw_description = self._clean_description(description)
                inferred_type = infer_opportunity_type(
                    title,
                    description,
                    listing_title,
                    listing_description,
                )

                record = {
                    "title": title,
                    "description": description,
                    "description_html": detail_description_html or None,
                    "organization": organization,
                    "location": location,
                    # NEW
                    "experience": detail_structured["experience"] or structured["experience"] or None,
                    "education_level": detail_structured["education_level"] or structured["education_level"] or None,
                    "contract_type": detail_structured["contract_type"] or structured["contract_type"] or None,
                    "salary": detail_structured["salary"] or None,
                    "location_region": detail_structured["location_region"] or structured["location"] or None,
                    "city": detail_structured["city"] or None,
                    "remote": detail_structured["remote"] or None,
                    "positions": detail_structured["positions"] or None,
                    "management": detail_structured["management"] or None,
                    "skills": detail_structured["skills"] or structured["skills"] or None,
                    "job_qualifications": detail_qualifications or None,
                    "job_category": detail_structured["job_category"] or structured["job_category"] or None,
                    "company_sector": detail_structured["company_sector"] or None,
                    "company_logo": company_meta["company_logo"] or None,
                    "company_website": company_meta["company_website"] or None,
                    "company_description": company_meta["company_description"] or None,
                    "type_opportunite": inferred_type,
                    "type": inferred_type,
                    "statut": "ACTIVE",
                    "status": "ACTIVE",
                    "publication_date": publication_date,
                    "date_confidence": date_confidence,
                    "url": url,
                    "source_name": self.source_name,
                    "source_url": self.source_url,
                    "source_type": self.source_type,
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
                        "EmploiTunisie scraper extracted %s records (skipped: %s, pages scanned: %s)",
                        len(records),
                        skipped_records,
                        page_index + 1,
                    )
                    yield page_records
                    return
            if len(cards) < self.page_size:
                logger.info(
                    "EmploiTunisie page=%s has %s cards (< page_size=%s), stopping early.",
                    page_index + 1,
                    len(cards),
                    self.page_size,
                )
                yield page_records
                break
            yield page_records
            if page_records:
                empty_pages_count = 0
            else:
                empty_pages_count += 1
                if empty_pages_count >= 2:
                    logger.info("[emploi_tn] stopping early at page=%s (no new data)", page_index + 1)
                    break

        logger.info(
            "EmploiTunisie scraper extracted %s records (skipped: %s, pages: %s)",
            len(records),
            skipped_records,
            self.max_pages,
        )

    def _build_listing_url(self, page_index):
        if page_index <= 0:
            return self.listing_base_url
        return f"{self.listing_base_url}?page={page_index}"

    def _safe_get_soup(self, url):
        try:
            logger.info(f"Fetching URL: {url} (timeout={self.timeout})")
            self._rate_limit_delay()
            response = self.session.get(url, timeout=self.timeout)
            logger.info(f"Fetched URL: {url} (status={response.status_code})")
            if response.status_code == 403:
                self.blocked = True
                logger.warning("[emploi_tn] blocked (403), stopping")
                return None
            if response.status_code != 200:
                logger.warning("Request failed for %s status=%s", url, response.status_code)
                return None
            response.raise_for_status()
            return BeautifulSoup(response.text, "html.parser")
        except requests.RequestException as exc:
            logger.warning("Request failed for %s: %s", url, exc)
            return None

    def _extract_listing_cards(self, soup):
        cards = []
        for selector in self.LISTING_CARD_SELECTORS:
            matches = soup.select(selector)
            if matches:
                cards.extend(matches)

        filtered = []
        for card in cards:
            if card.select_one(self.JOB_LINK_SELECTORS[0]) or card.select_one(self.JOB_LINK_SELECTORS[1]):
                filtered.append(card)
        return filtered

    def _extract_url(self, card):
        data_href = self._clean_text(card.get("data-href"))
        if self._is_valid_url(data_href):
            return data_href

        for selector in self.JOB_LINK_SELECTORS:
            node = card.select_one(selector)
            if not node:
                continue
            href = self._clean_text(node.get("href"))
            if not href:
                continue
            return urljoin(self.source_url, href)
        return ""

    def _extract_title(self, card, detail_soup):
        listing_title = self._extract_first_text(card, self.TITLE_SELECTORS)
        detail_title = self._extract_first_text(detail_soup, self.DETAIL_TITLE_SELECTORS) if detail_soup else ""

        title = detail_title or listing_title
        if self._normalize_token(title).startswith("poste propose :"):
            title = title.split(":", 1)[1].strip()
        return title

    def _extract_organization(self, card, detail_soup):
        listing_company = self._extract_first_text(card, self.COMPANY_SELECTORS)
        detail_company = self._extract_first_text(detail_soup, self.DETAIL_COMPANY_SELECTORS) if detail_soup else ""
        return listing_company or detail_company

    def _extract_detail_description_html(self, detail_soup):
        if detail_soup is None:
            return ""

        for selector in self.DETAIL_DESCRIPTION_SELECTORS:
            node = detail_soup.select_one(selector)
            if node is None:
                continue

            raw_html = node.decode_contents(formatter="html")
            cleaned = self._sanitize_description_html(raw_html)
            if cleaned:
                return cleaned

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

    def _extract_detail_description(self, detail_soup, description_html=""):
        if detail_soup is None:
            return ""

        html_payload = self._clean_text(description_html)
        if html_payload:
            html_soup = BeautifulSoup(f"<div>{html_payload}</div>", "html.parser")
            wrapper = html_soup.find("div")
            if wrapper is not None:
                text = self._clean_text(wrapper.get_text("\n", strip=True))
                if text:
                    return text

        for selector in self.DETAIL_DESCRIPTION_SELECTORS:
            node = detail_soup.select_one(selector)
            if not node:
                continue
            text = self._clean_text(node.get_text("\n", strip=True))
            if text:
                return text
        return ""

    def _extract_listing_description(self, card):
        return self._extract_first_text(card, self.LISTING_DESCRIPTION_SELECTORS)

    def _extract_location(self, card, detail_soup):
        location = self._extract_location_from_listing(card)
        if location:
            return location
        if detail_soup is None:
            return ""
        return self._extract_location_from_detail(detail_soup)

    def _extract_location_from_listing(self, card):
        for li in card.select("div.card-job-detail ul li"):
            text = self._clean_text(li.get_text(" ", strip=True))
            normalized = self._normalize_token(text)
            if "region de" in normalized:
                strong = li.select_one("strong")
                if strong:
                    strong_text = self._clean_text(strong.get_text(" ", strip=True))
                    if strong_text:
                        return strong_text
                if ":" in text:
                    return self._clean_text(text.split(":", 1)[1])
        return ""

    def _extract_location_from_detail(self, detail_soup):
        for li in detail_soup.select("article.page-application-content ul.arrow-list li"):
            label_node = li.select_one("strong")
            if not label_node:
                continue
            label = self._normalize_token(label_node.get_text(" ", strip=True))
            if label.startswith("region"):
                value_node = li.select_one("span")
                if value_node:
                    value = self._clean_text(value_node.get_text(" ", strip=True))
                    if value:
                        return value
                text = self._clean_text(li.get_text(" ", strip=True))
                if ":" in text:
                    return self._clean_text(text.split(":", 1)[1])
        return ""

    def _extract_publication_date(self, card, detail_soup):
        time_node = card.select_one("time[datetime]")
        if time_node:
            raw_value = self._clean_text(time_node.get("datetime")) or self._clean_text(time_node.get_text(" ", strip=True))
            parsed = self._parse_date_to_iso(raw_value)
            if parsed:
                return parsed, "EXACT"

        fallback_time_node = card.select_one("time")
        if fallback_time_node:
            parsed = self._parse_date_to_iso(fallback_time_node.get_text(" ", strip=True))
            if parsed:
                return parsed, "EXACT"

        jsonld_date = self._extract_date_from_jsonld(detail_soup) if detail_soup is not None else ""
        if jsonld_date:
            parsed = self._parse_date_to_iso(jsonld_date)
            if parsed:
                return parsed, "EXACT"

        return date.today().isoformat(), "FALLBACK"

    # NEW
    def _extract_structured_fields(self, card):
        structured = {
            "experience": None,
            "education_level": None,
            "contract_type": None,
            "location": None,
            "skills": None,
            "job_category": None,
        }

        try:
            li_nodes = card.select("div.card-job-detail ul li")
            if not li_nodes:
                li_nodes = card.select("ul li")

            for li in li_nodes:
                text = self._clean_text(li.get_text(" ", strip=True))
                if not text:
                    continue

                normalized_text = self._normalize_match_token(text)
                class_token = self._normalize_match_token(" ".join(li.get("class", [])))
                strong_node = li.select_one("strong")
                if strong_node:
                    value = self._clean_text(strong_node.get_text(" ", strip=True))
                else:
                    # fallback brut
                    if ":" in text:
                        value = self._clean_text(text.split(":", 1)[1])
                    else:
                        value = text

                if not value:
                    continue

                value_token = self._normalize_match_token(value)

                if (
                    self._contains_any_token(class_token, self.SUMMARY_EDUCATION_CLASS_TOKENS)
                    or normalized_text.startswith("niveau d etudes")
                    or self._looks_education(value_token)
                ):
                    structured["education_level"] = value
                    continue

                if (
                    self._contains_any_token(class_token, self.SUMMARY_EXPERIENCE_CLASS_TOKENS)
                    or normalized_text.startswith("niveau d experience")
                    or self._looks_experience(value_token)
                ):
                    structured["experience"] = value
                    continue

                if (
                    self._contains_any_token(class_token, self.SUMMARY_CONTRACT_CLASS_TOKENS)
                    or normalized_text.startswith("contrat propose")
                    or self._looks_contract(value_token)
                ):
                    structured["contract_type"] = value
                    continue

                if (
                    self._contains_any_token(class_token, self.SUMMARY_LOCATION_CLASS_TOKENS)
                    or normalized_text.startswith("region")
                ):
                    structured["location"] = value
                    continue

                if (
                    self._contains_any_token(class_token, self.SUMMARY_JOB_CATEGORY_CLASS_TOKENS)
                    and structured["job_category"] is None
                ):
                    structured["job_category"] = value
                    continue

                if normalized_text.startswith("competences"):
                    skills = [self._clean_text(item) for item in value.split("-")]
                    skills = [item for item in skills if item]
                    structured["skills"] = skills or None
        except Exception:
            return structured

        return structured

    def _empty_detail_structured_schema(self):
        return {
            "experience": None,
            "education_level": None,
            "contract_type": None,
            "salary": None,
            "location_region": None,
            "city": None,
            "remote": None,
            "positions": None,
            "management": None,
            "skills": None,
            "job_category": None,
            "company_sector": None,
        }

    def _normalize_match_token(self, value):
        token = self._normalize_token(value)
        token = re.sub(r"[^a-z0-9\s]", " ", token)
        return re.sub(r"\s+", " ", token).strip()

    def _contains_any_token(self, haystack, needles):
        if not haystack:
            return False
        return any(needle in haystack for needle in needles)

    def _looks_contract(self, token):
        contract_tokens = (
            "cdi",
            "cdd",
            "stage",
            "sivp",
            "freelance",
            "independant",
            "alternance",
            "interim",
            "temps plein",
            "temps partiel",
            "pfe",
        )
        return any(marker in token for marker in contract_tokens)

    def _looks_experience(self, token):
        if not token:
            return False
        if "experience" in token:
            return True
        if "debutant" in token:
            return True
        if "moins d un an" in token:
            return True
        return False

    def _looks_education(self, token):
        return "bac" in token

    def _extract_structured_fields_from_summary(self, detail_soup):
        structured = self._empty_detail_structured_schema()
        if detail_soup is None:
            return structured

        try:
            for li in detail_soup.select("div.card-block-summary ul li"):
                value = self._clean_text(li.get_text(" ", strip=True))
                if not value:
                    continue

                token = self._normalize_match_token(value)
                class_token = self._normalize_match_token(" ".join(li.get("class", [])))
                if not token:
                    continue

                if (
                    structured["experience"] is None
                    and (
                        self._contains_any_token(class_token, self.SUMMARY_EXPERIENCE_CLASS_TOKENS)
                        or self._looks_experience(token)
                    )
                ):
                    structured["experience"] = value
                    continue

                if (
                    structured["education_level"] is None
                    and (
                        self._contains_any_token(class_token, self.SUMMARY_EDUCATION_CLASS_TOKENS)
                        or self._looks_education(token)
                    )
                ):
                    structured["education_level"] = value
                    continue

                if (
                    structured["contract_type"] is None
                    and (
                        self._contains_any_token(class_token, self.SUMMARY_CONTRACT_CLASS_TOKENS)
                        or self._looks_contract(token)
                    )
                ):
                    structured["contract_type"] = value
                    continue

                if structured["remote"] is None and token in {"oui", "non"}:
                    structured["remote"] = value
                    continue

                if (
                    structured["location_region"] is None
                    and self._contains_any_token(class_token, self.SUMMARY_LOCATION_CLASS_TOKENS)
                ):
                    structured["location_region"] = value
                    continue

                if (
                    structured["job_category"] is None
                    and self._contains_any_token(class_token, self.SUMMARY_JOB_CATEGORY_CLASS_TOKENS)
                ):
                    structured["job_category"] = value
        except Exception:
            return structured

        return structured

    def _extract_arrow_list_value(self, li, label_text):
        span = li.select_one("span")
        if span:
            value = self._clean_text(span.get_text(" ", strip=True))
            if value:
                return value

        full_text = self._clean_text(li.get_text(" ", strip=True))
        if not full_text:
            return ""

        if ":" in full_text:
            return self._clean_text(full_text.split(":", 1)[1])

        label_clean = self._clean_text(label_text)
        if label_clean and full_text.startswith(label_clean):
            return self._clean_text(full_text[len(label_clean):].lstrip(": "))

        return ""

    def _extract_structured_fields_from_detail_block(self, detail_soup):
        structured = self._empty_detail_structured_schema()
        if detail_soup is None:
            return structured

        try:
            for li in detail_soup.select("ul.arrow-list li"):
                label_node = li.select_one("strong")
                if label_node is None:
                    continue

                label_text = self._clean_text(label_node.get_text(" ", strip=True))
                label = self._normalize_match_token(label_text)
                if not label:
                    continue

                value = self._extract_arrow_list_value(li, label_text)
                if not value:
                    continue

                if "type de contrat" in label or label.startswith("contrat"):
                    structured["contract_type"] = value
                    continue
                if "salaire" in label:
                    structured["salary"] = value
                    continue
                if label.startswith("region") or "region" in label:
                    structured["location_region"] = value
                    continue
                if label.startswith("ville") or "ville" in label:
                    structured["city"] = value
                    continue
                if "experience" in label:
                    structured["experience"] = value
                    continue
                if "etudes" in label or "etude" in label:
                    structured["education_level"] = value
                    continue
                if "travail a distance" in label or "teletravail" in label:
                    structured["remote"] = value
                    continue
                if "nombre de poste" in label:
                    structured["positions"] = value
                    continue
                if "management" in label and "equipe" in label:
                    structured["management"] = value
                    continue
                if "metier" in label:
                    structured["job_category"] = value
                    continue
                if "secteur" in label:
                    structured["company_sector"] = value
        except Exception:
            return structured

        return structured

    def _extract_structured_skills_from_detail(self, detail_soup):
        if detail_soup is None:
            return None

        try:
            skills = []
            for li in detail_soup.select("ul.skills li"):
                value = self._clean_text(li.get_text(" ", strip=True))
                if value and value not in skills:
                    skills.append(value)
            return skills or None
        except Exception:
            return None

    def _extract_detail_structured_fields(self, detail_soup):
        structured = self._empty_detail_structured_schema()
        if detail_soup is None:
            return structured

        summary_values = self._extract_structured_fields_from_summary(detail_soup)
        detail_values = self._extract_structured_fields_from_detail_block(detail_soup)

        for field in (
            "experience",
            "education_level",
            "contract_type",
            "salary",
            "location_region",
            "city",
            "remote",
            "positions",
            "management",
            "job_category",
            "company_sector",
        ):
            structured[field] = detail_values.get(field) or summary_values.get(field) or None

        structured["skills"] = self._extract_structured_skills_from_detail(detail_soup)
        return structured

    def _extract_detail_qualifications(self, detail_soup):
        if detail_soup is None:
            return ""

        try:
            node = detail_soup.select_one(".job-qualifications")
            if node is None:
                return ""

            items = []
            seen = set()
            for li in node.select("li"):
                value = self._clean_text(li.get_text(" ", strip=True))
                if not value or value in seen:
                    continue
                seen.add(value)
                items.append(value)

            if items:
                return "\n".join(items)

            return self._clean_text(node.get_text("\n", strip=True))
        except Exception:
            return ""

    def _extract_company_metadata(self, detail_soup):
        metadata = {
            "company_logo": None,
            "company_website": None,
            "company_description": None,
        }
        if detail_soup is None:
            return metadata

        try:
            for img in detail_soup.select("div.card-block-company img[src], .card-block-company img[src], .company-logo img[src]"):
                src = self._clean_text(img.get("src"))
                if src:
                    metadata["company_logo"] = urljoin(self.source_url, src)
                    break

            for section in detail_soup.select("div.card.card-block.card-block-summary"):
                title_node = section.select_one("h2.card-block-title")
                title_token = self._normalize_match_token(title_node.get_text(" ", strip=True) if title_node else "")
                if "entreprise" not in title_token:
                    continue

                if metadata["company_website"] is None:
                    for anchor in section.select("a[href]"):
                        href = self._clean_text(anchor.get("href"))
                        if not href:
                            continue
                        if "emploitunisie.com" in href:
                            continue
                        metadata["company_website"] = urljoin(self.source_url, href)
                        break

                if metadata["company_description"] is None:
                    paragraphs = []
                    for paragraph in section.select("p"):
                        text = self._clean_text(paragraph.get_text(" ", strip=True))
                        if text:
                            paragraphs.append(text)
                    if paragraphs:
                        metadata["company_description"] = "\n".join(paragraphs)
                break
        except Exception:
            return metadata

        return metadata

    def _extract_date_from_jsonld(self, soup):
        if soup is None:
            return ""
        for script in soup.select("script[type='application/ld+json']"):
            payload = self._clean_text(script.string or script.get_text(" ", strip=True))
            if not payload:
                continue
            try:
                parsed_json = json.loads(payload)
            except json.JSONDecodeError:
                continue

            objects = parsed_json if isinstance(parsed_json, list) else [parsed_json]
            for item in objects:
                if not isinstance(item, dict):
                    continue
                date_posted = self._clean_text(item.get("datePosted"))
                if date_posted:
                    return date_posted
        return ""

    def _parse_date_to_iso(self, raw_value):
        text = self._clean_text(raw_value)
        if not text:
            return ""

        if "T" in text and len(text) >= 10:
            text = text[:10]

        formats = ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%Y/%m/%d")
        for fmt in formats:
            try:
                return datetime.strptime(text, fmt).date().isoformat()
            except ValueError:
                continue
        return ""

    def _extract_first_text(self, node, selectors):
        if node is None:
            return ""
        for selector in selectors:
            element = node.select_one(selector)
            if element:
                text = self._clean_text(element.get_text(" ", strip=True))
                if text:
                    return text
        return ""

    def _first_non_empty(self, *values):
        for value in values:
            cleaned = self._clean_text(value)
            if cleaned:
                return cleaned
        return ""

    def _is_valid_record(self, record):
        title = self._clean_text(record.get("title"))
        description = self._clean_text(record.get("description"))
        url = self._clean_text(record.get("url"))

        if not title or len(title) < 5:
            logger.info("Skipping record with invalid title: %r", title)
            return False
        if not description:
            logger.info("Skipping record with empty description (url=%s)", url or "N/A")
            return False
        if not self._is_valid_url(url):
            logger.info("Skipping record with invalid URL: %r", url)
            return False
        return True

    def _needs_detail_fetch(self, title, description, publication_date):
        return not (self._clean_text(title) and self._clean_text(description) and self._clean_text(publication_date))

    def _clean_description(self, text):
        return clean_description_for_ml(text)

    def _clean_location(self, location):
        return clean_location_for_ml(location)

    def _is_valid_url(self, value):
        if not value:
            return False
        parsed = urlparse(value)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)

    def _rate_limit_delay(self):
        delay = random.uniform(self.min_delay, self.max_delay)
        time.sleep(delay)

    def _clean_text(self, value):
        if value is None:
            return ""
        return re.sub(r"\s+", " ", str(value)).strip()

    def _normalize_token(self, value):
        text = self._clean_text(value).lower()
        text = unicodedata.normalize("NFKD", text)
        text = "".join(ch for ch in text if not unicodedata.combining(ch))
        return text
