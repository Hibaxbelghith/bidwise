import os
import sys
from datetime import date, timedelta
from pathlib import Path

from bs4 import BeautifulSoup


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from opportunities.models import StatutOpportunite, TypeOpportunite
from opportunities.scraping.keejob_scraper import KeejobScraper
from opportunities.scraping.parser import normalize_opportunity


LISTING_HTML = """
<html>
  <body>
    <article>
      <h2><a href="/offres-emploi/123/job-one/">Senior Data Analyst</a></h2>
      <p><a>Acme Corp</a></p>
      <div class="mb-3"><p>Great opportunity in analytics.</p></div>
      <i class="fa-map-marker-alt"></i><span>Tunis</span>
      <i class="fa-clock"></i><span>aujourd'hui</span>
    </article>
    <article>
      <h2><a href="/offres-emploi/456/job-two/">Dev</a></h2>
      <p><a>Another Corp</a></p>
      <div class="mb-3"><p></p></div>
      <i class="fa-map-marker-alt"></i><span>Sfax</span>
      <i class="fa-clock"></i><span>hier</span>
    </article>
    <article>
      <h2>Not a job card</h2>
    </article>
  </body>
</html>
"""


def _soup():
    return BeautifulSoup(LISTING_HTML, "html.parser")


def test_extract_cards_filters_non_job_articles():
    scraper = KeejobScraper()
    cards = scraper._extract_cards(_soup())
    assert len(cards) == 2


def test_extract_url_builds_absolute_url():
    scraper = KeejobScraper()
    cards = scraper._extract_cards(_soup())
    url = scraper._extract_url(cards[0])
    assert url == "https://www.keejob.com/offres-emploi/123/job-one/"


def test_normalize_publication_date_variants():
    scraper = KeejobScraper()
    today = date.today()

    assert scraper._normalize_publication_date("aujourd'hui") == today.isoformat()
    assert scraper._normalize_publication_date("hier") == (today - timedelta(days=1)).isoformat()
    assert scraper._normalize_publication_date("2 jours") == (today - timedelta(days=2)).isoformat()
    assert scraper._normalize_publication_date("15/03/2026") == "2026-03-15"


def test_record_validation_rules():
    scraper = KeejobScraper()
    assert not scraper._is_valid_record({"title": "Dev", "description": "desc", "url": "https://x.com"})
    assert not scraper._is_valid_record(
        {"title": "Senior Developer", "description": "", "url": "https://x.com"}
    )
    assert not scraper._is_valid_record(
        {"title": "Senior Developer", "description": "desc", "url": "notaurl"}
    )
    assert scraper._is_valid_record(
        {"title": "Senior Developer", "description": "desc", "url": "https://x.com/job"}
    )


def test_fetch_raw_records_filters_invalid_records(monkeypatch):
    scraper = KeejobScraper()
    monkeypatch.setattr(scraper, "_safe_get_soup", lambda url: _soup())
    records = scraper.fetch_raw_records()

    assert len(records) == 1
    assert records[0]["title"] == "Senior Data Analyst"
    assert records[0]["organization"] == "Acme Corp"
    assert records[0]["location"] == "Tunis"
    assert records[0]["url"] == "https://www.keejob.com/offres-emploi/123/job-one/"


def test_parser_normalization_contract_from_scraper_record():
    raw_record = {
        "title": "Senior Data Analyst",
        "description": "Great opportunity in analytics.",
        "publication_date": "2026-03-15",
        "source_name": "Keejob",
        "source_url": "https://www.keejob.com/offres-emploi/",
        "source_type": "SITE_EMPLOI",
    }
    default_source = {
        "name": "Fallback Source",
        "url": "https://fallback.example/jobs",
        "type_source": "AUTRE",
    }

    normalized = normalize_opportunity(raw_record, default_source=default_source)

    assert normalized["titre"] == "Senior Data Analyst"
    assert normalized["description"] == "Great opportunity in analytics."
    assert normalized["date_publication"].isoformat() == "2026-03-15"
    assert normalized["type_opportunite"] == TypeOpportunite.EMPLOI
    assert normalized["statut"] == StatutOpportunite.ACTIVE
    assert normalized["source_name"] == "Keejob"
    assert normalized["organisation_nom"] == ""


def test_parser_populates_organisation_nom_from_raw_organization():
    raw_record = {
        "title": "Business Analyst",
        "description": "We are hiring now",
        "organization": "Acme Corp",
        "publication_date": "2026-03-15",
        "source_name": "Keejob",
        "source_url": "https://www.keejob.com/offres-emploi/",
        "source_type": "SITE_EMPLOI",
    }
    default_source = {
        "name": "Fallback Source",
        "url": "https://fallback.example/jobs",
        "type_source": "AUTRE",
    }

    normalized = normalize_opportunity(raw_record, default_source=default_source)

    assert normalized["organisation_nom"] == "Acme Corp"
