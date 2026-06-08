import os
import requests
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

from django.conf import settings  # noqa: E402
from opportunities.scraping.sources import linkedin as linkedin_module  # noqa: E402
from opportunities.scraping.sources.linkedin import (  # noqa: E402
    DESCRIPTION_QUALITY_DETAIL,
    DESCRIPTION_QUALITY_METADATA,
    DESCRIPTION_QUALITY_SNIPPET,
    LinkedInScraper,
    MAX_PAGES_SAFE,
    PAGE_SIZE,
    _build_description,
    _merge_detail_data,
    _parse_job_card,
    parse_linkedin_job,
    parse_linkedin_job_detail_html,
    scrape_linkedin_jobs,
)
from opportunities.management.commands.collect_opportunities import Command  # noqa: E402


def test_build_description_uses_snippet_when_available():
    description, quality = _build_description(
        "Junior Frontend Developer",
        "Linedata",
        "Tunis, Tunisia",
        "Build React interfaces for financial software.",
        keyword="developer",
    )

    assert description == "Build React interfaces for financial software."
    assert quality == DESCRIPTION_QUALITY_SNIPPET


def test_build_description_enriches_metadata_without_fake_listing_text():
    description, quality = _build_description(
        "Junior Frontend Developer",
        "Linedata",
        "Tunis, Tunisia",
        "",
        keyword="developer",
    )

    assert "LinkedIn public job listing" not in description
    assert "Role: Junior Frontend Developer." in description
    assert "Company: Linedata." in description
    assert "Location: Tunis, Tunisia." in description
    assert "Search keyword: developer." in description
    assert quality == DESCRIPTION_QUALITY_METADATA


def test_parse_job_card_marks_metadata_enriched_description():
    html = """
    <div class="base-card" data-entity-urn="urn:li:jobPosting:4405644242">
      <a class="base-card__full-link" href="https://tn.linkedin.com/jobs/view/full-stack-developer-at-light-speed-tech-4405644242?trk=public_jobs_jserp-result_search-card"></a>
      <h3 class="base-search-card__title">Full Stack Developer</h3>
      <h4 class="base-search-card__subtitle">Light Speed Tech.</h4>
      <span class="job-search-card__location">Ezzahra, Ben Arous, Tunisia</span>
      <time datetime="2026-04-23"></time>
    </div>
    """
    card = BeautifulSoup(html, "html.parser").select_one(".base-card")

    parsed = _parse_job_card(
        card,
        keyword="developer",
        location="Tunisia",
        source_listing_url="https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords=developer&location=tunisia&start=0",
    )

    assert parsed["description_quality"] == DESCRIPTION_QUALITY_METADATA
    assert parsed["source_reliability"] == "LOW"
    assert parsed["source_record_id"] == "4405644242"
    assert parsed["url"] == "https://tn.linkedin.com/jobs/view/full-stack-developer-at-light-speed-tech-4405644242"


def test_parse_public_linkedin_search_card_extracts_display_fields():
    html = """
    <div class="base-card job-search-card" data-entity-urn="urn:li:jobPosting:4400414873" data-row="2">
      <a class="base-card__full-link" href="https://tn.linkedin.com/jobs/view/human-resources-and-administrative-officer-at-presto-4400414873?position=2&amp;pageNum=0&amp;trk=public_jobs_jserp-result_search-card">
        <span class="sr-only">Human Resources and Administrative Officer</span>
      </a>
      <div class="search-entity-media">
        <img class="artdeco-entity-image" alt="" src="https://media.licdn.com/dms/image/v2/D4E0BAQEqEHiKJ4JsQg/company-logo_100_100/company-logo_100_100/0/prestoeat_logo" />
      </div>
      <div class="base-search-card__info">
        <h3 class="base-search-card__title">Human Resources and Administrative Officer</h3>
        <h4 class="base-search-card__subtitle">
          <a class="hidden-nested-link" href="https://ly.linkedin.com/company/prestoapplication?trk=public_jobs_jserp-result_job-search-card-subtitle">Presto</a>
        </h4>
        <div class="base-search-card__metadata">
          <span class="job-search-card__location">Tunis, Gouvernorat Tunis, Tunisie</span>
          <time class="job-search-card__listdate" datetime="2026-04-21">il y a 1 jour</time>
        </div>
      </div>
    </div>
    """
    card = BeautifulSoup(html, "html.parser").select_one(".job-search-card")

    parsed = _parse_job_card(
        card,
        keyword="",
        location="Tunisia",
        source_listing_url="https://www.linkedin.com/jobs/search?keywords=&location=Tunisia&pageNum=0",
    )

    assert parsed["title"] == "Human Resources and Administrative Officer"
    assert parsed["company_name"] == "Presto"
    assert parsed["location"] == "Tunis, Gouvernorat Tunis, Tunisie"
    assert parsed["company_logo"] == "https://media.licdn.com/dms/image/v2/D4E0BAQEqEHiKJ4JsQg/company-logo_100_100/company-logo_100_100/0/prestoeat_logo"
    assert parsed["publication_date"] == "2026-04-21"
    assert parsed["source_record_id"] == "4400414873"
    assert parsed["url"] == "https://tn.linkedin.com/jobs/view/human-resources-and-administrative-officer-at-presto-4400414873"


