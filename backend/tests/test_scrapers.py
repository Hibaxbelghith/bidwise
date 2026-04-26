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

from opportunities.scraping.sources import KeejobScraper
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
        <a href="/offres-emploi/companies/123/">
            <img src="/media/recruiter/acme/logo.png" alt="ACME" />
            ACME Corp
        </a>
        <h3>Lieu de travail</h3>
        <p>Tunis, Tunisie</p>
        <h3>Type de contrat</h3>
        <span>Stage</span>
        <div class="prose">
            <h3>Missions</h3>
            <ul>
                <li>Mission principale&nbsp;: développer des APIs.</li>
            </ul>
            <p>Profil requis&nbsp;: Python.</p>
            <script>alert("x")</script>
        </div>
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
                <h3>Date limite</h3>
                <p>20 avril 2026</p>
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


DETAIL_PUBLICATION_CALENDAR_HTML = """
<html>
    <body>
        <h1>Comptable</h1>
        <div>
            <i class="fas fa-calendar-alt mr-1 text-gray-500 dark:text-gray-400"></i>
            <span>Publiée le 12 avril 2026</span>
        </div>
        <h3>Type de contrat</h3>
        <span>Saisonnier</span>
        <div class="prose"><p>Mission comptable.</p></div>
    </body>
</html>
"""


DETAIL_PUBLICATION_SIMILAR_ONLY_HTML = """
<html>
    <body>
        <h1>Responsable Stock</h1>
        <div>Offres similaires</div>
        <div>Publiée le 05 avril 2026</div>
    </body>
</html>
"""


DETAIL_LOGO_AMBIGUOUS_HTML = """
<html>
    <body>
        <h1>Office Manager Sousse</h1>
        <div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden mt-6">
            <div>Offres similaires</div>
            <div class="divide-y divide-gray-200 dark:divide-gray-700">
                <div class="p-4 hover:bg-gray-50 dark:hover:bg-gray-700">
                    <div class="flex items-center">
                        <div class="w-12 h-12 flex-shrink-0 mr-4">
                            <img src="/media/recruiter/recruiter_27713/logo-27713-20260108-154401.webp.300x300_q85_crop-smart.png" alt="SEPT SUR SEPT DISPATCHING&amp;LOGISTIC logo" />
                        </div>
                    </div>
                </div>
                <div class="p-4 hover:bg-gray-50 dark:hover:bg-gray-700">
                    <div class="flex items-center">
                        <div class="w-12 h-12 flex-shrink-0 mr-4">
                            <img src="/media/recruiter/recruiter_13089/logo-13089-20170928-092629.png.300x300_q85_crop-smart.jpg" alt="VEO WORLDWIDE SERVICES logo" />
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden mb-6">
            <div class="p-6">
                <div class="flex flex-col md:flex-row items-start">
                    <div class="w-24 h-24 flex-shrink-0 mb-4 md:mb-0 md:mr-6">
                        <img src="/media/recruiter/recruiter_13089/logo-13089-20170928-092629.png" alt="VEO WORLDWIDE SERVICES logo" />
                    </div>
                    <div>
                        <h2>Entreprise</h2>
                        <p>VEO WORLDWIDE SERVICES</p>
                        <p>Secteur: consulting</p>
                        <p>Taille: Plus de 500 employes</p>
                    </div>
                </div>
            </div>
        </div>
    </body>
</html>
"""


DETAIL_EXPIRED_BADGE_HTML = """
<html>
    <body>
        <h1>Développeur Full Stack</h1>
        <span class="badge text-red-500">Offre expirée</span>
        <a href="/offres-emploi/companies/456/">Expired Corp</a>
        <h3>Lieu de travail</h3>
        <p>Tunis</p>
        <h3>Type de contrat</h3>
        <span>CDI</span>
        <div class="p-6 space-y-4">
            <div>
                <h3>Date limite</h3>
                <p>10/01/2024</p>
            </div>
        </div>
        <div class="prose"><p>Poste backend confirmé.</p></div>
    </body>
</html>
"""


