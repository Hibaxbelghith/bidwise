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

from opportunities.scraping.keejob_scraper import KeejobScraper
from opportunities.scraping.scraper_utils import clean_description_for_ml


LISTING_HTML = """
<html>
  <body>
    <article>
            <h2><a href="/offres-emploi/123/job-one/">Développeur Python</a></h2>
      <i class="fa-clock"></i><span>aujourd'hui</span>
    </article>
    <article>
            <h2><a href="/offres-emploi/456/job-two/">Data Analyst</a></h2>
      <i class="fa-clock"></i><span>hier</span>
    </article>
    <article>
      <h2>Not a job card</h2>
    </article>
  </body>
</html>
"""


LISTING_CDI_ONLY_HTML = """
<html>
  <body>
    <article>
      <h2><a href="/offres-emploi/999/job-cdi/">Ingénieur QA</a></h2>
      <i class="fa-clock"></i><span>aujourd'hui</span>
    </article>
  </body>
</html>
"""


DETAIL_STAGE_HTML = """
<html>
    <body>
        <h1>Développeur Python</h1>
        <a href="/offres-emploi/companies/123/">ACME Corp</a>
        <h3>Lieu de travail</h3>
        <p>Tunis, Tunisie</p>
        <h3>Type de contrat</h3>
        <span>Stage</span>
        <div class="prose">Mission principale&nbsp;: développer des APIs. Profil requis&nbsp;: Python.</div>
    </body>
</html>
"""


DETAIL_CDI_HTML = """
<html>
    <body>
        <h1>Data Analyst</h1>
        <a href="/offres-emploi/companies/999/">BETA Labs</a>
        <h3>Lieu de travail</h3>
        <p>Sfax, Tunisie</p>
        <h3>Type de contrat</h3>
        <span>CDI</span>
        <div class="prose">Analyser et structurer les données. Maîtrise SQL demandée.</div>
    </body>
</html>
"""


DETAIL_EMPTY_DESCRIPTION_HTML = """
<html>
    <body>
        <h1>Sans description</h1>
        <a href="/offres-emploi/companies/555/">Gamma Corp</a>
        <h3>Lieu de travail</h3>
        <p>Tunis</p>
        <h3>Type de contrat</h3>
        <span>CDI</span>
    </body>
</html>
"""


DETAIL_HEADER_LOCATION_HTML = """
<html>
    <body>
        <h1>Développeur Backend</h1>
        <a href="/offres-emploi/companies/321/">Header Corp</a>
        <div class="flex flex-wrap items-center gap-4 mt-2">
            <i class="fas fa-map-marker-alt"></i><span>Ariana</span>
        </div>
        <h3>Type de contrat</h3>
        <span>CDI</span>
        <div class="prose">
            <p>Construire des services backend.</p>
        </div>
    </body>
</html>
"""


DETAIL_HTML_JSONLD_COMPANY = """
<html>
    <body>
        <h1>Assistant comptable</h1>
        <h3>Type de contrat</h3>
        <span>CDD</span>
        <h3>Lieu de travail</h3>
        <p>Hammam Sousse</p>
        <div class="prose">Detailed mission from fallback scenario.</div>
        <script type="application/ld+json">
            {"@type":"JobPosting","hiringOrganization":{"@type":"Organization","name":"Entreprise Anonyme"}}
        </script>
    </body>
</html>
"""


DETAIL_STRUCTURED_HTML = """
<html>
    <body>
        <h1>Ingénieur QA</h1>
        <div class="p-6 space-y-4">
            <div>
                <h3>Référence</h3>
                <p>REF-123</p>
            </div>
            <div>
                <h3>Date de publication</h3>
                <p>10 avril 2026</p>
            </div>
            <div>
                <h3>Expérience</h3>
                <p>3 à 5 ans</p>
            </div>
            <div>
                <h3>Niveau d'études</h3>
                <p>Bac+5</p>
            </div>
            <div>
                <h3>Disponibilité</h3>
                <p>Immédiate</p>
            </div>
            <div>
                <h3>Salaire proposé</h3>
                <span class="badge">700 -1000 TND / Mois</span>
            </div>
            <div>
                <h3>Langues</h3>
                <p><span>Arabe</span><span>Français</span></p>
            </div>
        </div>
        <div>
            <span>Secteur:</span> Industrie
        </div>
        <div>
            <span>Taille:</span> 50-100 employés
        </div>
    </body>
</html>
"""