def test_parse_linkedin_logo_url_keeps_direct_source_url():
    html = """
    <section>
      <a data-tracking-control-name="public_jobs_topcard_logo" href="https://www.linkedin.com/company/pip">
        <img
          alt="Protective Industrial Products"
          src="https://media.licdn.com/dms/image/v2/D560BAQED0XNwfD373w/company-logo_100_100/B56Zb5oYEuHwAQ-/0/1747944833723/protective_industrial_products_logo?e=2147483647&amp;v=beta&amp;t=JOSFJKBFyVXqiLWpG-7TZRMt9gY9gPNorx-sh-Ooytg"
        />
      </a>
      <h1>Quality Manager</h1>
      <a href="https://www.linkedin.com/company/pip">Protective Industrial Products</a>
      <span>Tunis, Tunisia</span>
      <div data-testid="expandable-text-box"><p>Quality operations.</p></div>
    </section>
    """

    parsed = parse_linkedin_job_detail_html(
        html,
        job_url="https://tn.linkedin.com/jobs/view/quality-manager-123",
    )

    assert parsed["company_logo"] == (
        "https://media.licdn.com/dms/image/v2/D560BAQED0XNwfD373w/company-logo_100_100/"
        "B56Zb5oYEuHwAQ-/0/1747944833723/protective_industrial_products_logo?e=2147483647&v=beta&t=JOSFJKBFyVXqiLWpG-7TZRMt9gY9gPNorx-sh-Ooytg"
    )


def test_linkedin_scraper_accepts_collect_command_max_pages_alias():
    scraper = LinkedInScraper(max_pages=5, timeout=7, min_delay=0, max_delay=0)

    assert scraper.pages == 5
    assert scraper.timeout == 7
    assert scraper.min_delay == 0
    assert scraper.max_delay == 0


def test_collect_command_exposes_linkedin_search_options():
    parser = Command().create_parser("manage.py", "collect_opportunities")

    options = parser.parse_args(
        [
            "--source",
            "linkedin",
            "--keyword",
            "developer",
            "--location",
            "tunisia",
            "--max-pages",
            "5",
            "--fetch-details",
        ]
    )

    assert options.source == "linkedin"
    assert options.keyword == "developer"
    assert options.location == "tunisia"
    assert options.max_pages == 5
    assert options.fetch_details is True


def test_linkedin_pipeline_uses_configured_detail_fetch_by_default(monkeypatch):
    monkeypatch.setattr(settings, "SCRAPER_CONFIG", {
        "linkedin": {
            "max_pages": 3,
            "fetch_details": True,
        }
    })

    from opportunities.pipeline import resolve_source_collection

    collection = resolve_source_collection("linkedin")

    assert collection["scraper_kwargs"]["fetch_details"] is True


