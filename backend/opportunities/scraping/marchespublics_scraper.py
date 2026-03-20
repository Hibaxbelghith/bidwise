import logging
import os
import random
import re
import time
from datetime import date, datetime
from urllib.parse import urlparse

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
MARCHESPUBLICS_MAX_PAGES = _get_env_int("MARCHESPUBLICS_MAX_PAGES", 5)
MARCHESPUBLICS_PAGE_SIZE = _get_env_int("MARCHESPUBLICS_PAGE_SIZE", 50)
MARCHESPUBLICS_MAX_RECORDS = _get_env_int("MARCHESPUBLICS_MAX_RECORDS", 0)


class MarchesPublicsScraper(BaseOpportunityScraper):
    source_name = "MarchesPublics"
    source_url = "https://www.marchespublics.gov.tn"
    source_type = "PORTAIL_PROJET"

    LISTING_URL = "https://www.marchespublics.gov.tn/fr/appels-doffres"
    DETAIL_URL_TEMPLATE = "https://www.marchespublics.gov.tn/fr/appels-doffres/{tender_id}"

    DEFAULT_TIMEOUT = SCRAPER_TIMEOUT
    DEFAULT_MAX_PAGES = MARCHESPUBLICS_MAX_PAGES
    DEFAULT_PAGE_SIZE = MARCHESPUBLICS_PAGE_SIZE
    DEFAULT_MAX_RECORDS = MARCHESPUBLICS_MAX_RECORDS

    DETAIL_CONTAINER_SELECTORS = [
        "div.liste_appel_offre.page-cms",
        "div.page-cms",
        "main",
    ]

    def __init__(
        self,
        max_pages=DEFAULT_MAX_PAGES,
        timeout=DEFAULT_TIMEOUT,
        min_delay=SCRAPER_MIN_DELAY,
        max_delay=SCRAPER_MAX_DELAY,
        page_size=DEFAULT_PAGE_SIZE,
        max_records=DEFAULT_MAX_RECORDS,
        fetch_details=FETCH_DETAILS,
    ):
        self.max_pages = max(1, int(max_pages))
        self.timeout = timeout
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.page_size = max(10, min(int(page_size), 100))
        self.max_records = max_records if max_records and max_records > 0 else None
        self.fetch_details = fetch_details
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
                "X-Requested-With": "XMLHttpRequest",
                "Accept": "application/json, text/javascript, */*; q=0.01",
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
            payload = self._fetch_listing_payload(page_number)
            if payload is None:
                logger.warning("Skipping listing page=%s due to fetch failure", page_number)
                continue

            rows = payload.get("data") or []
            logger.info("MarchesPublics listing page=%s returned rows=%s", page_number, len(rows))

            if not rows:
                logger.info("No rows on listing page=%s, stopping pagination.", page_number)
                break

            new_links = 0
            for row in rows:
                row_record = self._extract_listing_row(row)
                url = row_record.get("url")
                if not url:
                    skipped_records += 1
                    logger.info("Skipping row without detail URL")
                    continue
                if url in seen_urls:
                    skipped_records += 1
                    logger.debug("Duplicate URL across listing pages: %s", url)
                    continue

                seen_urls.add(url)
                new_links += 1

                needs_details = self.fetch_details or self._needs_detail_fetch(
                    row_record.get("title"),
                    row_record.get("description"),
                )
                detail_data = {}
                if needs_details:
                    detail_soup = self._safe_get_soup(url)
                    if detail_soup is None and self.fetch_details:
                        logger.info(
                            "Detail fetch failed, falling back to listing data: %s",
                            url,
                        )
                    if detail_soup is not None:
                        detail_data = self._extract_detail_data(detail_soup)

                title = self._first_non_empty(
                    detail_data.get("title"),
                    row_record.get("title"),
                )
                organization = self._first_non_empty(
                    detail_data.get("organization"),
                    row_record.get("organization"),
                    "Unknown",
                )
                location = self._first_non_empty(
                    detail_data.get("location"),
                    row_record.get("location"),
                )
                location = self._clean_location(location)
                publication_date = self._first_non_empty(
                    self._parse_date_to_iso(detail_data.get("publication_date")),
                    self._parse_date_to_iso(row_record.get("publication_date")),
                    date.today().isoformat(),
                )
                deadline = self._first_non_empty(
                    self._parse_date_to_iso(detail_data.get("deadline")),
                    self._parse_date_to_iso(row_record.get("deadline")),
                )

                description = self._first_non_empty(
                    detail_data.get("description"),
                    row_record.get("description"),
                    title,
                )
                if deadline and "deadline:" not in description.lower():
                    description = f"{description}\nDeadline: {deadline}"
                description, raw_description = self._clean_description(description)
                if not description:
                    description, raw_description = self._clean_description(title)

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
                    "opportunity_type": "project",
                }
                if deadline:
                    record["deadline"] = deadline
                if raw_description:
                    record["raw_description"] = raw_description

                if not self._is_valid_record(record):
                    skipped_records += 1
                    continue

                records.append(record)

                if self.max_records and len(records) >= self.max_records:
                    logger.info(
                        "Reached max_records=%s extracted=%s skipped=%s",
                        self.max_records,
                        len(records),
                        skipped_records,
                    )
                    return records

            if new_links == 0:
                logger.info("No new listing records on page=%s, stopping.", page_number)
                break
            if len(rows) < self.page_size:
                logger.info(
                    "Early stop: rows (%s) < page_size (%s) on page=%s",
                    len(rows),
                    self.page_size,
                    page_number,
                )
                break

            total_filtered = payload.get("recordsFiltered")
            if isinstance(total_filtered, int):
                current_offset = page_number * self.page_size
                if current_offset >= total_filtered:
                    logger.info(
                        "Reached end of listing by recordsFiltered=%s at page=%s",
                        total_filtered,
                        page_number,
                    )
                    break

        logger.info(
            "MarchesPublics extraction done. records=%s skipped=%s pages<=%s",
            len(records),
            skipped_records,
            self.max_pages,
        )
        return records

    def _fetch_listing_payload(self, page_number):
        params = {
            "draw": str(page_number),
            "start": str((page_number - 1) * self.page_size),
            "length": str(self.page_size),
        }
        try:
            self._rate_limit_delay()
            response = self.session.get(self.LISTING_URL, params=params, timeout=self.timeout)
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                logger.warning("Unexpected listing payload type for page=%s", page_number)
                return None
            return payload
        except requests.RequestException as exc:
            logger.warning("Listing request failed for page=%s: %s", page_number, exc)
            return None
        except ValueError as exc:
            logger.warning("Listing JSON decode failed for page=%s: %s", page_number, exc)
            return None

    def _extract_listing_row(self, row):
        tender_id = self._clean_text(row.get("id"))
        title = self._clean_text(row.get("title_fr"))
        organization = ""
        org = row.get("organization")
        if isinstance(org, dict):
            organization = self._clean_text(org.get("name_fr"))

        publication_date = self._parse_date_to_iso(row.get("publication_date"))
        deadline = self._parse_date_to_iso(row.get("tenderPeriod_endDate"))
        detail_url = self._build_detail_url(tender_id)

        raw_description_candidates = []
        for key in ("description_fr", "description", "objet", "title_fr"):
            value = row.get(key)
            if isinstance(value, dict):
                value = value.get("name_fr") or value.get("value") or ""
            raw_description_candidates.append(value)

        listing_description = self._first_non_empty(*raw_description_candidates, title)
        cleaned_description, _ = self._clean_description(listing_description)

        return {
            "title": title,
            "description": cleaned_description,
            "organization": organization,
            "location": "",
            "publication_date": publication_date,
            "deadline": deadline,
            "url": detail_url,
        }

    def _build_detail_url(self, tender_id):
        tender_id = self._clean_text(tender_id)
        if not tender_id:
            return ""
        return self.DETAIL_URL_TEMPLATE.format(tender_id=tender_id)

    def _extract_detail_data(self, soup):
        if soup is None:
            return {}

        container = None
        for selector in self.DETAIL_CONTAINER_SELECTORS:
            node = soup.select_one(selector)
            if node:
                container = node
                break
        if container is None:
            container = soup

        h5_map = self._extract_h5_value_map(container)
        strong_map = self._extract_strong_value_map(container)

        title = self._first_non_empty(
            h5_map.get("objet"),
            self._extract_first_text(container, ["h1"]),
        )
        organization = self._first_non_empty(
            strong_map.get("acheteur public"),
            strong_map.get("organisme"),
            "Unknown",
        )
        location = self._first_non_empty(
            strong_map.get("region d execution"),
            strong_map.get("lieu de reception des offres"),
            strong_map.get("lieu d ouverture des offres"),
        )
        publication_date = self._first_non_empty(
            h5_map.get("date de publication"),
            strong_map.get("date de commencement de reception des offres"),
        )
        deadline = self._first_non_empty(
            strong_map.get("date limite de reception des offres"),
            h5_map.get("date limite"),
        )

        description_parts = []
        for key in [
            "descriptif",
            "procedure de passation",
            "type de commande",
            "methodologie d evaluation",
            "lieu d ouverture des offres",
            "lieu de reception des offres",
        ]:
            value = self._first_non_empty(h5_map.get(key), strong_map.get(key))
            if value:
                description_parts.append(f"{key}: {value}")

        full_text = self._clean_text(container.get_text(" ", strip=True))
        description, _ = self._clean_description(
            " ".join(description_parts) if description_parts else full_text
        )

        return {
            "title": title,
            "organization": organization,
            "description": description,
            "publication_date": publication_date,
            "deadline": deadline,
            "location": location,
        }

    def _extract_h5_value_map(self, container):
        values = {}
        for h5 in container.select("h5"):
            label = self._normalize_key(h5.get_text(" ", strip=True))
            if not label:
                continue
            span = h5.find_next_sibling("span")
            if not span:
                continue
            value = self._clean_text(span.get_text(" ", strip=True))
            if value and label not in values:
                values[label] = value
        return values

    def _extract_strong_value_map(self, container):
        values = {}
        for paragraph in container.select("p"):
            strong = paragraph.select_one("strong")
            if not strong:
                continue

            label = self._normalize_key(strong.get_text(" ", strip=True))
            if not label:
                continue

            full_text = self._clean_text(paragraph.get_text(" ", strip=True))
            raw_label = self._clean_text(strong.get_text(" ", strip=True))
            value = self._clean_text(full_text.replace(raw_label, "", 1).strip(" :-|"))
            if value and label not in values:
                values[label] = value
        return values

    def _parse_date_to_iso(self, raw_value):
        text = self._clean_text(raw_value)
        if not text:
            return ""

        datetime_match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", text)
        if datetime_match:
            return datetime_match.group(1)

        for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%Y/%m/%d"):
            try:
                return datetime.strptime(text[:10], fmt).date().isoformat()
            except ValueError:
                continue
        return ""

    def _needs_detail_fetch(self, title, description):
        title_clean = self._clean_text(title)
        description_clean = self._clean_text(description)

        if not title_clean:
            return True
        if not description_clean or len(description_clean) < 40:
            return True
        return False

    def _clean_description(self, text):
        cleaned, raw_description = clean_description_for_ml(text)
        cleaned = self._clean_text(cleaned)
        if len(cleaned) > self.max_description_length:
            return cleaned[: self.max_description_length].strip(), raw_description or cleaned
        return cleaned, raw_description

    def _clean_location(self, location):
        return clean_location_for_ml(location)

    def _safe_get_soup(self, url):
        try:
            self._rate_limit_delay()
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return BeautifulSoup(response.text, "html.parser")
        except requests.RequestException as exc:
            logger.warning("Request failed for %s: %s", url, exc)
            return None

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

    def _normalize_key(self, text):
        normalized = self._clean_text(text).lower()
        replacements = {
            "\u00e9": "e",
            "\u00e8": "e",
            "\u00ea": "e",
            "\u00e0": "a",
            "\u00e2": "a",
            "\u00ee": "i",
            "\u00ef": "i",
            "\u00f4": "o",
            "\u00f9": "u",
            "\u00fb": "u",
            "\u00e7": "c",
            "\u00c3\u00a9": "e",
            "\u00c3\u00a8": "e",
            "\u00c3\u00aa": "e",
            "\u00c3\u00a0": "a",
            "\u00c3\u00a2": "a",
            "\u00c3\u00ae": "i",
            "\u00c3\u00af": "i",
            "\u00c3\u00b4": "o",
            "\u00c3\u00b9": "u",
            "\u00c3\u00bb": "u",
            "\u00c3\u00a7": "c",
            "\u00a0": " ",
        }
        for src, target in replacements.items():
            normalized = normalized.replace(src, target)
        normalized = re.sub(r"\s+", " ", normalized).strip(" :-_")
        return normalized

    def _is_valid_record(self, record):
        title = self._clean_text(record.get("title"))
        description = self._clean_text(record.get("description"))
        url = self._clean_text(record.get("url"))

        if not title:
            logger.info("Skipping record with empty title (url=%s)", url or "N/A")
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
        time.sleep(random.uniform(self.min_delay, self.max_delay))

    def _clean_text(self, value):
        if value is None:
            return ""
        return re.sub(r"\s+", " ", str(value)).strip()