DETAIL_DUPLICATE_DESCRIPTION_HTML = """
<html>
    <body>
        <div class="prose">
            <p>Bloc A</p>
            <p>Bloc B</p>
            <p>Bloc A</p>
        </div>
    </body>
</html>
"""


def _soup():
    return BeautifulSoup(LISTING_HTML, "html.parser")


def _cdi_only_soup():
    return BeautifulSoup(LISTING_CDI_ONLY_HTML, "html.parser")


def _detail_stage_soup():
    return BeautifulSoup(DETAIL_STAGE_HTML, "html.parser")


def _detail_cdi_soup():
    return BeautifulSoup(DETAIL_CDI_HTML, "html.parser")


def _detail_empty_description_soup():
    return BeautifulSoup(DETAIL_EMPTY_DESCRIPTION_HTML, "html.parser")


def _detail_header_location_soup():
    return BeautifulSoup(DETAIL_HEADER_LOCATION_HTML, "html.parser")


def _detail_soup_jsonld_company():
    return BeautifulSoup(DETAIL_HTML_JSONLD_COMPANY, "html.parser")


def _detail_structured_soup():
    return BeautifulSoup(DETAIL_STRUCTURED_HTML, "html.parser")


def _detail_duplicate_description_soup():
    return BeautifulSoup(DETAIL_DUPLICATE_DESCRIPTION_HTML, "html.parser")


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


def test_record_validation_rules_non_aggressive():
    scraper = KeejobScraper()
    assert not scraper._is_valid_record({"title": "", "description": "desc", "url": "https://x.com"})
    assert not scraper._is_valid_record(
        {"title": "Senior Developer", "description": "", "url": "https://x.com"}
    )
    assert not scraper._is_valid_record(
        {"title": "Senior Developer", "description": "desc", "url": ""}
    )
    assert scraper._is_valid_record(
        {"title": "Dev", "description": "desc", "url": "notaurl"}
    )


def test_fetch_raw_records_uses_detail_only_fields(monkeypatch):
    scraper = KeejobScraper()

    def fake_safe_get_soup(url):
        if "job-one" in url:
            return _detail_stage_soup()
        if "job-two" in url:
            return _detail_empty_description_soup()
        return _soup()

    monkeypatch.setattr(scraper, "_safe_get_soup", fake_safe_get_soup)
    records = scraper.fetch_raw_records()

    assert len(records) == 1
    assert records[0]["title"] == "Développeur Python"
    assert records[0]["organization"] == "ACME Corp"
    assert records[0]["organization_normalized"] == "acme corp"
    assert records[0]["location"] == "Tunis"
    assert records[0]["type_opportunite"] == "STAGE"
    assert records[0]["contract_type"] == "Stage"
    assert records[0]["type_contrat"] == "Stage"
    assert "Mission principale" in records[0]["description"]
    assert "Profil requis" in records[0]["description"]
    assert records[0]["url"] == "https://www.keejob.com/offres-emploi/123/job-one/"
    assert records[0]["reference"] is None
    assert records[0]["published_at"] is None
    assert records[0]["experience"] is None
    assert records[0]["education_level"] is None
    assert records[0]["availability"] is None
    assert records[0]["salary"] is None
    assert records[0]["languages"] is None
    assert records[0]["company_sector"] is None
    assert records[0]["company_size"] is None


def test_extract_company_from_detail():
    scraper = KeejobScraper()
    assert scraper._extract_detail_company(_detail_stage_soup()) == "ACME Corp"


def test_extract_detail_company_falls_back_to_jsonld_when_link_missing():
    scraper = KeejobScraper()
    assert scraper._extract_detail_company(_detail_soup_jsonld_company()) == "Entreprise Anonyme"


def test_extract_structured_fields_from_detail_sidebar_and_company_info():
    scraper = KeejobScraper()
    fields = scraper._extract_structured_detail_fields(_detail_structured_soup())

    assert fields["reference"] == "REF-123"
    assert fields["published_at"] == "10 avril 2026"
    assert fields["experience"] == "3 à 5 ans"
    assert fields["education_level"] == "Bac+5"
    assert fields["availability"] == "Immédiate"
    assert fields["salary"] == "700 -1000 TND / Mois"
    assert fields["languages"] == ["Arabe", "Français"]
    assert fields["company_sector"] == "Industrie"
    assert fields["company_size"] == "50-100 employés"