def test_scrape_linkedin_jobs_caps_pagination_to_safe_offset(monkeypatch):
    class FakeResponse:
        text = "<li></li>"

        def raise_for_status(self):
            return None

    class FakeSession:
        def __init__(self):
            self.starts = []

        def get(self, url, params, timeout):
            self.starts.append(params["start"])
            return FakeResponse()

        def close(self):
            return None

    fake_session = FakeSession()
    monkeypatch.setattr(linkedin_module, "_build_session", lambda: fake_session)
    monkeypatch.setattr(linkedin_module, "_rate_limit_delay", lambda **kwargs: None)
    monkeypatch.setattr(linkedin_module, "_extract_listing_cards", lambda soup: [object()])
    monkeypatch.setattr(
        linkedin_module,
        "_parse_job_card",
        lambda card, **kwargs: {
            "url": f"https://www.linkedin.com/jobs/view/{len(fake_session.starts)}",
            "external_id": str(len(fake_session.starts)),
            "source_record_id": str(len(fake_session.starts)),
        },
    )

    scrape_linkedin_jobs(pages=999, min_delay=0, max_delay=0)

    assert len(fake_session.starts) == MAX_PAGES_SAFE
    assert fake_session.starts[0] == 0
    assert fake_session.starts[-1] == (MAX_PAGES_SAFE - 1) * PAGE_SIZE
    assert all(start < linkedin_module.MAX_OFFSET for start in fake_session.starts)


def test_scrape_linkedin_jobs_stops_on_bad_request(monkeypatch):
    class FakeResponse:
        status_code = 400

    class FakeSession:
        def __init__(self):
            self.calls = 0

        def get(self, url, params, timeout):
            self.calls += 1
            exc = requests.HTTPError("400 Client Error")
            exc.response = FakeResponse()
            raise exc

        def close(self):
            return None

    fake_session = FakeSession()
    monkeypatch.setattr(linkedin_module, "_build_session", lambda: fake_session)
    monkeypatch.setattr(linkedin_module, "_rate_limit_delay", lambda **kwargs: None)

    results = scrape_linkedin_jobs(pages=999, min_delay=0, max_delay=0)

    assert results == []
    assert fake_session.calls == 1


def test_parse_linkedin_detail_html_without_css_classes():
    html = """
    <html>
      <body>
        <main>
          <section>
            <h1>Senior Data Engineer</h1>
            <a href="https://www.linkedin.com/company/acme-data">ACME Data</a>
            <img src="https://media.licdn.com/dms/image/company-logo_100_100/acme.png" alt="ACME Data Logo" />
            <span>Tunis, Tunisia</span>
            <span>Full-time</span>
            <span>2 days ago</span>
            <div data-testid="expandable-text-box">
              <p>Build reliable data pipelines.</p>
              <ul>
                <li>Python and SQL</li>
              </ul>
              <script>alert("noise")</script>
            </div>
            <a href="https://www.linkedin.com/safety/go?url=https%3A%2F%2Fjobs.example.com%2Fapply">Apply</a>
          </section>
        </main>
      </body>
    </html>
    """

    parsed = parse_linkedin_job_detail_html(
        html,
        job_url="https://tn.linkedin.com/jobs/view/senior-data-engineer-123",
    )

    assert parsed["title"] == "Senior Data Engineer"
    assert parsed["company_name"] == "ACME Data"
    assert parsed["company_logo"] == "https://media.licdn.com/dms/image/company-logo_100_100/acme.png"
    assert parsed["location"] == "Tunis, Tunisia"
    assert parsed["contract_type"] == "Temps plein"
    assert parsed["availability"] == "Temps plein"
    assert parsed["publication_date"] == (date.today() - timedelta(days=2)).isoformat()
    assert parsed["description_text"] == "Build reliable data pipelines. Python and SQL"
    assert "<p>Build reliable data pipelines.</p>" in parsed["description_html"]
    assert "<li>Python and SQL</li>" in parsed["description_html"]
    assert parsed["apply_url"] == "https://www.linkedin.com/safety/go?url=https%3A%2F%2Fjobs.example.com%2Fapply"
    assert "script" not in parsed["description_html"].lower()


