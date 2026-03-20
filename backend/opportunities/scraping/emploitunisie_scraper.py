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

from .scraper_base import BaseOpportunityScraper
from .scraper_utils import (
    FETCH_DETAILS,
    MAX_DESCRIPTION_LENGTH,
    SCRAPER_TIMEOUT_DEFAULT,
    clean_description_for_ml,
    clean_location_for_ml,
)


logger = logging.getLogger(__name__)


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


SCRAPER_TIMEOUT = _get_env_int("SCRAPER_TIMEOUT", SCRAPER_TIMEOUT_DEFAULT)
SCRAPER_MIN_DELAY = _get_env_float("SCRAPER_MIN_DELAY", 0.8)
SCRAPER_MAX_DELAY = _get_env_float("SCRAPER_MAX_DELAY", 1.5)
EMPLOITUNISIE_MAX_PAGES = _get_env_int("EMPLOITUNISIE_MAX_PAGES", 5)
EMPLOITUNISIE_MAX_RECORDS = _get_env_int("EMPLOITUNISIE_MAX_RECORDS", 0)
EMPLOITUNISIE_PAGE_SIZE = _get_env_int("EMPLOITUNISIE_PAGE_SIZE", 20)


class EmploiTunisieScraper(BaseOpportunityScraper):
    source_name = "EmploiTunisie"
    source_url = "https://www.emploitunisie.com"
    source_type = "SITE_EMPLOI"

    LISTING_BASE_URL = "https://www.emploitunisie.com/recherche-jobs-tunisie"
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

    def __init__(
        self,
        max_pages=DEFAULT_MAX_PAGES,
        timeout=DEFAULT_TIMEOUT,
        min_delay=SCRAPER_MIN_DELAY,
        max_delay=SCRAPER_MAX_DELAY,
        max_records=EMPLOITUNISIE_MAX_RECORDS,
        fetch_details=FETCH_DETAILS,
        page_size=EMPLOITUNISIE_PAGE_SIZE,
    ):
        self.max_pages = max(1, min(int(max_pages), self.DEFAULT_MAX_PAGES))
        self.timeout = timeout
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.max_records = max_records if max_records and max_records > 0 else None
        self.fetch_details = fetch_details
        self.page_size = max(1, int(page_size))
        self.max_description_length = MAX_DESCRIPTION_LENGTH

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
        seen_urls = set()
        skipped_records = 0

        for page_index in range(self.max_pages):
            listing_url = self._build_listing_url(page_index)
            listing_soup = self._safe_get_soup(listing_url)
            if listing_soup is None:
                logger.warning("No listing HTML for page=%s url=%s", page_index + 1, listing_url)
                continue

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

                listing_title = self._extract_title(card, None)
                listing_description = self._extract_listing_description(card)
                listing_organization = self._extract_organization(card, None)
                listing_location = self._extract_location(card, None)
                listing_publication_date = self._extract_publication_date(card, None)

                detail_soup = None
                needs_details = self.fetch_details or self._needs_detail_fetch(
                    listing_title,
                    listing_description,
                    listing_publication_date,
                )
                if needs_details:
                    detail_soup = self._safe_get_soup(url)
                    if detail_soup is None and self.fetch_details:
                        skipped_records += 1
                        logger.warning("Skipping URL because detail page is unavailable: %s", url)
                        continue

                title = self._extract_title(card, detail_soup) or listing_title
                description = self._extract_detail_description(detail_soup) or listing_description
                organization = self._extract_organization(card, detail_soup) or listing_organization
                location = self._clean_location(
                    self._first_non_empty(
                        self._extract_location(card, detail_soup),
                        listing_location,
                    )
                )
                publication_date = self._extract_publication_date(card, detail_soup) or listing_publication_date
                description, raw_description = self._clean_description(description)

                record = {
                    "title": title,
                    "description": description,
                    "organization": organization,
                    "location": location,
                    "publication_date": publication_date,
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
                if self.max_records and len(records) >= self.max_records:
                    logger.info("Reached max_records=%s, stopping early", self.max_records)
                    logger.info(
                        "EmploiTunisie scraper extracted %s records (skipped: %s, pages scanned: %s)",
                        len(records),
                        skipped_records,
                        page_index + 1,
                    )
                    return records
            if len(cards) < self.page_size:
                logger.info(
                    "EmploiTunisie page=%s has %s cards (< page_size=%s), stopping early.",
                    page_index + 1,
                    len(cards),
                    self.page_size,
                )
                break

        logger.info(
            "EmploiTunisie scraper extracted %s records (skipped: %s, pages: %s)",
            len(records),
            skipped_records,
            self.max_pages,
        )
        return records

    def _build_listing_url(self, page_index):
        if page_index <= 0:
            return self.LISTING_BASE_URL
        return f"{self.LISTING_BASE_URL}?page={page_index}"

    def _safe_get_soup(self, url):
        try:
            logger.info(f"Fetching URL: {url} (timeout={self.timeout})")
            self._rate_limit_delay()
            response = self.session.get(url, timeout=self.timeout)
            logger.info(f"Fetched URL: {url} (status={response.status_code})")
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

    def _extract_detail_description(self, detail_soup):
        if detail_soup is None:
            return ""
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
                return parsed

        fallback_time_node = card.select_one("time")
        if fallback_time_node:
            parsed = self._parse_date_to_iso(fallback_time_node.get_text(" ", strip=True))
            if parsed:
                return parsed

        jsonld_date = self._extract_date_from_jsonld(detail_soup) if detail_soup is not None else ""
        if jsonld_date:
            parsed = self._parse_date_to_iso(jsonld_date)
            if parsed:
                return parsed

        return date.today().isoformat()

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
