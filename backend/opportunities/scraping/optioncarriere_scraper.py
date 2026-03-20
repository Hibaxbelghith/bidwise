import json
import logging
import os
import random
import re
import time
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
OPTIONCARRIERE_MAX_PAGES = _get_env_int("OPTIONCARRIERE_MAX_PAGES", 5)
OPTIONCARRIERE_MAX_RECORDS = _get_env_int("OPTIONCARRIERE_MAX_RECORDS", 0)
OPTIONCARRIERE_PAGE_SIZE = _get_env_int("OPTIONCARRIERE_PAGE_SIZE", 20)


class OptionCarriereScraper(BaseOpportunityScraper):
    source_name = "OptionCarriere"
    source_url = "https://www.optioncarriere.tn/emploi"
    source_type = "SITE_EMPLOI"

    LISTING_BASE_URL = "https://www.optioncarriere.tn/emploi"
    DEFAULT_TIMEOUT = SCRAPER_TIMEOUT
    DEFAULT_MAX_PAGES = OPTIONCARRIERE_MAX_PAGES

    LISTING_CARD_SELECTORS = [
        "article.job",
        "article[data-url*='/jobad/']",
    ]
    JOB_LINK_SELECTORS = [
        "header h2 a[href*='/jobad/']",
        "a[href*='/jobad/']",
    ]
    TITLE_SELECTORS = [
        "header h2 a",
        "h2 a",
    ]
    COMPANY_SELECTORS = [
        "p.company",
    ]
    LOCATION_SELECTORS = [
        "ul.location li",
    ]
    LISTING_DESCRIPTION_SELECTORS = [
        "div.desc",
    ]
    LISTING_DATE_SELECTORS = [
        "footer ul li span.badge.badge-r.badge-s.badge-icon",
        "ul.tags li span.badge.badge-r.badge-s",
    ]

    DETAIL_TITLE_SELECTORS = [
        "article#job header h1",
        "article header h1",
    ]
    DETAIL_COMPANY_SELECTORS = [
        "article#job header p.company",
        "article#job section.content .company h3",
    ]
    DETAIL_LOCATION_SELECTORS = [
        "article#job header ul.details li span",
    ]
    DETAIL_DESCRIPTION_SELECTORS = [
        "article#job section.content",
        "section.content",
    ]

    def __init__(
        self,
        max_pages=DEFAULT_MAX_PAGES,
        timeout=DEFAULT_TIMEOUT,
        min_delay=SCRAPER_MIN_DELAY,
        max_delay=SCRAPER_MAX_DELAY,
        max_records=OPTIONCARRIERE_MAX_RECORDS,
        fetch_details=FETCH_DETAILS,
        page_size=OPTIONCARRIERE_PAGE_SIZE,
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
                "OptionCarriere page=%s detected %s candidate cards",
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

                listing_title = self._extract_first_text(card, self.TITLE_SELECTORS)
                listing_description = self._extract_listing_description(card)
                listing_organization = self._extract_first_text(card, self.COMPANY_SELECTORS)
                listing_location = self._extract_first_text(card, self.LOCATION_SELECTORS)
                listing_publication_date = self._extract_publication_date(card, {})

                detail_soup = None
                jsonld = {}
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
                    if detail_soup is not None:
                        jsonld = self._extract_detail_jsonld(detail_soup)

                title = self._extract_title(card, detail_soup, jsonld) or listing_title
                description = self._extract_detail_description(detail_soup, jsonld) or listing_description
                organization = self._extract_organization(card, detail_soup, jsonld) or listing_organization
                location = self._clean_location(
                    self._first_non_empty(
                        self._extract_location(card, detail_soup, jsonld),
                        listing_location,
                    )
                )
                publication_date = self._extract_publication_date(card, jsonld) or listing_publication_date
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
                        "OptionCarriere scraper extracted %s records (skipped: %s, pages scanned: %s)",
                        len(records),
                        skipped_records,
                        page_number,
                    )
                    return records
            if len(cards) < self.page_size:
                logger.info(
                    "OptionCarriere page=%s has %s cards (< page_size=%s), stopping early.",
                    page_number,
                    len(cards),
                    self.page_size,
                )
                break

        logger.info(
            "OptionCarriere scraper extracted %s records (skipped: %s, pages: %s)",
            len(records),
            skipped_records,
            self.max_pages,
        )
        return records

    def _build_listing_url(self, page_number):
        if page_number <= 1:
            return self.LISTING_BASE_URL
        return f"{self.LISTING_BASE_URL}?p={page_number}"

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
            if any(card.select_one(selector) for selector in self.JOB_LINK_SELECTORS):
                filtered.append(card)
        return filtered

    def _extract_url(self, card):
        data_url = self._clean_text(card.get("data-url"))
        if data_url:
            return urljoin(self.source_url, data_url)

        for selector in self.JOB_LINK_SELECTORS:
            node = card.select_one(selector)
            if not node:
                continue
            href = self._clean_text(node.get("href"))
            if href:
                return urljoin(self.source_url, href)
        return ""

    def _extract_title(self, card, detail_soup, jsonld):
        listing_title = self._extract_first_text(card, self.TITLE_SELECTORS)
        detail_title = self._extract_first_text(detail_soup, self.DETAIL_TITLE_SELECTORS) if detail_soup else ""
        jsonld_title = self._clean_text(jsonld.get("title")) if jsonld else ""
        return detail_title or listing_title or jsonld_title

    def _extract_organization(self, card, detail_soup, jsonld):
        listing_company = self._extract_first_text(card, self.COMPANY_SELECTORS)
        detail_company = self._extract_first_text(detail_soup, self.DETAIL_COMPANY_SELECTORS) if detail_soup else ""

        jsonld_company = ""
        if jsonld:
            org = jsonld.get("hiringOrganization") or {}
            if isinstance(org, dict):
                jsonld_company = self._clean_text(org.get("name"))

        return listing_company or detail_company or jsonld_company

    def _extract_location(self, card, detail_soup, jsonld):
        listing_location = self._extract_first_text(card, self.LOCATION_SELECTORS)
        detail_location = self._extract_location_from_detail(detail_soup) if detail_soup else ""
        jsonld_location = self._extract_location_from_jsonld(jsonld)
        return listing_location or detail_location or jsonld_location

    def _extract_location_from_detail(self, detail_soup):
        for selector in self.DETAIL_LOCATION_SELECTORS:
            node = detail_soup.select_one(selector)
            if node:
                text = self._clean_text(node.get_text(" ", strip=True))
                if text:
                    return text
        return ""

    def _extract_location_from_jsonld(self, jsonld):
        if not isinstance(jsonld, dict):
            return ""
        location_data = jsonld.get("jobLocation") or {}
        if not isinstance(location_data, dict):
            return ""
        address = location_data.get("address") or {}
        if not isinstance(address, dict):
            return ""
        locality = self._clean_text(address.get("addressLocality"))
        region = self._clean_text(address.get("addressRegion"))
        return locality or region

    def _extract_listing_description(self, card):
        return self._extract_first_text(card, self.LISTING_DESCRIPTION_SELECTORS)

    def _extract_detail_description(self, detail_soup, jsonld):
        if detail_soup is None:
            return ""
        for selector in self.DETAIL_DESCRIPTION_SELECTORS:
            node = detail_soup.select_one(selector)
            if node:
                text = self._clean_text(node.get_text("\n", strip=True))
                if text:
                    return text

        if isinstance(jsonld, dict):
            jsonld_desc = self._clean_text(
                BeautifulSoup(str(jsonld.get("description", "")), "html.parser").get_text(" ", strip=True)
            )
            if jsonld_desc:
                return jsonld_desc
        return ""

    def _extract_publication_date(self, card, jsonld):
        for selector in self.LISTING_DATE_SELECTORS:
            node = card.select_one(selector)
            if node:
                raw = self._clean_text(node.get_text(" ", strip=True))
                parsed = self._parse_date_to_iso(raw)
                if parsed:
                    return parsed

        if isinstance(jsonld, dict):
            raw = self._clean_text(jsonld.get("datePosted"))
            parsed = self._parse_date_to_iso(raw)
            if parsed:
                return parsed

        return date.today().isoformat()

    def _extract_detail_jsonld(self, detail_soup):
        if detail_soup is None:
            return {}
        for node in detail_soup.select("script[type='application/ld+json']"):
            payload = self._clean_text(node.string or node.get_text(" ", strip=True))
            if not payload:
                continue
            try:
                parsed = json.loads(payload)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                return parsed
            if isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, dict):
                        return item
        return {}

    def _parse_date_to_iso(self, raw_value):
        text = self._clean_text(raw_value).lower()
        today = date.today()

        if not text:
            return ""

        if "t" in text and len(text) >= 10 and text[:4].isdigit():
            text = text[:10]

        absolute_formats = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y/%m/%d")
        for fmt in absolute_formats:
            try:
                return datetime.strptime(text, fmt).date().isoformat()
            except ValueError:
                continue

        day_match = re.search(r"il y a\s+(\d+)\s+jour", text)
        if day_match:
            return (today - timedelta(days=int(day_match.group(1)))).isoformat()

        week_match = re.search(r"il y a\s+(\d+)\s+semaine", text)
        if week_match:
            return (today - timedelta(days=int(week_match.group(1)) * 7)).isoformat()

        month_match = re.search(r"il y a\s+(\d+)\s+mois", text)
        if month_match:
            return (today - timedelta(days=int(month_match.group(1)) * 30)).isoformat()

        if "il y a" in text and "heure" in text:
            return today.isoformat()
        if "il y a" in text and "minute" in text:
            return today.isoformat()
        if "aujourd" in text:
            return today.isoformat()
        if "hier" in text:
            return (today - timedelta(days=1)).isoformat()

        return ""

    def _extract_first_text(self, node, selectors):
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