def test_linkedin_jsonld_valid_through_sets_future_deadline_and_stays_active():
    html = """
    <html>
      <head>
        <script type="application/ld+json">
          {
            "@context": "https://schema.org",
            "@type": "JobPosting",
            "title": "Backend Engineer",
            "datePosted": "2026-06-01T08:00:00Z",
            "validThrough": "2026-07-15T23:59:59Z",
            "description": "Build reliable APIs.",
            "hiringOrganization": {"@type": "Organization", "name": "ACME"}
          }
        </script>
      </head>
      <body><h1>Backend Engineer</h1></body>
    </html>
    """

    parsed = parse_linkedin_job_detail_html(html)

    assert parsed["deadline"] == "2026-07-15"
    assert parsed["status"] == "ACTIVE"


def test_linkedin_closed_applications_text_sets_expired_status():
    html = """
    <section>
      <h1>Backend Engineer</h1>
      <a href="https://www.linkedin.com/company/example/">Example Inc</a>
      <div data-testid="expandable-text-box"><p>Build APIs.</p></div>
      <figure class="closed-job">
        <figcaption>Les candidatures ne sont plus acceptées</figcaption>
      </figure>
    </section>
    """

    parsed = parse_linkedin_job_detail_html(html)

    assert parsed["status"] == "EXPIREE"
    assert parsed["deadline"] is None


def test_linkedin_without_deadline_or_closed_signal_stays_active():
    parsed = parse_linkedin_job_detail_html(
        """
        <section>
          <h1>Backend Engineer</h1>
          <a href="https://www.linkedin.com/company/example/">Example Inc</a>
          <div data-testid="expandable-text-box"><p>Build APIs.</p></div>
        </section>
        """
    )

    assert parsed["status"] == "ACTIVE"
    assert parsed["deadline"] is None


def test_parse_linkedin_job_alias_uses_detail_parser():
    parsed = parse_linkedin_job(
        """
        <section>
          <h1>Backend Engineer</h1>
          <a href="https://www.linkedin.com/company/example/">Example Inc</a>
          <span data-testid="expandable-text-box"><p>Build APIs.</p></span>
        </section>
        """
    )

    assert parsed["title"] == "Backend Engineer"
    assert parsed["company_name"] == "Example Inc"
    assert parsed["description_text"] == "Build APIs."


def test_parse_public_linkedin_detail_pane_extracts_description_and_criteria():
    html = """
    <div class="details-pane__content details-pane__content--show">
      <section class="top-card-layout">
        <div class="top-card-layout__card">
          <a data-tracking-control-name="public_jobs_topcard_logo" href="https://ly.linkedin.com/company/prestoapplication?trk=public_jobs_topcard_logo">
            <img alt="Presto" src="https://media.licdn.com/dms/image/v2/D4E0BAQEqEHiKJ4JsQg/company-logo_100_100/company-logo_100_100/0/prestoeat_logo" />
          </a>
          <a class="topcard__link" data-tracking-control-name="public_jobs_topcard-title" href="https://tn.linkedin.com/jobs/view/human-resources-and-administrative-officer-at-presto-4400414873?trk=public_jobs_topcard-title">
            <h2 class="topcard__title">Human Resources and Administrative Officer</h2>
          </a>
          <div class="topcard__flavor-row">
            <span class="topcard__flavor">
              <a href="https://ly.linkedin.com/company/prestoapplication?trk=public_jobs_topcard-org-name" data-tracking-control-name="public_jobs_topcard-org-name">Presto</a>
            </span>
            <span class="topcard__flavor topcard__flavor--bullet">Tunis, Gouvernorat Tunis, Tunisie</span>
          </div>
          <div class="topcard__flavor-row">
            <span class="posted-time-ago__text topcard__flavor--metadata">il y a 1 jour</span>
            <span class="num-applicants__caption topcard__flavor--metadata topcard__flavor--bullet">161 candidats</span>
          </div>
          <button data-tracking-control-name="public_jobs_apply-link-onsite">Postuler</button>
        </div>
      </section>
      <section class="core-section-container description">
        <div class="description__text description__text--rich">
          <section data-max-lines="5" class="show-more-less-html">
            <div class="show-more-less-html__markup show-more-less-html__markup--clamp-after-5">
              <strong>HR &amp; Administrative Officer</strong>
              <p><strong>Location:</strong> Tunisia</p>
              <p>We are looking for a proactive and detail-oriented HR &amp; Administrative Officer.</p>
              <ul><li>Manage employee lifecycle</li><li>Support payroll preparation</li></ul>
            </div>
            <button class="show-more-less-html__button--more">Show more</button>
            <button class="show-more-less-html__button--less">Show less</button>
          </section>
        </div>
        <ul class="description__job-criteria-list">
          <li class="description__job-criteria-item">
            <h3 class="description__job-criteria-subheader">Type d’emploi</h3>
            <span class="description__job-criteria-text description__job-criteria-text--criteria">Temps plein</span>
          </li>
          <li class="description__job-criteria-item">
            <h3 class="description__job-criteria-subheader">Secteurs</h3>
            <span class="description__job-criteria-text description__job-criteria-text--criteria">Technologie, information et Internet</span>
          </li>
        </ul>
      </section>
      <code style="display: none" id="decoratedJobPostingId"><!--"4400414873"--></code>
    </div>
    """

    parsed = parse_linkedin_job_detail_html(
        html,
        job_url="https://tn.linkedin.com/jobs/view/human-resources-and-administrative-officer-at-presto-4400414873",
    )

    assert parsed["title"] == "Human Resources and Administrative Officer"
    assert parsed["company_name"] == "Presto"
    assert parsed["company_logo"] == "https://media.licdn.com/dms/image/v2/D4E0BAQEqEHiKJ4JsQg/company-logo_100_100/company-logo_100_100/0/prestoeat_logo"
    assert parsed["location"] == "Tunis, Gouvernorat Tunis, Tunisie"
    assert parsed["contract_type"] == "Temps plein"
    assert parsed["availability"] == "Temps plein"
    assert parsed["company_sector"] == "Technologie, information et Internet"
    assert parsed["publication_date"] == (date.today() - timedelta(days=1)).isoformat()
    assert "Manage employee lifecycle" in parsed["description_text"]
    assert "Show more" not in parsed["description_text"]
    assert "show-more-less-html__button" not in parsed["description_html"]
    assert parsed["apply_url"] == "https://tn.linkedin.com/jobs/view/human-resources-and-administrative-officer-at-presto-4400414873"