def test_extract_structured_fields_missing_return_none_without_crash():
    scraper = KeejobScraper()
    fields = scraper._extract_structured_detail_fields(_detail_stage_soup())

    assert fields["reference"] is None
    assert fields["published_at"] is None
    assert fields["experience"] is None
    assert fields["education_level"] is None
    assert fields["availability"] is None
    assert fields["salary"] is None
    assert fields["languages"] is None
    assert fields["company_sector"] is None
    assert fields["company_size"] is None


def test_structured_payload_schema_is_consistent_even_with_partial_extractor(monkeypatch):
    scraper = KeejobScraper()

    def fake_safe_get_soup(url):
        if "job-one" in url:
            return _detail_stage_soup()
        return _soup()

    monkeypatch.setattr(scraper, "_safe_get_soup", fake_safe_get_soup)
    monkeypatch.setattr(
        scraper,
        "_extract_structured_detail_fields",
        lambda _detail_soup: {"experience": "2 ans"},
    )

    records = scraper.fetch_raw_records()

    assert len(records) == 1
    expected_keys = {
        "reference",
        "published_at",
        "experience",
        "education_level",
        "availability",
        "salary",
        "languages",
        "company_sector",
        "company_size",
    }
    assert expected_keys.issubset(set(records[0].keys()))
    assert records[0]["experience"] == "2 ans"
    assert records[0]["reference"] is None
    assert records[0]["published_at"] is None
    assert records[0]["education_level"] is None
    assert records[0]["availability"] is None
    assert records[0]["salary"] is None
    assert records[0]["languages"] is None
    assert records[0]["company_sector"] is None
    assert records[0]["company_size"] is None


def test_type_mapping_binary_stage_and_emploi_only():
    scraper = KeejobScraper()

    assert scraper._map_contract_to_opportunity_type("Stage", "x", "y") == "STAGE"
    assert scraper._map_contract_to_opportunity_type("CDI", "x", "y") == "EMPLOI"
    assert scraper._map_contract_to_opportunity_type("Indépendant/Freelance", "x", "y") == "EMPLOI"
    assert scraper._map_contract_to_opportunity_type("", "x", "y") == "EMPLOI"


def test_description_extraction_from_prose():
    scraper = KeejobScraper()
    description = scraper._extract_detail_description(_detail_stage_soup())

    assert "Mission principale" in description
    assert "Profil requis" in description
    assert "\xa0" not in description


def test_description_extraction_deduplicates_repeated_blocks():
    scraper = KeejobScraper()
    description = scraper._extract_detail_description(_detail_duplicate_description_soup())

    lines = [line for line in description.split("\n") if line]
    assert lines == ["Bloc A", "Bloc B"]


def test_location_fallback_to_header_when_sidebar_missing():
    scraper = KeejobScraper()

    assert scraper._extract_detail_location(_detail_header_location_soup()) == ""
    assert scraper._extract_header_location(_detail_header_location_soup()) == "Ariana"


def test_clean_location_preserves_granularity_and_drops_country():
    scraper = KeejobScraper()

    assert scraper._clean_location("Sbikha, Kairouan, Tunisie") == "Sbikha, Kairouan"


def test_enrich_location_from_description_recovers_locality():
    scraper = KeejobScraper()
    description = "Poste basé à la zone industrielle SBIKHA Kairouan."

    assert scraper._enrich_location_from_description("Kairouan", description) == "Sbikha, Kairouan"


def test_stage_only_builds_keejob_stage_listing_urls():
    scraper = KeejobScraper(stage_only=True)

    page1 = scraper._build_listing_url(1)
    page2 = scraper._build_listing_url(2)

    assert "job_types=9" in page1
    assert "page=1" in page1
    assert "job_types=9" in page2
    assert "page=2" in page2


def test_stage_only_filter_skips_non_stage_contract(monkeypatch):
    scraper = KeejobScraper(stage_only=True)

    def fake_safe_get_soup(url):
        if "job-cdi" in url:
            return _detail_cdi_soup()
        return _cdi_only_soup()

    monkeypatch.setattr(scraper, "_safe_get_soup", fake_safe_get_soup)
    records = scraper.fetch_raw_records()

    assert len(records) == 0


def test_clean_description_preserves_raw_source_text_for_replay():
    source_text = "Republica tunisienne Draft text that should stay available as raw source"
    cleaned, raw = clean_description_for_ml(source_text)

    assert cleaned
    assert raw == source_text