DETAIL_EXPIRED_DARK_BADGE_HTML = """
<html>
    <body>
        <h1>Conseiller commercial</h1>
        <div class="bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200 px-3 py-1 rounded-full text-sm font-medium inline-block mt-3">Expirée</div>
        <a href="/offres-emploi/companies/777/">Dark Badge Corp</a>
        <h3>Lieu de travail</h3>
        <p>Tunis</p>
        <h3>Type de contrat</h3>
        <span>CDI</span>
        <div class="prose"><p>Poste commercial terrain.</p></div>
    </body>
</html>
"""


DETAIL_UNRELATED_EXPIRED_TEXT_HTML = """
<html>
    <body>
        <h1>Commercial</h1>
        <p>Le client mentionne une ancienne offre expirée dans son historique.</p>
        <h3>Type de contrat</h3>
        <span>CDI</span>
    </body>
</html>
"""


DETAIL_MISSING_CONTRACT_HTML = """
<html>
    <body>
        <h1>Assistant administratif</h1>
        <div class="p-6 space-y-4">
            <div>
                <h3>Type de contrat</h3>
                <span>Lieu du travail</span>
            </div>
            <div>
                <h3>Lieu de travail</h3>
                <p>Sousse</p>
            </div>
        </div>
    </body>
</html>
"""


DETAIL_CONTRACT_STAGE_PFE_HTML = """
<html>
    <body>
        <h1>Stagiaire QA</h1>
        <div class="p-6 space-y-4">
            <div>
                <h3>Type de contrat</h3>
                <span>stage/pfe</span>
            </div>
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

DETAIL_LI_PARAGRAPH_DESCRIPTION_HTML = """
<html>
    <body>
        <div class="prose">
            <ul>
                <li><p>Tache A</p></li>
                <li><p>Tache B</p></li>
            </ul>
        </div>
    </body>