def test_parse_linkedin_detail_prefers_apply_link_over_badge_job_links_and_ignores_premium():
    html = """
    <section>
      <div>
        <a href="https://www.linkedin.com/company/honeyveil/life/">
          <figure>
            <img alt="Logo de l’entreprise, Honey Veil Co." src="https://media.licdn.com/dms/image/v2/D4E0BAQFRl_wrYW7BnA/company-logo_100_100/honeyveil_logo" />
          </figure>
          <p><a href="https://www.linkedin.com/company/honeyveil/life/">Honey Veil Co.</a></p>
        </a>
        <p>Social Media Content Creator &amp; Creative Assistant</p>
        <p><span>Miami, FL</span> · <span><strong>Republication il y a 2 heures</strong></span> · <span>30 candidats</span></p>
        <a href="https://www.linkedin.com/jobs/view/social-media-content-creator-creative-assistant-at-honey-veil-co-4402972793/">Hybride</a>
        <a href="https://www.linkedin.com/jobs/view/social-media-content-creator-creative-assistant-at-honey-veil-co-4402972793/">Temps plein</a>
        <a href="https://www.linkedin.com/jobs/view/4402972793/apply/?openSDUIApplyFlow=true&amp;trackingId=abc" aria-label="Candidature simplifiée pour ce poste">Candidature simplifiée</a>
      </div>
      <div>
        <p>Découvrez comment vous vous positionnez par rapport aux 30 candidats</p>
        <a href="https://www.linkedin.com/premium/products/?upsellOrderOrigin=Tracking%3Av1%3Apremium_job_details_summary_card">Essayer Premium pour 0 $</a>
      </div>
      <div>
        <h2>À propos de l’offre d’emploi</h2>
        <span data-testid="expandable-text-box">
          <p><strong>Company Description</strong></p>
          <p>Honey Veil Co. is a Miami-based modern matcha café.</p>
          <p><strong>The Role</strong></p>
          <p>We’re hiring a full-time Social Media Content Creator.</p>
          <button data-testid="expandable-text-button" aria-hidden="true">… plus</button>
        </span>
      </div>
    </section>
    """

    parsed = parse_linkedin_job_detail_html(
        html,
        job_url="https://www.linkedin.com/jobs/view/social-media-content-creator-creative-assistant-at-honey-veil-co-4402972793/",
    )

    assert parsed["title"] == "Social Media Content Creator & Creative Assistant"
    assert parsed["company_name"] == "Honey Veil Co."
    assert parsed["company_logo"] == "https://media.licdn.com/dms/image/v2/D4E0BAQFRl_wrYW7BnA/company-logo_100_100/honeyveil_logo"
    assert parsed["location"] == "Miami, FL"
    assert parsed["contract_type"] == "Temps plein"
    assert parsed["availability"] == "Temps plein"
    assert parsed["publication_date"] == date.today().isoformat()
    assert parsed["apply_url"] == "https://www.linkedin.com/jobs/view/4402972793/apply?openSDUIApplyFlow=true"
    assert "Honey Veil Co. is a Miami-based modern matcha café." in parsed["description_text"]
    assert "Essayer Premium" not in parsed["description_text"]
    assert "plus" not in parsed["description_text"].lower()


