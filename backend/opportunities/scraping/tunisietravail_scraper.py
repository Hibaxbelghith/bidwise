import logging
import os
import random
import re
import time
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
TUNISIETRAVAIL_MAX_PAGES = _get_env_int("TUNISIETRAVAIL_MAX_PAGES", 5)
TUNISIETRAVAIL_MAX_RECORDS = _get_env_int("TUNISIETRAVAIL_MAX_RECORDS", 0)
TUNISIETRAVAIL_PAGE_SIZE = _get_env_int("TUNISIETRAVAIL_PAGE_SIZE", 10)


class TunisieTravailScraper(BaseOpportunityScraper):
    source_name = "TunisieTravail"
    source_url = "https://www.tunisietravail.net/tag/offre-demploi-tunisie-2026/"
    source_type = "SITE_EMPLOI"

    LISTING_BASE_URL = "https://www.tunisietravail.net/tag/offre-demploi-tunisie-2026/"
    DEFAULT_TIMEOUT = SCRAPER_TIMEOUT
    DEFAULT_MAX_PAGES = TUNISIETRAVAIL_MAX_PAGES

    # Requested selectors (primary) + robust fallbacks for current DOM.
    LISTING_CARD_SELECTORS = [
        "article",
    ]
    TITLE_SELECTORS = [
        "article h2 a",
        "h2 a",
    ]
    URL_SELECTORS = [
        "article h2 a[href]",
        "h2 a[href]",
    ]
    SUMMARY_SELECTORS = [
        "div.entry-content p",
        ".entry-content p",
        ".Post div[align='justify']",
        "div[align='justify']",
    ]
    PUBLICATION_DATE_SELECTORS = [
        "time.entry-date",
        ".entry-date",
    ]

    DETAIL_DESCRIPTION_SELECTORS = [
        "div.entry-content",
        ".entry-content",
        ".PostContent",
    ]
    DETAIL_DATE_SELECTORS = [
        "time.entry-date",
        "meta[property='article:published_time']",
        "meta[itemprop='datePublished']",
        "meta[name='date']",
    ]

    def __init__(
        self,
        max_pages=DEFAULT_MAX_PAGES,
        timeout=DEFAULT_TIMEOUT,
        min_delay=SCRAPER_MIN_DELAY,
        max_delay=SCRAPER_MAX_DELAY,
        max_records=TUNISIETRAVAIL_MAX_RECORDS,
        fetch_details=FETCH_DETAILS,
        page_size=TUNISIETRAVAIL_PAGE_SIZE,
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

        for page_number in range(1, self.max_pages + 1):
            listing_url = self._build_listing_url(page_number)
            listing_soup = self._safe_get_soup(listing_url)
            if listing_soup is None:
                logger.warning("No listing HTML for page=%s url=%s", page_number, listing_url)
                continue

            cards = self._extract_listing_cards(listing_soup)
            logger.info(
                "TunisieTravail page=%s detected %s candidate cards",
                page_number,
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
                listing_description = self._extract_summary_description(card)
                listing_publication_date = self._extract_publication_date(card, None)
                listing_organization = self._extract_organization(listing_title)

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
                description = self._extract_detail_description(detail_soup) or listing_description or title
                publication_date = self._extract_publication_date(card, detail_soup) or listing_publication_date
                organization = self._extract_organization(title) or listing_organization
                description, raw_description = self._clean_description(description)

                record = {
                    "title": title,
                    "description": description,
                    "organization": organization,
                    "location": self._clean_location(""),
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
                        "TunisieTravail scraper extracted %s records (skipped: %s, pages scanned: %s)",
                        len(records),
                        skipped_records,
                        page_number,
                    )
                    return records
            if len(cards) < self.page_size:
                logger.info(
                    "TunisieTravail page=%s has %s cards (< page_size=%s), stopping early.",
                    page_number,
                    len(cards),
                    self.page_size,
                )
                break

        logger.info(
            "TunisieTravail scraper extracted %s records (skipped: %s, pages: %s)",
            len(records),
            skipped_records,
            self.max_pages,
        )
        return records

    def _build_listing_url(self, page_number):
        if page_number <= 1:
            return self.LISTING_BASE_URL
        return f"{self.LISTING_BASE_URL.rstrip('/')}/page/{page_number}/"

    def _safe_get_soup(self, url):
        try:
            self._rate_limit_delay()
            response = self.session.get(url, timeout=self.timeout)
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
            if any(card.select_one(selector) for selector in self.URL_SELECTORS):
                filtered.append(card)
        return filtered

    def _extract_title(self, card, detail_soup):
        title = self._extract_first_text(card, self.TITLE_SELECTORS)
        if title:
            return title
        if detail_soup is not None:
            detail_h1 = detail_soup.select_one("h1")
            if detail_h1:
                return self._clean_text(detail_h1.get_text(" ", strip=True))
            if detail_soup.title:
                return self._clean_text(detail_soup.title.get_text(" ", strip=True))
        return ""

    def _extract_url(self, card):
        for selector in self.URL_SELECTORS:
            node = card.select_one(selector)
            if not node:
                continue
            href = self._clean_text(node.get("href"))
            if href:
                return urljoin(self.source_url, href)
        return ""

    def _extract_summary_description(self, card):
        return self._extract_first_text(card, self.SUMMARY_SELECTORS)

    def _extract_detail_description(self, detail_soup):
        if detail_soup is None:
            return ""
        for selector in self.DETAIL_DESCRIPTION_SELECTORS:
            node = detail_soup.select_one(selector)
            if node:
                text = self._clean_text(node.get_text("\n", strip=True))
                if text:
                    return text
        return ""

    def _extract_publication_date(self, card, detail_soup):
        listing_raw = self._extract_date_from_node(card, self.PUBLICATION_DATE_SELECTORS)
        parsed = self._parse_date_to_iso(listing_raw)
        if parsed:
            return parsed

        if detail_soup is not None:
            detail_raw = self._extract_date_from_node(detail_soup, self.DETAIL_DATE_SELECTORS)
            parsed = self._parse_date_to_iso(detail_raw)
            if parsed:
                return parsed

        return date.today().isoformat()

    def _extract_date_from_node(self, node, selectors):
        if node is None:
            return ""
        for selector in selectors:
            element = node.select_one(selector)
            if not element:
                continue
            content = self._clean_text(element.get("datetime") or element.get("content") or element.get("value"))
            if content:
                return content
            text = self._clean_text(element.get_text(" ", strip=True))
            if text:
                return text
        return ""

    def _extract_organization(self, title):
        text = self._clean_text(title)
        if not text:
            return ""
        match = re.match(r"^(.*?)\s+recrute\b", text, flags=re.IGNORECASE)
        if match:
            return self._clean_text(match.group(1))
        return ""

    def _parse_date_to_iso(self, raw_value):
        text = self._clean_text(raw_value)
        if not text:
            return ""

        if "T" in text and len(text) >= 10 and text[:4].isdigit():
            text = text[:10]

        absolute_formats = (
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%d.%m.%Y",
            "%Y-%m-%d %H:%M:%S",
        )
        for fmt in absolute_formats:
            try:
                return datetime.strptime(text, fmt).date().isoformat()
            except ValueError:
                continue
        return ""

    def _extract_first_text(self, node, selectors):
        for selector in selectors:
            element = node.select_one(selector)
            if element:
                text = self._clean_text(element.get_text(" ", strip=True))
                if text:
                    return text
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

    def _clean_description(self, text):
        return clean_description_for_ml(text)

    def _clean_location(self, location):
        return clean_location_for_ml(location)