</html>
"""


def _soup():
    return BeautifulSoup(LISTING_HTML, "html.parser")


def _cdi_only_soup():
    return BeautifulSoup(LISTING_CDI_ONLY_HTML, "html.parser")


def _detail_li_paragraph_description_soup():
    return BeautifulSoup(DETAIL_LI_PARAGRAPH_DESCRIPTION_HTML, "html.parser")

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


def _detail_publication_calendar_soup():
    return BeautifulSoup(DETAIL_PUBLICATION_CALENDAR_HTML, "html.parser")


def _detail_publication_similar_only_soup():
    return BeautifulSoup(DETAIL_PUBLICATION_SIMILAR_ONLY_HTML, "html.parser")


def _detail_logo_ambiguous_soup():
    return BeautifulSoup(DETAIL_LOGO_AMBIGUOUS_HTML, "html.parser")


def _detail_duplicate_description_soup():
    return BeautifulSoup(DETAIL_DUPLICATE_DESCRIPTION_HTML, "html.parser")


def _detail_expired_badge_soup():
    return BeautifulSoup(DETAIL_EXPIRED_BADGE_HTML, "html.parser")


def _detail_expired_dark_badge_soup():
    return BeautifulSoup(DETAIL_EXPIRED_DARK_BADGE_HTML, "html.parser")


def _detail_unrelated_expired_text_soup():
    return BeautifulSoup(DETAIL_UNRELATED_EXPIRED_TEXT_HTML, "html.parser")


def _detail_missing_contract_soup():
    return BeautifulSoup(DETAIL_MISSING_CONTRACT_HTML, "html.parser")


def _detail_contract_stage_pfe_soup():
    return BeautifulSoup(DETAIL_CONTRACT_STAGE_PFE_HTML, "html.parser")


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
    assert scraper._normalize_publication_date("Publiée le 12 avril 2026") == "2026-04-12"


def test_extract_detail_publication_date_from_calendar_badge():
    scraper = KeejobScraper()
    assert scraper._extract_detail_publication_date(_detail_publication_calendar_soup()) == "2026-04-12"


def test_extract_detail_publication_date_ignores_similar_offers_only_dates():
    scraper = KeejobScraper()
    assert scraper._extract_detail_publication_date(_detail_publication_similar_only_soup()) == ""


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
    assert records[0]["company_logo"] == "https://www.keejob.com/media/recruiter/acme/logo.png"
    assert records[0]["location"] == "Tunis"
    assert records[0]["type_opportunite"] == "STAGE"
    assert records[0]["contract_type"] == "Stage"
    assert records[0]["type_contrat"] == "Stage"
    assert "<strong>Missions</strong>" in records[0]["description_html"]
    assert "<li>" in records[0]["description_html"]
    assert "Mission principale" in records[0]["description_html"]
    assert "Profil requis" in records[0]["description_html"]
    assert "script" not in records[0]["description_html"].lower()
    assert records[0]["statut"] == "ACTIVE"
    assert records[0]["status"] == "ACTIVE"
    assert records[0]["deadline"] is None
    assert records[0]["date_limite"] is None
    assert len(records[0]["external_id"]) == 40
    assert "Mission principale" in records[0]["description"]
    assert "Profil requis" in records[0]["description"]
    assert records[0]["url"] == "https://www.keejob.com/offres-emploi/123/job-one"
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


def test_extract_company_logo_from_relative_detail_img():
    scraper = KeejobScraper()
    logo_url = scraper._extract_detail_company_logo(
        _detail_stage_soup(),
        "https://www.keejob.com/offres-emploi/123/job-one/",
    )
    assert logo_url == "https://www.keejob.com/media/recruiter/acme/logo.png"


def test_extract_company_logo_prefers_company_section_over_similar_offers():
    scraper = KeejobScraper()
    logo_url = scraper._extract_detail_company_logo(
        _detail_logo_ambiguous_soup(),
        "https://www.keejob.com/offres-emploi/239154/office-manager-sousse/",
        "VEO WORLDWIDE SERVICES",
    )

    assert "recruiter_13089" in logo_url
    assert "recruiter_27713" not in logo_url


def test_extract_detail_company_falls_back_to_jsonld_when_link_missing():
    scraper = KeejobScraper()
    assert scraper._extract_detail_company(_detail_soup_jsonld_company()) == "Entreprise Anonyme"


def test_extract_structured_fields_from_detail_sidebar_and_company_info():
    scraper = KeejobScraper()
    fields = scraper._extract_structured_detail_fields(_detail_structured_soup())

    assert fields["reference"] == "REF-123"
    assert fields["published_at"] == "10 avril 2026"
    assert fields["deadline"] == "20 avril 2026"
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
    assert fields["deadline"] is None
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
        "deadline",
        "date_limite",
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
    assert records[0]["deadline"] is None
    assert records[0]["date_limite"] is None
    assert records[0]["education_level"] is None
    assert records[0]["availability"] is None
    assert records[0]["salary"] is None
    assert records[0]["languages"] is None
    assert records[0]["company_sector"] is None
    assert records[0]["company_size"] is None


def test_type_mapping_assigns_saisonnier_only_from_contract_type():
    scraper = KeejobScraper()

    assert scraper._map_contract_to_opportunity_type("SAISONNIER", "x", "y") == "SAISONNIER"
    assert scraper._map_contract_to_opportunity_type("Stage", "x", "y") == "STAGE"
    assert scraper._map_contract_to_opportunity_type("CDD", "Agent saisonnier", "prime saisonniere") == "EMPLOI"
    assert scraper._map_contract_to_opportunity_type("CDI", "x", "y") == "EMPLOI"
    assert scraper._map_contract_to_opportunity_type("Indépendant/Freelance", "x", "y") == "EMPLOI"
    assert scraper._map_contract_to_opportunity_type("", "x", "y") == "EMPLOI"


def test_listing_roots_include_diversified_filters_by_default():
    scraper = KeejobScraper(max_pages=1, stage_only=False)
    roots = scraper._build_listing_roots()

    assert any("keywords=saisonnier" in url for url in roots)
    assert any("job_types=9" in url for url in roots)
    assert any(url.startswith("https://www.keejob.com/offres-emploi") for url in roots)


def test_listing_roots_stage_only_keeps_single_stage_listing():
    scraper = KeejobScraper(max_pages=1, stage_only=True)
    roots = scraper._build_listing_roots()

    assert len(roots) == 1
    assert "job_types=9" in roots[0]


def test_description_extraction_from_prose():
    scraper = KeejobScraper()
    description = scraper._extract_detail_description(_detail_stage_soup())

    assert "Mission principale" in description
    assert "Profil requis" in description
    assert "\xa0" not in description


def test_description_html_sanitization_keeps_structure_and_drops_script():
    scraper = KeejobScraper()
    description_html = scraper._extract_detail_description_html(_detail_stage_soup())

    assert "<strong>Missions</strong>" in description_html
    assert "<ul>" in description_html
    assert "<li>" in description_html
    assert "Mission principale" in description_html
    assert "<script" not in description_html.lower()


def test_detail_status_detects_expired_badge():
    scraper = KeejobScraper()
    assert scraper._extract_detail_status(_detail_expired_badge_soup()) == "EXPIREE"


def test_detail_status_detects_expired_dark_red_badge():
    scraper = KeejobScraper()
    assert scraper._extract_detail_status(_detail_expired_dark_badge_soup()) == "EXPIREE"


def test_detail_status_ignores_unrelated_expired_text_without_badge():
    scraper = KeejobScraper()
    assert scraper._extract_detail_status(_detail_unrelated_expired_text_soup()) == "ACTIVE"


def test_extract_detail_contract_type_returns_empty_when_value_is_invalid():
    scraper = KeejobScraper()
    assert scraper._extract_detail_contract_type(_detail_missing_contract_soup()) == ""


def test_extract_detail_contract_type_normalizes_stage_pfe():
    scraper = KeejobScraper()
    assert scraper._extract_detail_contract_type(_detail_contract_stage_pfe_soup()) == "Stage/PFE"


def test_fetch_raw_records_marks_expired_when_explicit_badge_present(monkeypatch):
    scraper = KeejobScraper()

    def fake_safe_get_soup(url):
        if "job-one" in url:
            return _detail_expired_badge_soup()
        return _soup()

    monkeypatch.setattr(scraper, "_safe_get_soup", fake_safe_get_soup)
    records = scraper.fetch_raw_records()

    assert len(records) == 1
    assert records[0]["statut"] == "EXPIREE"
    assert records[0]["status"] == "EXPIREE"
    assert records[0]["date_limite"] == "10/01/2024"


def test_fetch_raw_records_keeps_active_without_expired_badge_even_if_deadline_is_past(monkeypatch):
    scraper = KeejobScraper()

    def fake_safe_get_soup(url):
        if "job-one" in url:
            return _detail_stage_soup()
        return _soup()

    monkeypatch.setattr(scraper, "_safe_get_soup", fake_safe_get_soup)
    monkeypatch.setattr(
        scraper,
        "_extract_structured_detail_fields",
        lambda _detail_soup: {"deadline": "10/01/2024"},
    )

    records = scraper.fetch_raw_records()

    assert len(records) == 1
    assert records[0]["statut"] == "ACTIVE"
    assert records[0]["status"] == "ACTIVE"
    assert records[0]["date_limite"] == "10/01/2024"


def test_description_extraction_deduplicates_repeated_blocks():
    scraper = KeejobScraper()
    description = scraper._extract_detail_description(_detail_duplicate_description_soup())

    lines = [line for line in description.split("\n") if line]
    assert lines == ["Bloc A", "Bloc B"]


def test_description_extraction_avoids_li_paragraph_double_counting():
    scraper = KeejobScraper()
    description = scraper._extract_detail_description(_detail_li_paragraph_description_soup())

    lines = [line for line in description.split("\n") if line]
    assert lines == ["- Tache A", "- Tache B"]


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