def test_parse_linkedin_detail_prefers_external_safety_apply_link():
    html = """
    <section>
      <a href="https://www.linkedin.com/company/maui-ocean-center-aquarium/life/">
        <img alt="Logo de l’entreprise, Maui Ocean Center." src="https://media.licdn.com/dms/image/v2/C560BAQGlbXne7umu_w/company-logo_100_100/company-logo_100_100/0/logo" />
        <p><a href="https://www.linkedin.com/company/maui-ocean-center-aquarium/life/">Maui Ocean Center</a></p>
      </a>
      <p>Aquarist</p>
      <p><span>Wailuku, HI</span> · <span><strong>il y a 4 heures</strong></span> · <span>0 personne a cliqué sur Postuler</span></p>
      <a href="https://www.linkedin.com/jobs/view/aquarist-at-maui-ocean-center-4405614489/">Temps partiel</a>
      <a href="https://www.linkedin.com/safety/go/?url=https%3A%2F%2Fmauioceancenter%2Ecom%2Fvacancy%2Faquarist-2026%2F&amp;urlhash=1Uhk&amp;isSdui=true" target="_blank">Postuler</a>
      <div>
        <a href="https://www.linkedin.com/premium/products/?upsellOrderOrigin=Tracking%3Av1%3Apremium_job_details_summary_card">Essayer Premium pour 0 $</a>
      </div>
      <span data-testid="expandable-text-box">
        <strong>JOB TITLE: AQUARIST</strong>
        <p>Responsible for animal care and exhibit maintenance.</p>
      </span>
    </section>
    """

    parsed = parse_linkedin_job_detail_html(
        html,
        job_url="https://www.linkedin.com/jobs/view/aquarist-at-maui-ocean-center-4405614489/",
    )

    assert parsed["title"] == "Aquarist"
    assert parsed["company_name"] == "Maui Ocean Center"
    assert parsed["company_logo"] == "https://media.licdn.com/dms/image/v2/C560BAQGlbXne7umu_w/company-logo_100_100/company-logo_100_100/0/logo"
    assert parsed["location"] == "Wailuku, HI"
    assert parsed["contract_type"] == "Temps partiel"
    assert parsed["availability"] == "Temps partiel"
    assert parsed["publication_date"] == date.today().isoformat()
    assert parsed["apply_url"].startswith("https://www.linkedin.com/safety/go/")
    assert "Responsible for animal care" in parsed["description_text"]


