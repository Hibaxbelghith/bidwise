import logging
import os
import random
import re
import time
from datetime import date, timedelta
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


SCRAPER_TIMEOUT = _get_env_int("SCRAPER_TIMEOUT", SCRAPER_TIMEOUT_DEFAULT)


class KeejobScraper(BaseOpportunityScraper):
    source_name = "Keejob"
    source_url = "https://www.keejob.com/offres-emploi/"
    source_type = "SITE_EMPLOI"

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
    ]

    def __init__(self, timeout=DEFAULT_TIMEOUT, min_delay=0.8, max_delay=1.5, fetch_details=FETCH_DETAILS):
        self.timeout = timeout
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.fetch_details = fetch_details
        self.max_description_length = MAX_DESCRIPTION_LENGTH
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
        soup = self._safe_get_soup(self.source_url)
        if soup is None:
            logger.warning("No HTML returned for source URL: %s", self.source_url)
            return []

        records = []
        seen_urls = set()
        skipped_records = 0
        cards = self._extract_cards(soup)
        logger.info("Keejob scraper detected %s candidate job cards", len(cards))

        for card in cards:
            url = self._extract_url(card)
            if not url or url in seen_urls:
                skipped_records += 1
                if url in seen_urls:
                    logger.info("Skipping duplicate URL in same run: %s", url)
                continue
            seen_urls.add(url)

            title = self._extract_first_text(card, self.TITLE_SELECTORS)
            description = self._extract_first_text(card, self.DESCRIPTION_SELECTORS)
            publication_date_text = self._extract_first_text(card, self.PUBLICATION_DATE_SELECTORS)
            publication_date = self._normalize_publication_date(publication_date_text)
            location = self._clean_location(self._extract_first_text(card, self.LOCATION_SELECTORS))
            description, raw_description = self._clean_description(description)

            record = {
                "title": title,
                "description": description,
                "organization": self._extract_first_text(card, self.COMPANY_SELECTORS),
                "location": location,
                "publication_date": publication_date,
                "source_name": self.source_name,
                "source_url": self.source_url,
                "source_type": self.source_type,
                "url": url,
            }
            if raw_description:
                record["raw_description"] = raw_description
            if not self._is_valid_record(record):
                skipped_records += 1
                continue
            records.append(record)

        logger.info(
            "Keejob scraper extracted %s records (skipped: %s)",
            len(records),
            skipped_records,
        )
        return records

    def _safe_get_soup(self, url):
        try:
            self._rate_limit_delay()
            response = self.session.get(url, timeout=self.timeout)
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
        return re.sub(r"\s+", " ", str(value)).strip()

    def _clean_description(self, text):
        cleaned, raw = clean_description_for_ml(text)
        return cleaned, raw

    def _clean_location(self, location):
        return clean_location_for_ml(location)
