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
    infer_city_from_text,
    infer_organization_from_text,
    infer_organization_from_title,
    normalize_organization_name,
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


def _get_env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


SCRAPER_TIMEOUT = _get_env_int("SCRAPER_TIMEOUT", SCRAPER_TIMEOUT_DEFAULT)
SCRAPER_MIN_DELAY = _get_env_float("SCRAPER_MIN_DELAY", 0.8)
SCRAPER_MAX_DELAY = _get_env_float("SCRAPER_MAX_DELAY", 1.5)
HIINTERNS_MAX_PAGES = _get_env_int("HIINTERNS_MAX_PAGES", 5)
HIINTERNS_MAX_RECORDS = _get_env_int("HIINTERNS_MAX_RECORDS", 0)
HIINTERNS_PAGE_SIZE = _get_env_int("HIINTERNS_PAGE_SIZE", 20)
HIINTERNS_USE_PLAYWRIGHT = _get_env_bool("HIINTERNS_USE_PLAYWRIGHT", True)
HIINTERNS_PLAYWRIGHT_HEADLESS = _get_env_bool("HIINTERNS_PLAYWRIGHT_HEADLESS", True)
HIINTERNS_PLAYWRIGHT_WAIT_MS = _get_env_int("HIINTERNS_PLAYWRIGHT_WAIT_MS", 2500)
HIINTERNS_PLAYWRIGHT_TIMEOUT_MS = _get_env_int("HIINTERNS_PLAYWRIGHT_TIMEOUT_MS", 30000)
HIINTERNS_TRACE_API = _get_env_bool("HIINTERNS_TRACE_API", False)
HIINTERNS_TRACE_API_MAX_EVENTS = _get_env_int("HIINTERNS_TRACE_API_MAX_EVENTS", 40)
HIINTERNS_TRACE_API_INCLUDE_BODIES = _get_env_bool("HIINTERNS_TRACE_API_INCLUDE_BODIES", False)
HIINTERNS_TRACE_API_MAX_BODY_CHARS = _get_env_int("HIINTERNS_TRACE_API_MAX_BODY_CHARS", 500)
HIINTERNS_TRACE_STDOUT = _get_env_bool("HIINTERNS_TRACE_STDOUT", True)
HIINTERNS_TRACE_FIRST_PARTY_ONLY = _get_env_bool("HIINTERNS_TRACE_FIRST_PARTY_ONLY", True)
HIINTERNS_TRACE_DETAIL_URLS_MAX = _get_env_int("HIINTERNS_TRACE_DETAIL_URLS_MAX", 20)
HIINTERNS_USE_RSC = _get_env_bool("HIINTERNS_USE_RSC", True)
HIINTERNS_RSC_MAX_URLS = _get_env_int("HIINTERNS_RSC_MAX_URLS", 100)
HIINTERNS_USE_SITEMAP = _get_env_bool("HIINTERNS_USE_SITEMAP", True)
HIINTERNS_SITEMAP_URL = os.getenv("HIINTERNS_SITEMAP_URL", "https://hi-interns.com/sitemap.xml")


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
    OPPORTUNITY_TYPE = "STAGE"
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
        use_playwright=HIINTERNS_USE_PLAYWRIGHT,
        playwright_headless=HIINTERNS_PLAYWRIGHT_HEADLESS,
        playwright_wait_ms=HIINTERNS_PLAYWRIGHT_WAIT_MS,
        playwright_timeout_ms=HIINTERNS_PLAYWRIGHT_TIMEOUT_MS,
        trace_api=HIINTERNS_TRACE_API,
        trace_api_max_events=HIINTERNS_TRACE_API_MAX_EVENTS,
        trace_api_include_bodies=HIINTERNS_TRACE_API_INCLUDE_BODIES,
        trace_api_max_body_chars=HIINTERNS_TRACE_API_MAX_BODY_CHARS,
        trace_stdout=HIINTERNS_TRACE_STDOUT,
        trace_first_party_only=HIINTERNS_TRACE_FIRST_PARTY_ONLY,
        trace_detail_urls_max=HIINTERNS_TRACE_DETAIL_URLS_MAX,
        use_rsc=HIINTERNS_USE_RSC,
        rsc_max_urls=HIINTERNS_RSC_MAX_URLS,
        use_sitemap=HIINTERNS_USE_SITEMAP,
        sitemap_url=HIINTERNS_SITEMAP_URL,
    ):
        self.max_pages = max(1, min(int(max_pages), self.DEFAULT_MAX_PAGES))
        self.timeout = timeout
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.max_records = max_records if max_records and max_records > 0 else None
        self.fetch_details = fetch_details
        self.page_size = max(1, int(page_size))
        self.use_playwright = bool(use_playwright)
        self.playwright_headless = bool(playwright_headless)
        self.playwright_wait_ms = max(0, int(playwright_wait_ms))
        self.playwright_timeout_ms = max(1000, int(playwright_timeout_ms))
        self.trace_api = bool(trace_api)
        self.trace_api_max_events = max(1, int(trace_api_max_events))
        self.trace_api_include_bodies = bool(trace_api_include_bodies)
        self.trace_api_max_body_chars = max(80, int(trace_api_max_body_chars))
        self.trace_stdout = bool(trace_stdout)
        self.trace_first_party_only = bool(trace_first_party_only)
        self.trace_detail_urls_max = max(1, int(trace_detail_urls_max))
        self.use_rsc = bool(use_rsc)
        self.rsc_max_urls = max(1, int(rsc_max_urls))
        self.use_sitemap = bool(use_sitemap)
        self.sitemap_url = (sitemap_url or "").strip()
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
        sitemap_cards = self._build_listing_cards_from_sitemap() if self.use_sitemap else []

        for page_number in range(1, self.max_pages + 1):
            listing_url = self._build_listing_url(page_number)
            if sitemap_cards:
                cards = sitemap_cards if page_number == 1 else []
                logger.info(
                    "HiInterns page=%s loaded %s cards via sitemap path",
                    page_number,
                    len(cards),
                )
                listing_soup = None
            else:
                listing_soup = self._safe_get_soup(listing_url)
                if listing_soup is None:
                    logger.warning("No listing HTML for page=%s url=%s", page_number, listing_url)
                    continue

                cards = self._extract_listing_cards(listing_soup)

                if not cards and self.use_rsc:
                    rsc_cards = self._build_listing_cards_from_rsc(listing_url)
                    if rsc_cards:
                        cards = rsc_cards
                        logger.info(
                            "HiInterns page=%s recovered %s cards via RSC requests path",
                            page_number,
                            len(cards),
                        )

                if not cards and self.use_playwright:
                    logger.info(
                        "HiInterns page=%s had no cards via requests; trying Playwright fallback",
                        page_number,
                    )
                    rendered_soup = self._safe_get_soup_with_playwright(listing_url)
                    if rendered_soup is not None:
                        listing_soup = rendered_soup
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
                needs_details = self.fetch_details or not listing_location or self._needs_detail_fetch(
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

                organization = normalize_organization_name(organization)
                if not organization:
                    organization = infer_organization_from_title(title)
                if not organization:
                    organization = infer_organization_from_text(title, description)
                if not location:
                    location = infer_city_from_text(title, description, url, organization)
                location = self._clean_location(location)
                description, raw_description = self._clean_description(description)

                record = {
                    "title": title,
                    "description": description,
                    "organization": organization,
                    "location": location,
                    "publication_date": publication_date,
                    # Ensure internships are materialized as STAGE instead of
                    # falling back to EMPLOI when type is missing downstream.
                    "type_opportunite": self.OPPORTUNITY_TYPE,
                    "type": self.OPPORTUNITY_TYPE,
                    "statut": "ACTIVE",
                    "status": "ACTIVE",
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

    def _build_listing_cards_from_sitemap(self):
        if not self.sitemap_url:
            return []

        detail_urls = self._extract_detail_urls_from_sitemap()
        if not detail_urls:
            return []

        max_urls = self.max_records or (self.max_pages * self.page_size)
        if max_urls > 0:
            detail_urls = detail_urls[:max_urls]

        pseudo_soup = BeautifulSoup("", "html.parser")
        cards = []
        for detail_url in detail_urls:
            path = urlparse(detail_url).path or ""
            if not path.startswith("/internships/"):
                continue
            cards.append(pseudo_soup.new_tag("a", href=path))

        if cards:
            logger.info(
                "HiInterns sitemap extracted %s internship URLs",
                len(cards),
            )
        return cards

    def _extract_detail_urls_from_sitemap(self):
        try:
            self._rate_limit_delay()
            response = self.session.get(self.sitemap_url, timeout=self.timeout)
            response.raise_for_status()
            payload = response.text or ""
        except requests.RequestException as exc:
            logger.warning("HiInterns sitemap fetch failed for %s: %s", self.sitemap_url, exc)
            return []

        candidates = re.findall(
            r"https?://hi-interns\.com/internships/[a-z0-9][a-z0-9\-]*",
            payload,
            flags=re.IGNORECASE,
        )

        unique_urls = []
        seen = set()
        for item in candidates:
            canonical = item.rstrip("/")
            if canonical in seen:
                continue
            seen.add(canonical)
            unique_urls.append(canonical)

        return unique_urls

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

    def _build_listing_cards_from_rsc(self, listing_url):
        payload = self._safe_get_rsc_listing_payload(listing_url)
        if not payload:
            return []

        detail_urls = self._extract_detail_urls_from_rsc_payload(payload)
        if not detail_urls:
            return []

        pseudo_soup = BeautifulSoup("", "html.parser")
        cards = []
        for detail_url in detail_urls:
            path = urlparse(detail_url).path or ""
            if not path.startswith("/internships/"):
                continue
            cards.append(pseudo_soup.new_tag("a", href=path))

        if cards:
            logger.info(
                "HiInterns RSC extracted %s internship URLs from %s",
                len(cards),
                listing_url,
            )
        return cards

    def _safe_get_rsc_listing_payload(self, listing_url):
        token = "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=5))
        separator = "&" if "?" in listing_url else "?"
        rsc_url = f"{listing_url}{separator}_rsc={token}"

        try:
            self._rate_limit_delay()
            response = self.session.get(
                rsc_url,
                timeout=self.timeout,
                headers={
                    "Accept": "text/x-component, text/plain;q=0.9, */*;q=0.8",
                },
            )
            response.raise_for_status()

            content_type = (response.headers.get("content-type") or "").lower()
            if "text/x-component" not in content_type:
                logger.info(
                    "HiInterns RSC response is not text/x-component (url=%s, content_type=%s)",
                    rsc_url,
                    content_type,
                )
            return response.text
        except requests.RequestException as exc:
            logger.warning("HiInterns RSC request failed for %s: %s", rsc_url, exc)
            return ""

    def _extract_detail_urls_from_rsc_payload(self, payload):
        if not payload:
            return []

        normalized_payload = payload.replace("\\/", "/")

        raw_paths = re.findall(
            r"/internships/[a-z0-9][a-z0-9\-]*",
            normalized_payload,
            flags=re.IGNORECASE,
        )

        raw_full_urls = re.findall(
            r"https?://hi-interns\.com/internships/[a-z0-9][a-z0-9\-]*",
            normalized_payload,
            flags=re.IGNORECASE,
        )

        unique_urls = []
        seen = set()

        for path in raw_paths:
            canonical = urljoin(self.source_url, path)
            if canonical not in seen:
                seen.add(canonical)
                unique_urls.append(canonical)
            if len(unique_urls) >= self.rsc_max_urls:
                return unique_urls

        for full_url in raw_full_urls:
            canonical = full_url.rstrip("/")
            if canonical not in seen:
                seen.add(canonical)
                unique_urls.append(canonical)
            if len(unique_urls) >= self.rsc_max_urls:
                break

        return unique_urls

    def _safe_get_soup_with_playwright(self, url):
        try:
            from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
            from playwright.sync_api import sync_playwright
        except Exception as exc:  # noqa: BLE001 - optional dependency
            logger.warning("Playwright not available for HiInterns fallback: %s", exc)
            return None

        try:
            self._rate_limit_delay()
            trace_events = []
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=self.playwright_headless)
                context = browser.new_context(
                    user_agent=self.session.headers.get("User-Agent", ""),
                    locale="fr-FR",
                )
                page = context.new_page()

                if self.trace_api:
                    context.on(
                        "response",
                        lambda response: self._capture_trace_response(response, trace_events),
                    )

                page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=self.playwright_timeout_ms,
                )
                try:
                    page.wait_for_selector(
                        "a[href*='/internships/']",
                        timeout=self.playwright_timeout_ms,
                    )
                except PlaywrightTimeoutError:
                    logger.info(
                        "Playwright loaded %s but selector did not appear before timeout",
                        url,
                    )

                if self.playwright_wait_ms:
                    page.wait_for_timeout(self.playwright_wait_ms)

                html = page.content()
                if self.trace_api:
                    self._log_trace_events(url, trace_events)
                context.close()
                browser.close()
                return BeautifulSoup(html, "html.parser")
        except Exception as exc:  # noqa: BLE001 - scraper resiliency
            logger.warning("Playwright render failed for %s: %s", url, exc)
            return None

    def _capture_trace_response(self, response, trace_events):
        if len(trace_events) >= self.trace_api_max_events:
            return

        try:
            url = response.url or ""
        except Exception:
            return

        if not self._is_trace_candidate_url(url):
            return

        event = {
            "url": url,
            "status": "unknown",
            "method": "",
            "content_type": "",
            "request_body_preview": "",
            "response_body_preview": "",
        }

        try:
            event["status"] = str(response.status)
        except Exception:
            pass

        try:
            headers = response.headers or {}
            event["content_type"] = headers.get("content-type", "")
        except Exception:
            pass

        try:
            req = response.request
            event["method"] = req.method or ""
            if self.trace_api_include_bodies:
                post_data = req.post_data or ""
                if post_data:
                    event["request_body_preview"] = self._truncate_trace_text(post_data)
        except Exception:
            pass

        if self.trace_api_include_bodies:
            try:
                response_text = response.text() or ""
                if response_text:
                    event["response_body_preview"] = self._truncate_trace_text(response_text)
            except Exception:
                pass

        trace_events.append(event)

    def _is_trace_candidate_url(self, url):
        parsed = urlparse(url or "")
        host = (parsed.netloc or "").lower()
        path = (parsed.path or "").lower()
        query = (parsed.query or "").lower()

        if not (host or path):
            return False

        if self.trace_first_party_only and "hi-interns.com" not in host:
            return False

        noisy_paths = (
            "/mobility",
            "/pricing",
            "/dashboard",
            "/auth/login",
            "/api/redirect/",
        )
        if any(path.startswith(noisy) for noisy in noisy_paths):
            return False

        if "/api/" in path or "/trpc" in path:
            return True

        if path == "/internships" or path.startswith("/internships/"):
            return True

        if "_rsc" in query and path.startswith("/internships"):
            return True

        return False

    def _truncate_trace_text(self, text):
        compact = self._clean_text(text)
        if len(compact) <= self.trace_api_max_body_chars:
            return compact
        return compact[: self.trace_api_max_body_chars] + " ...<truncated>"

    def _log_trace_events(self, listing_url, trace_events):
        if not trace_events:
            self._emit_trace(
                "HiInterns trace: no candidate API calls captured for %s",
                listing_url,
            )
            return

        self._emit_trace(
            "HiInterns trace: captured %s candidate calls for %s",
            len(trace_events),
            listing_url,
        )

        detail_urls = self._build_trace_shortlist_detail_urls(trace_events)
        if detail_urls:
            self._emit_trace(
                "HiInterns trace: shortlist %s internship detail URLs",
                len(detail_urls),
            )
            for idx, detail_url in enumerate(detail_urls, start=1):
                self._emit_trace("HiInterns detail_url #%s %s", idx, detail_url)

        for idx, event in enumerate(trace_events, start=1):
            self._emit_trace(
                "HiInterns trace #%s method=%s status=%s content_type=%s url=%s",
                idx,
                event.get("method", ""),
                event.get("status", "unknown"),
                event.get("content_type", ""),
                event.get("url", ""),
            )
            if self.trace_api_include_bodies and event.get("request_body_preview"):
                self._emit_trace(
                    "HiInterns trace #%s request_body=%s",
                    idx,
                    event["request_body_preview"],
                )
            if self.trace_api_include_bodies and event.get("response_body_preview"):
                self._emit_trace(
                    "HiInterns trace #%s response_body=%s",
                    idx,
                    event["response_body_preview"],
                )

    def _build_trace_shortlist_detail_urls(self, trace_events):
        urls = []
        seen = set()
        for event in trace_events:
            parsed = urlparse(event.get("url", ""))
            path = (parsed.path or "").strip()
            if not path.startswith("/internships/"):
                continue

            canonical = urljoin(self.source_url, path)
            if canonical in seen:
                continue

            seen.add(canonical)
            urls.append(canonical)
            if len(urls) >= self.trace_detail_urls_max:
                break

        return urls

    def _emit_trace(self, message, *args):
        logger.info(message, *args)
        if self.trace_api and self.trace_stdout:
            if args:
                try:
                    print(message % args)
                    return
                except Exception:
                    pass
            print(message)

    def _extract_listing_cards(self, soup):
        cards = []
        for selector in self.LISTING_CARD_SELECTORS:
            cards.extend(soup.select(selector))

        filtered = []
        for card in cards:
            href = self._clean_text(card.get("href"))
            is_relative_detail = href.startswith("/internships/") and href != "/internships"
            is_absolute_detail = href.startswith("https://hi-interns.com/internships/")
            if is_relative_detail or is_absolute_detail:
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