def test_parse_linkedin_detail_extracts_structured_contract_availability_education_and_skills():
    html = """
    <div class="details-pane__content details-pane__content--show">
      <section class="top-card-layout">
        <div class="top-card-layout__card">
          <a data-tracking-control-name="public_jobs_topcard_logo" href="https://ma.linkedin.com/company/redticmaroc">
            <img alt="RED TIC" src="https://media.licdn.com/dms/image/v2/D4E0BAQHvA79wEZpfEw/company-logo_100_100/company-logo_100_100/0/1703065889854/redticmaroc_logo" />
          </a>
          <a class="topcard__link" data-tracking-control-name="public_jobs_topcard-title" href="https://tn.linkedin.com/jobs/view/data-engineer-confirme-it-at-red-tic-4393247239">
            <h2 class="topcard__title">DATA ENGINEER CONFIRME (IT)</h2>
          </a>
          <div class="topcard__flavor-row">
            <span class="topcard__flavor">
              <a href="https://ma.linkedin.com/company/redticmaroc">RED TIC</a>
            </span>
            <span class="topcard__flavor topcard__flavor--bullet">Tunis, Gouvernorat Tunis, Tunisie</span>
          </div>
          <div class="topcard__flavor-row">
            <span class="posted-time-ago__text topcard__flavor--metadata">il y a 3 semaines</span>
          </div>
        </div>
      </section>
      <section class="core-section-container description">
        <div class="description__text description__text--rich">
          <section data-max-lines="5" class="show-more-less-html">
            <div class="show-more-less-html__markup show-more-less-html__markup--clamp-after-5">
              <ul><li>CDD</li><li>Tunis</li><li>Publié il y a 10 mois</li></ul>
              RED TIC recherche un(e) <strong>Data Engineer Confirmé(e)</strong>.
              <strong>Profil Recherché</strong>
              <ul>
                <li>Bac+5 en informatique, data engineering ou équivalent.</li>
                <li>Maîtrise avancée de SQL et d’un langage de programmation (Python, Scala).</li>
                <li>Solide expérience sur les outils et frameworks de traitement de données (Airflow, Spark, DBT).</li>
                <li>Connaissance des environnements cloud (GCP, AWS, Azure).</li>
              </ul>
            </div>
          </section>
        </div>
        <ul class="description__job-criteria-list">
          <li class="description__job-criteria-item">
            <h3 class="description__job-criteria-subheader">Type d'emploi</h3>
            <span class="description__job-criteria-text description__job-criteria-text--criteria">Temps plein</span>
          </li>
          <li class="description__job-criteria-item">
            <h3 class="description__job-criteria-subheader">Secteurs</h3>
            <span class="description__job-criteria-text description__job-criteria-text--criteria">Services et conseil en informatique</span>
          </li>
        </ul>
      </section>
    </div>
    """

    parsed = parse_linkedin_job_detail_html(
        html,
        job_url="https://tn.linkedin.com/jobs/view/data-engineer-confirme-it-at-red-tic-4393247239",
    )

    assert parsed["company_logo"] == "https://media.licdn.com/dms/image/v2/D4E0BAQHvA79wEZpfEw/company-logo_100_100/company-logo_100_100/0/1703065889854/redticmaroc_logo"
    assert parsed["publication_date"] == (date.today() - timedelta(days=21)).isoformat()
    assert parsed["contract_type"] == "CDD"
    assert parsed["availability"] == "Temps plein"
    assert parsed["education_level"] == "Bac+5"
    assert parsed["company_sector"] == "Services et conseil en informatique"
    assert {"python", "scala", "sql", "airflow", "spark", "dbt", "gcp", "aws", "azure"}.issubset(set(parsed["skills"]))
    assert len(parsed["skills"]) <= 10


def test_parse_linkedin_detail_prefers_description_contract_and_availability_labels():
    html = """
    <section>
      <a data-tracking-control-name="public_jobs_topcard_logo" href="https://www.linkedin.com/company/saiph">
        <img alt="SAIPH" src="https://media.licdn.com/dms/image/v2/C4D0BAQFEMi2z9FMgJw/company-logo_100_100/company-logo_100_100/0/1636362362408/saiph_logo" />
      </a>
      <h1>Agent de Prélèvement &amp; Contrôle</h1>
      <a href="https://www.linkedin.com/company/saiph">SAIPH</a>
      <span>Tunis, Gouvernorat Tunis, Tunisie</span>
      <span class="posted-time-ago__text">il y a 2 mois</span>
      <div class="show-more-less-html__markup">
        <strong>Description Du Poste</strong>
        <p>Type de Contrat: CDI</p>
        <p>Disponibilité: Plein temps présentiel</p>
        <strong>Exigences</strong>
        <ul>
          <li>Maîtrise des normes d'hygiène et des procédures qualité.</li>
          <li>Connaissance des procédures de prélèvement d'échantillons et de contrôle.</li>
          <li>Appliquer strictement les procédures qualité et les BPF.</li>
        </ul>
        <strong>Niveau Académique</strong>
        <ul>
          <li>Licence en qualité, hygiène ou dans un domaine connexe.</li>
        </ul>
      </div>
      <ul class="description__job-criteria-list">
        <li class="description__job-criteria-item">
          <h3 class="description__job-criteria-subheader">Type d'emploi</h3>
          <span class="description__job-criteria-text description__job-criteria-text--criteria">Temps plein</span>
        </li>
      </ul>
    </section>
    """

    parsed = parse_linkedin_job_detail_html(
        html,
        job_url="https://tn.linkedin.com/jobs/view/agent-prelevement-controle-123",
    )

    assert parsed["contract_type"] == "CDI"
    assert parsed["availability"] == "Plein temps présentiel"
    assert parsed["education_level"] == "Licence"
    assert {"bpf", "prelevement"}.issubset(set(parsed["skills"]))
    assert "qualite" not in set(parsed["skills"])


