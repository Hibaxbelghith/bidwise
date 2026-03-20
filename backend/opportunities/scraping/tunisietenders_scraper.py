import logging
import os
import random
import re
import time
from datetime import date, datetime
from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlunparse

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
TUNISIETENDERS_MAX_CATEGORIES = _get_env_int("TUNISIETENDERS_MAX_CATEGORIES", 10)
TUNISIETENDERS_MAX_PAGES = _get_env_int("TUNISIETENDERS_MAX_PAGES", 5)
TUNISIETENDERS_MAX_RECORDS = _get_env_int("TUNISIETENDERS_MAX_RECORDS", 0)
TUNISIETENDERS_PAGE_SIZE = _get_env_int("TUNISIETENDERS_PAGE_SIZE", 20)


def clean_tender_description(text: str) -> str:
    value = "" if text is None else str(text)
    cleaned = re.sub(r"\s+", " ", value).strip()
    if not cleaned:
        return ""

    cleaned = re.sub(r"^\d+\s+[A-Z]{1,3}\b", " ", cleaned)
    cleaned = re.sub(r"\b(?:nat|rep|inter)\./[a-z]{2,4}\b", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b\d{1,2}/\d{4}\b", " ", cleaned)
    cleaned = re.sub(r"\b\d{2}:\d{2}:\d{2}\b", " ", cleaned)

    cleaned = re.sub(r"([!?.,;:])\1+", r"\1", cleaned)
    cleaned = re.sub(r"\s*([,;:.!?])\s*", r"\1 ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -_:;,")
    return cleaned


class TunisieTendersScraper(BaseOpportunityScraper):
    source_name = "TunisieTenders"
    source_url = "https://www.appeloffres.com"
    source_type = "PORTAIL_PROJET"

    CATEGORIES_URL = "https://www.appeloffres.com/appels-offres"
    DEFAULT_TIMEOUT = SCRAPER_TIMEOUT
    DEFAULT_MAX_CATEGORIES = TUNISIETENDERS_MAX_CATEGORIES
    DEFAULT_MAX_PAGES = TUNISIETENDERS_MAX_PAGES

    CATEGORY_LINK_SELECTORS = [
        "a[href*='/appels-offres/']",
    ]
    DETAIL_LINK_SELECTORS = [
        "a[href*='/appels-offres/']",
    ]
    DETAIL_TITLE_SELECTORS = [
        "h1",
        "h2",
        "div.page-header h1",
        "main h1",
        "article h1",
    ]
    DETAIL_DESCRIPTION_SELECTORS = [
        "main",
        "article",
        "div#content",
        "section.content",
        "div.content",
        "div.entry-content",
        "table",
    ]

    CATEGORY_PATH_RE = re.compile(r"^/appels-offres/[a-z0-9\-]+/?$", re.IGNORECASE)
    DETAIL_PATH_RE = re.compile(
        r"^/appels-offres/[a-z0-9\-]+/[a-z0-9\-]*\d+[a-z0-9\-]*$",
        re.IGNORECASE,
    )
    DATE_RE = re.compile(r"\b(\d{2}/\d{2}/\d{4})\b")
    LOCATION_RE = re.compile(r"\b(?:Nat|Rep|Inter)\./([A-Z]{3})\b")

    def __init__(
        self,
        max_categories=DEFAULT_MAX_CATEGORIES,
        max_pages=DEFAULT_MAX_PAGES,
        timeout=DEFAULT_TIMEOUT,
        min_delay=SCRAPER_MIN_DELAY,
        max_delay=SCRAPER_MAX_DELAY,
        max_records=TUNISIETENDERS_MAX_RECORDS,
        page_size=TUNISIETENDERS_PAGE_SIZE,
        fetch_details=FETCH_DETAILS,
    ):
        self.max_categories = max(1, int(max_categories))
        self.max_pages = max(1, int(max_pages))
        self.timeout = timeout
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.max_records = max_records if max_records and max_records > 0 else None
        self.page_size = max(1, int(page_size))
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
        category_urls = self._extract_category_urls()
        if not category_urls:
            logger.warning("No category URLs found from %s", self.CATEGORIES_URL)
            return []

        records = []
        seen_urls = set()
        skipped_records = 0

        for category_index, category_url in enumerate(category_urls, start=1):
            logger.info(
                "Processing TunisieTenders category %s/%s: %s",
                category_index,
                len(category_urls),
                category_url,
            )
            category_new_links = 0

            for page_number in range(1, self.max_pages + 1):
                listing_url = self._build_paginated_url(category_url, page_number)
                listing_soup = self._safe_get_soup(listing_url)
                if listing_soup is None:
                    logger.warning(
                        "Category page failed (category=%s, page=%s): %s",
                        category_url,
                        page_number,
                        listing_url,
                    )
                    continue

                listing_items = self._extract_listing_items(listing_soup)
                logger.info(
                    "Category page processed (category=%s, page=%s): %s candidate rows",
                    category_url,
                    page_number,
                    len(listing_items),
                )

                if not listing_items:
                    logger.info(
                        "No listing rows found, stopping pagination for category=%s at page=%s",
                        category_url,
                        page_number,
                    )
                    break

                new_links_in_page = 0
                for item in listing_items:
                    url = self._clean_text(item.get("url"))
                    if not url:
                        skipped_records += 1
                        logger.info("Skipping listing item without URL")
                        continue
                    if url in seen_urls:
                        skipped_records += 1
                        logger.debug("Skipping duplicate URL across categories: %s", url)
                        continue

                    seen_urls.add(url)
                    new_links_in_page += 1
                    category_new_links += 1

                    needs_details = self.fetch_details or self._needs_detail_fetch(
                        item.get("title"),
                        item.get("description"),
                        item.get("location"),
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
                        item.get("title"),
                    )
                    description = self._first_non_empty(
                        detail_data.get("description"),
                        item.get("description"),
                        title,
                    )
                    description, raw_description = self._clean_description(description)
                    if not description:
                        description, raw_description = self._clean_description(title)

                    organization = self._first_non_empty(
                        detail_data.get("organization"),
                        item.get("organization"),
                        "Unknown",
                    )
                    location = self._clean_location(
                        self._first_non_empty(
                            detail_data.get("location"),
                            item.get("location"),
                        )
                    )

                    publication_date = self._first_non_empty(
                        self._parse_date_to_iso(detail_data.get("publication_date")),
                        self._parse_date_to_iso(item.get("publication_date")),
                        date.today().isoformat(),
                    )

                    deadline = self._first_non_empty(
                        self._parse_date_to_iso(detail_data.get("deadline")),
                        self._parse_date_to_iso(item.get("deadline")),
                    )
                    if deadline and "deadline:" not in description.lower():
                        description = f"{description}\nDeadline: {deadline}"
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
                            "Reached max_records=%s. Extracted=%s, skipped=%s",
                            self.max_records,
                            len(records),
                            skipped_records,
                        )
                        return records

                if new_links_in_page == 0:
                    logger.info(
                        "No new links in category=%s page=%s, stopping this category.",
                        category_url,
                        page_number,
                    )
                    break
                if len(listing_items) < self.page_size:
                    logger.info(
                        "Early stop: listing rows (%s) < page_size (%s) for category=%s page=%s",
                        len(listing_items),
                        self.page_size,
                        category_url,
                        page_number,
                    )
                    break

            if category_new_links == 0:
                logger.info("Category had no new links: %s", category_url)

        logger.info(
            "TunisieTenders extraction done. Records=%s, skipped=%s, categories=%s",
            len(records),
            skipped_records,
            len(category_urls),
        )
        return records

    def _extract_category_urls(self):
        soup = self._safe_get_soup(self.CATEGORIES_URL)
        if soup is None:
            return []

        blocked_slugs = {
            "appels-offres",
            "resultat",
            "recherche",
            "newsletter",
            "contact",
            "abonnement",
            "devis-en-ligne",
            "termes-conditions",
            "espace-client",
        }

        category_urls = []
        seen = set()
        for selector in self.CATEGORY_LINK_SELECTORS:
            for node in soup.select(selector):
                href = self._clean_text(node.get("href"))
                if not href:
                    continue
                absolute = self._to_absolute_url(href)
                parsed = urlparse(absolute)
                path = parsed.path.rstrip("/")
                if not self.CATEGORY_PATH_RE.match(path):
                    continue

                slug = path.split("/")[-1].lower()
                if slug in blocked_slugs:
                    continue

                if absolute not in seen:
                    seen.add(absolute)
                    category_urls.append(absolute)

                if len(category_urls) >= self.max_categories:
                    logger.info(
                        "Reached max_categories=%s while collecting categories",
                        self.max_categories,
                    )
                    return category_urls

        logger.info("Discovered %s categories from %s", len(category_urls), self.CATEGORIES_URL)
        return category_urls

    def _build_paginated_url(self, category_url, page_number):
        if page_number <= 1:
            return category_url

        parsed = urlparse(category_url)
        query_params = parse_qs(parsed.query)
        query_params["page"] = [str(page_number)]
        updated_query = urlencode(query_params, doseq=True)
        return urlunparse(parsed._replace(query=updated_query))

    def _extract_listing_items(self, soup):
        items = []
        rows = soup.select("table tr")
        if not rows:
            rows = soup.select("tr")

        for row in rows:
            link_node, detail_url = self._extract_detail_link(row)
            if not detail_url:
                continue

            title = self._clean_text(link_node.get_text(" ", strip=True) if link_node else "")
            row_text = self._clean_text(row.get_text(" ", strip=True))
            if not title:
                title = self._clean_text(row_text)

            publication_date, deadline = self._extract_dates_from_text(row_text)
            location = self._extract_location_from_text(row_text)

            items.append(
                {
                    "title": title,
                    "description": self._build_listing_description(title, row_text),
                    "organization": self._extract_organization_from_text(row_text),
                    "location": location,
                    "publication_date": publication_date,
                    "deadline": deadline,
                    "url": detail_url,
                }
            )

        return items

    def _build_listing_description(self, title, row_text):
        description = self._first_non_empty(row_text, title)
        cleaned, _ = self._clean_description(description)
        return cleaned

    def _extract_detail_link(self, container):
        for selector in self.DETAIL_LINK_SELECTORS:
            for node in container.select(selector):
                href = self._clean_text(node.get("href"))
                if not href:
                    continue
                absolute = self._to_absolute_url(href)
                path = urlparse(absolute).path.rstrip("/")
                if self.DETAIL_PATH_RE.match(path):
                    return node, absolute
        return None, ""

    def _extract_detail_data(self, soup):
        if soup is None:
            return {}

        page_text = self._clean_text(soup.get_text(" ", strip=True))
        if self._looks_like_login_page(page_text):
            logger.debug("Detail page appears to be gated by login/subscription.")
            return {}

        title = self._extract_first_text(soup, self.DETAIL_TITLE_SELECTORS)
        description = self._extract_description(soup, page_text)
        organization = self._first_non_empty(
            self._extract_labeled_value(
                soup,
                [
                    "organisme",
                    "acheteur",
                    "ministere",
                    "societe",
                    "entreprise",
                    "etablissement",
                    "client",
                ],
            ),
            self._extract_organization_from_text(page_text),
            "Unknown",
        )
        publication_date = self._extract_labeled_value(
            soup,
            [
                "date",
                "publication",
                "publie",
            ],
        )
        deadline = self._extract_labeled_value(
            soup,
            ["echeance", "date limite", "deadline", "cloture"],
        )
        location = self._extract_labeled_value(
            soup,
            ["lieu", "gouvernorat", "region", "pays"],
        )

        # Fallbacks from full page text when labeled blocks are unavailable.
        if not publication_date:
            publication_date, _ = self._extract_dates_from_text(page_text)
        if not deadline:
            _, deadline = self._extract_dates_from_text(page_text)
        if not location:
            location = self._extract_location_from_text(page_text)

        return {
            "title": title,
            "description": description,
            "organization": organization,
            "location": location,
            "publication_date": publication_date,
            "deadline": deadline,
        }

    def _extract_description(self, soup, full_text):
        for selector in self.DETAIL_DESCRIPTION_SELECTORS:
            for node in soup.select(selector):
                text = self._clean_text(node.get_text("\n", strip=True))
                if not text:
                    continue
                if self._looks_like_login_page(text):
                    continue
                if len(text) >= 80:
                    return text

        if full_text and not self._looks_like_login_page(full_text):
            return full_text
        return ""

    def _extract_organization_from_text(self, text):
        cleaned = self._clean_text(text)
        if not cleaned:
            return "Unknown"

        normalized = self._normalize_keyword(cleaned)

        if "nat./tun" in normalized:
            return "Tunisie"
        if "inter./" in normalized:
            return "International"

        rep_match = re.search(r"\brep\./([a-z]{2,4})\b", normalized)
        if rep_match:
            return rep_match.group(1).upper()

        keyword_match = re.search(
            r"\b(ministere|societe|entreprise|office)\b([^\.;,\n]{0,80})",
            normalized,
        )
        if keyword_match:
            phrase = f"{keyword_match.group(1)} {keyword_match.group(2)}"
            phrase = self._clean_text(phrase).strip(" -_:;,")
            if phrase:
                return phrase.title()

        return "Unknown"

    def _extract_labeled_value(self, soup, label_keywords):
        keywords = [self._normalize_keyword(k) for k in label_keywords]

        for row in soup.select("tr"):
            cells = row.find_all(["th", "td"])
            if len(cells) < 2:
                continue
            label = self._normalize_keyword(cells[0].get_text(" ", strip=True))
            if any(keyword in label for keyword in keywords):
                value = self._clean_text(cells[1].get_text(" ", strip=True))
                if value:
                    return value

        for dt in soup.select("dt"):
            label = self._normalize_keyword(dt.get_text(" ", strip=True))
            if not any(keyword in label for keyword in keywords):
                continue
            dd = dt.find_next("dd")
            if dd:
                value = self._clean_text(dd.get_text(" ", strip=True))
                if value:
                    return value

        return ""

    def _extract_dates_from_text(self, text):
        cleaned = self._clean_text(text)
        if not cleaned:
            return "", ""

        date_matches = self.DATE_RE.findall(cleaned)
        if not date_matches:
            return "", ""

        publication_date = self._parse_date_to_iso(date_matches[0])
        deadline = self._parse_date_to_iso(date_matches[-1]) if len(date_matches) > 1 else ""
        return publication_date, deadline

    def _extract_location_from_text(self, text):
        cleaned = self._clean_text(text)
        if not cleaned:
            return ""
        match = self.LOCATION_RE.search(cleaned)
        if match:
            return match.group(1)
        return ""

    def _parse_date_to_iso(self, raw_value):
        text = self._clean_text(raw_value)
        if not text:
            return ""

        short_match = self.DATE_RE.search(text)
        if short_match:
            text = short_match.group(1)

        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y"):
            try:
                return datetime.strptime(text, fmt).date().isoformat()
            except ValueError:
                continue
        return ""

    def _needs_detail_fetch(self, title, description, location):
        title_clean = self._clean_text(title)
        description_clean = self._clean_text(description)
        location_clean = self._clean_text(location)

        if not title_clean:
            return True
        if not description_clean or len(description_clean) < 60:
            return True
        if description_clean.lower() == title_clean.lower():
            return True
        # Keep fast mode effective: missing location alone should not force a detail request.
        if location_clean and len(location_clean) < 2:
            return True
        return False

    def _clean_description(self, text):
        cleaned_domain = clean_tender_description(text)
        cleaned, raw_description = clean_description_for_ml(cleaned_domain)
        if len(cleaned) > self.max_description_length:
            return cleaned[: self.max_description_length].strip(), raw_description or cleaned_domain
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

    def _to_absolute_url(self, href):
        return urljoin(self.source_url, href)

    def _looks_like_login_page(self, text):
        normalized = self._normalize_keyword(text)
        if not normalized:
            return False
        return (
            "veuillez vous connecter" in normalized
            or "vous abonner" in normalized
            or "mot de passe oublie" in normalized
        )

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

    def _normalize_keyword(self, value):
        cleaned = self._clean_text(value).lower()
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
            cleaned = cleaned.replace(src, target)
        return cleaned

    def _rate_limit_delay(self):
        time.sleep(random.uniform(self.min_delay, self.max_delay))

    def _clean_text(self, value):
        if value is None:
            return ""
        return re.sub(r"\s+", " ", str(value)).strip()

