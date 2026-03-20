import logging
import os
import random
import re
import time
import unicodedata
from datetime import date, datetime, timedelta
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
HIINTERNS_MAX_PAGES = _get_env_int("HIINTERNS_MAX_PAGES", 5)
HIINTERNS_MAX_RECORDS = _get_env_int("HIINTERNS_MAX_RECORDS", 0)
HIINTERNS_PAGE_SIZE = _get_env_int("HIINTERNS_PAGE_SIZE", 20)


class HiInternsScraper(BaseOpportunityScraper):
    source_name = "HiInterns"
    source_url = "https://hi-interns.com"
    source_type = "SITE_STAGE"

    LISTING_BASE_URL = "https://hi-interns.com/internships"
    DEFAULT_TIMEOUT = SCRAPER_TIMEOUT
    DEFAULT_MAX_PAGES = HIINTERNS_MAX_PAGES

    LISTING_CARD_SELECTORS = [
        "a[href*='/internships/']",
    ]
    DETAIL_DESCRIPTION_SELECTORS = [
        "div.payload-richtext",
        "div.prose",
    ]

    def __init__(
        self,
        max_pages=DEFAULT_MAX_PAGES,
        timeout=DEFAULT_TIMEOUT,
        min_delay=SCRAPER_MIN_DELAY,
        max_delay=SCRAPER_MAX_DELAY,
        max_records=HIINTERNS_MAX_RECORDS,
        fetch_details=FETCH_DETAILS,
        page_size=HIINTERNS_PAGE_SIZE,
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
                "HiInterns page=%s detected %s candidate cards",
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
                listing_organization, listing_location = self._extract_org_and_location(card, None)
                listing_description = self._extract_description(card, None)
                listing_publication_date = self._extract_publication_date(None, card)

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
                organization, location = self._extract_org_and_location(card, detail_soup)
                if not organization:
                    organization = listing_organization
                if not location:
                    location = listing_location
                description = self._extract_description(card, detail_soup) or listing_description
                publication_date = self._extract_publication_date(detail_soup, card) or listing_publication_date

                location = self._clean_location(location)
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
                        "HiInterns scraper extracted %s records (skipped: %s, pages scanned: %s)",
                        len(records),
                        skipped_records,
                        page_number,
                    )
                    return records
            if len(cards) < self.page_size:
                logger.info(
                    "HiInterns page=%s has %s cards (< page_size=%s), stopping early.",
                    page_number,
                    len(cards),
                    self.page_size,
                )
                break

        logger.info(
            "HiInterns scraper extracted %s records (skipped: %s, pages: %s)",
            len(records),
            skipped_records,
            self.max_pages,
        )
        return records

    def _build_listing_url(self, page_number):
        if page_number <= 1:
            return self.LISTING_BASE_URL
        return f"{self.LISTING_BASE_URL}?internships%5Bpage%5D={page_number}"

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
            cards.extend(soup.select(selector))

        filtered = []
        for card in cards:
            href = self._clean_text(card.get("href"))
            if href.startswith("/internships/") and href != "/internships":
                filtered.append(card)
        return filtered

    def _extract_url(self, card):
        href = self._clean_text(card.get("href"))
        if not href:
            return ""
        return urljoin(self.source_url, href)

    def _extract_title(self, card, detail_soup):
        listing_title_node = card.select_one("h3")
        listing_title = self._clean_text(
            listing_title_node.get_text(" ", strip=True) if listing_title_node else ""
        )
        if listing_title:
            return listing_title

        if detail_soup is not None:
            detail_title_node = detail_soup.select_one("div.flex-1 h1")
            detail_title = self._clean_text(
                detail_title_node.get_text(" ", strip=True) if detail_title_node else ""
            )
            if detail_title:
                return detail_title

            h1 = detail_soup.select_one("h1")
            if h1:
                return self._clean_text(h1.get_text(" ", strip=True))
        return ""

    def _extract_org_and_location(self, card, detail_soup):
        listing_meta_node = card.select_one("p.text-muted-foreground")
        listing_meta = self._clean_text(
            listing_meta_node.get_text(" ", strip=True) if listing_meta_node else ""
        )
        org, loc = self._split_org_location(listing_meta)

        detail_org, detail_loc = "", ""
        if detail_soup is not None:
            detail_meta = ""
            meta_container = detail_soup.select_one("div.flex-1 div.text-muted-foreground")
            if meta_container:
                detail_meta = self._clean_text(meta_container.get_text(" ", strip=True))
            if not detail_meta:
                mobile_meta = detail_soup.select_one("div.mb-5.lg\\:hidden div.text-muted-foreground")
                if mobile_meta:
                    detail_meta = self._clean_text(mobile_meta.get_text(" ", strip=True))
            detail_org, detail_loc = self._split_org_location(detail_meta)

        return org or detail_org, loc or detail_loc

    def _split_org_location(self, text):
        if not text:
            return "", ""
        parts = [
            self._clean_text(p)
            for p in re.split(r"\s*(?:\u2022|\u00b7|\u2027)\s*", text)
            if self._clean_text(p)
        ]
        if not parts:
            return "", ""
        if len(parts) == 1:
            return parts[0], ""
        return parts[0], parts[1]

    def _extract_description(self, card, detail_soup):
        if detail_soup is not None:
            heading = detail_soup.find(
                lambda tag: tag.name in {"h2", "h3"}
                and "description du poste" in self._clean_text(tag.get_text(" ", strip=True)).lower()
            )
            if heading:
                rich_block = heading.find_next(
                    "div",
                    class_=lambda value: value and ("payload-richtext" in value or "prose" in value),
                )
                if rich_block:
                    text = self._clean_text(rich_block.get_text("\n", strip=True))
                    if text:
                        return text

            for selector in self.DETAIL_DESCRIPTION_SELECTORS:
                node = detail_soup.select_one(selector)
                if node:
                    text = self._clean_text(node.get_text("\n", strip=True))
                    if text:
                        return text

        summary_candidates = [self._clean_text(p.get_text(" ", strip=True)) for p in card.select("p")]
        summary_candidates = [
            text
            for text in summary_candidates
            if text
            and "expire dans" not in self._normalize_match_text(text)
            and "publie il y a" not in self._normalize_match_text(text)
        ]
        if summary_candidates:
            return max(summary_candidates, key=len)
        return ""

    def _extract_publication_date(self, detail_soup=None, card=None):
        if detail_soup is not None:
            for paragraph in detail_soup.select("p"):
                raw = self._clean_text(paragraph.get_text(" ", strip=True))
                if "publie il y a" in self._normalize_match_text(raw):
                    parsed = self._normalize_relative_date(raw)
                    if parsed:
                        return parsed

        if card is not None:
            for paragraph in card.select("p"):
                raw = self._clean_text(paragraph.get_text(" ", strip=True))
                if "publie il y a" in self._normalize_match_text(raw):
                    parsed = self._normalize_relative_date(raw)
                    if parsed:
                        return parsed
        return date.today().isoformat()

    def _normalize_relative_date(self, raw_value):
        text = self._normalize_match_text(raw_value)
        today = date.today()

        minute_match = re.search(r"(\d+)\s*minute", text)
        if minute_match:
            return today.isoformat()

        hour_match = re.search(r"(\d+)\s*heure", text)
        if hour_match:
            return today.isoformat()

        day_match = re.search(r"(\d+)\s*jour", text)
        if day_match:
            return (today - timedelta(days=int(day_match.group(1)))).isoformat()

        week_match = re.search(r"(\d+)\s*semaine", text)
        if week_match:
            return (today - timedelta(days=int(week_match.group(1)) * 7)).isoformat()

        month_match = re.search(r"(\d+)\s*mois", text)
        if month_match:
            return (today - timedelta(days=int(month_match.group(1)) * 30)).isoformat()

        absolute_formats = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y/%m/%d")
        for fmt in absolute_formats:
            try:
                return datetime.strptime(text, fmt).date().isoformat()
            except ValueError:
                continue
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

    def _normalize_match_text(self, value):
        cleaned = self._clean_text(value)
        if not cleaned:
            return ""

        # Handle mojibake variants and normalize accent-insensitive matching.
        cleaned = cleaned.replace("\u00c3\u00a9", "\u00e9")
        cleaned = cleaned.replace("\u00e2\u20ac\u00a2", "\u2022")
        normalized = unicodedata.normalize("NFKD", cleaned)
        return "".join(ch for ch in normalized if not unicodedata.combining(ch)).lower()