def test_parse_linkedin_detail_extracts_finance_skills_with_lightweight_nlp():
    html = """
    <section>
      <h1>Finance Manager Tunisie</h1>
      <a href="https://www.linkedin.com/company/clasquin">CLASQUIN</a>
      <span>Tunis, Tunisia</span>
      <div data-testid="expandable-text-box">
        <p>Analyse financiere, reporting financier et gestion de tresorerie.</p>
        <ul>
          <li>Suivi du P&amp;L et des budgets</li>
          <li>Coordination du cash management</li>
        </ul>
      </div>
    </section>
    """

    parsed = parse_linkedin_job_detail_html(
        html,
        job_url="https://tn.linkedin.com/jobs/view/finance-manager-tunisie-at-clasquin-4405009204",
    )

    assert {"financial analysis", "reporting", "cash management"}.issubset(set(parsed["skills"]))
    assert len(parsed["skills"]) <= 10


def test_merge_detail_data_promotes_rich_description_and_structured_fields():
    listing = {
        "title": "Data Engineer",
        "description": "Role: Data Engineer. Company: Unknown. Location: Tunisia.",
        "description_quality": DESCRIPTION_QUALITY_METADATA,
        "organization": "Unknown",
        "company_name": "Unknown",
        "location": "Tunisia",
        "publication_date": "2026-04-20",
        "date_publication": "2026-04-20",
        "type_opportunite": "EMPLOI",
        "opportunity_type": "EMPLOI",
    }
    detail_data = {
        "title": "Senior Data Engineer",
        "company_name": "ACME Data",
        "company_logo": "https://media.licdn.com/dms/image/company-logo_400_400/acme.png",
        "location": "Tunis, Tunisia",
        "contract_type": "CDD",
        "availability": "Temps plein",
        "publication_date": "2026-04-23",
        "description_text": "Build reliable data pipelines.",
        "description_html": "<p>Build reliable data pipelines.</p>",
        "education_level": "Bac+5",
        "job_qualifications": "Python\nSQL\nAirflow",
        "company_sector": "Services et conseil en informatique",
        "skills": ["python", "sql", "airflow"],
        "apply_url": "https://www.linkedin.com/safety/go?url=https%3A%2F%2Fjobs.example.com%2Fapply",
    }

    merged = _merge_detail_data(listing, detail_data, keyword="data")

    assert merged["title"] == "Senior Data Engineer"
    assert merged["organization"] == "ACME Data"
    assert merged["description"] == "Build reliable data pipelines."
    assert merged["description_quality"] == DESCRIPTION_QUALITY_DETAIL
    assert merged["company_logo"] == "https://media.licdn.com/dms/image/company-logo_400_400/acme.png"
    assert merged["contract_type"] == "CDD"
    assert merged["availability"] == "Temps plein"
    assert merged["date_publication"] == "2026-04-23"
    assert merged["education_level"] == "Bac+5"
    assert merged["job_qualifications"] == "Python\nSQL\nAirflow"
    assert merged["company_sector"] == "Services et conseil en informatique"
    assert merged["skills"] == ["python", "sql", "airflow"]
    assert merged["apply_url"].startswith("https://www.linkedin.com/safety/go")
