import os
import sys
from pathlib import Path
from types import SimpleNamespace

from django.test import SimpleTestCase


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from opportunities.nlp.nlp_preprocessing import (  # noqa: E402
    build_embedding_text,
    clean_tender_text,
    detect_content_type,
    extract_tender_structure,
    get_preprocessing_stats,
    prepare_combined_text,
    prepare_text_for_nlp,
    reset_preprocessing_stats,
)


class NLPPreprocessingTests(SimpleTestCase):
    def test_prepare_text_removes_html_urls_emails_and_boilerplate(self):
        raw = """
        <div>
          Cliquez ici!!! Envoyer CV a talent@example.com
          https://example.com/jobs
          Data engineer cloud platform with python and analytics workloads.
        </div>
        """
        cleaned = prepare_text_for_nlp(raw)

        self.assertTrue(cleaned)
        self.assertNotIn("<div>", cleaned)
        self.assertNotIn("http", cleaned)
        self.assertNotIn("example.com", cleaned)
        self.assertNotIn("talent@example.com", cleaned)
        self.assertNotIn("cliquez ici", cleaned)
        self.assertNotIn("envoyer cv", cleaned)
        self.assertIn("data engineer cloud platform", cleaned)

    def test_prepare_text_normalizes_case_accents_and_repeated_punctuation(self):
        raw = "Developpeur SENIOR!!! Python?? Donnees, APIs, integration continue."
        cleaned = prepare_text_for_nlp(raw)

        self.assertTrue(cleaned)
        self.assertIn("developpeur senior", cleaned)
        self.assertIn("python", cleaned)
        self.assertNotIn("!!!", cleaned)
        self.assertNotIn("??", cleaned)

    def test_prepare_text_adds_structured_hints_for_tender_like_rows(self):
        raw = (
            "1 DI 19/03/2026 Nat./TUN Avis de consultation "
            "Acquisition de materiel informatique 21/03/2026 10:00:00"
        )
        cleaned = prepare_text_for_nlp(raw)

        self.assertTrue(cleaned)
        self.assertIn("type: avis de consultation", cleaned)
        self.assertIn("publication date: 19/03/2026", cleaned)
        self.assertIn("deadline: 21/03/2026", cleaned)
        self.assertIn("location: tun", cleaned)
        self.assertIn("acquisition de materiel informatique", cleaned)
        self.assertNotIn("nat./tun", cleaned)
        self.assertNotIn("1 di", cleaned)

    def test_structured_extraction_before_cleaning_preserves_tender_signals(self):
        raw = "1 DI 19/03/2026 Nat./TUN Avis de consultation Acquisition materiel 21/03/2026"

        structured = extract_tender_structure(raw)
        cleaned_text = clean_tender_text(raw)
        embedding_text = build_embedding_text(raw)

        self.assertEqual(structured["tender_type"], "avis de consultation")
        self.assertEqual(structured["publication_date"], "19/03/2026")
        self.assertEqual(structured["deadline"], "21/03/2026")
        self.assertEqual(structured["location"], "tun")
        self.assertIn("avis de consultation", cleaned_text)
        self.assertNotIn("nat./tun", cleaned_text)
        self.assertIn("publication date: 19/03/2026", embedding_text)
        self.assertIn("deadline: 21/03/2026", embedding_text)
        self.assertIn("location: tun", embedding_text)

    def test_prepare_text_short_job_input_is_not_dropped(self):
        reset_preprocessing_stats()
        cleaned = prepare_text_for_nlp("Data Engineer Python SQL AWS")
        stats = get_preprocessing_stats()

        self.assertTrue(cleaned)
        self.assertIn("data engineer python sql aws", cleaned)
        self.assertGreaterEqual(stats["cleaned_records"], 1)

    def test_job_enrichment(self):
        text = "Business Analyst Senior H/F Sousse CDI"
        cleaned = prepare_text_for_nlp(text)

        self.assertTrue(cleaned)
        self.assertIn("contract:", cleaned)
        self.assertIn("location:", cleaned)
        self.assertIn("title:", cleaned)
        self.assertIn("sousse", cleaned)
        self.assertNotIn("business analyst senior h/f business analyst senior h/f business analyst senior h/f", cleaned)

    def test_detect_content_type_splits_tender_and_job(self):
        tender_text = "Avis de consultation pour acquisition de materiel"
        job_text = "Data Engineer Python SQL AWS"

        self.assertEqual(detect_content_type(tender_text), "tender")
        self.assertEqual(detect_content_type(job_text), "job")

    def test_noisy_tender_is_structured_and_cleaned(self):
        raw = "2 fe 19/03/2026 nat./tun acquisition des tenues de travail..."
        cleaned = prepare_text_for_nlp(raw)

        self.assertTrue(cleaned)
        self.assertIn("publication date: 19/03/2026", cleaned)
        self.assertIn("location: tun", cleaned)
        self.assertIn("acquisition des tenues de travail", cleaned)
        self.assertNotIn("2 fe", cleaned)
        self.assertNotIn("nat./tun", cleaned)

    def test_prepare_text_is_truncated_to_max_length(self):
        raw = ("semantic embeddings data pipeline " * 200).strip()
        cleaned = prepare_text_for_nlp(raw)

        self.assertTrue(cleaned)
        self.assertLessEqual(len(cleaned), 900)

    def test_prepare_combined_text_uses_title_description_org_location(self):
        opportunity = {
            "titre": "Stage Data Engineer",
            "description": "Conception de pipelines de donnees et qualite des donnees en production.",
            "organization": "BidWise",
            "location": "Tunis",
        }

        combined = prepare_combined_text(opportunity)

        self.assertTrue(combined)
        combined_lower = combined.lower()
        self.assertIn("stage data engineer", combined_lower)
        self.assertIn("bidwise", combined_lower)
        self.assertIn("tunis", combined_lower)

    def test_prepare_combined_text_removes_embedding_artifacts_for_jobs(self):
        opportunity = {
            "titre": "Business Analyst Senior H/F Sousse CDI",
            "description": "type: job title: business analyst senior h/f sousse cdi",
            "organization": "BidWise",
            "location": "Sousse",
        }

        combined = prepare_combined_text(opportunity)

        self.assertTrue(combined)
        combined_lower = combined.lower()
        self.assertNotIn("type: job", combined_lower)
        self.assertNotIn("title:", combined_lower)

    def test_prepare_combined_text_keeps_rich_job_sections_for_jobbert(self):
        opportunity = SimpleNamespace(
            titre="Developpeur Frontend React",
            description="""
            A propos de nous: societe digitale en croissance.
            Missions: developper des interfaces React, integrer des APIs REST,
            construire des composants reutilisables et optimiser les pages responsive.
            Profil recherche: junior avec JavaScript, HTML, CSS, Git et sens produit.
            Avantages: environnement dynamique.
            """,
            organisation_nom="BidWise",
            ville="Tunis",
            contract_type="CDI",
            availability="Plein temps",
            normalized_work_mode="HYBRID",
            experience_min=0,
            experience_max=2,
            education_level="Bac+3",
            salary="",
            skills=["React", "JavaScript"],
            raw_skills=[],
            normalized_skills=[{"preferred_label": "web development"}],
            languages=["Francais"],
            extra_data={"company_sector": "informatique / telecoms"},
            type_opportunite="EMPLOI",
            source=SimpleNamespace(nom="Keejob"),
        )

        combined = prepare_combined_text(opportunity)
        combined_lower = combined.lower()

        self.assertTrue(combined)
        self.assertLessEqual(len(combined), 2200)
        self.assertIn("developpeur frontend react", combined_lower)
        self.assertIn("keejob", combined_lower)
        self.assertIn("informatique", combined_lower)
        self.assertIn("developper des interfaces react", combined_lower)
        self.assertIn("integrer des apis rest", combined_lower)
        self.assertIn("javascript", combined_lower)
        self.assertIn("web development", combined_lower)

    def test_prepare_combined_text_uses_ville_and_extra_data_metadata(self):
        opportunity = SimpleNamespace(
            titre="Comptable Junior",
            description="Missions: saisie comptable, factures fournisseurs, rapprochement bancaire.",
            organisation_nom="Cabinet Finance",
            ville="Sousse",
            contract_type="CDI",
            availability="Plein temps",
            normalized_work_mode="ON_SITE",
            experience_min=1,
            experience_max=2,
            experience_years=None,
            education_level="Bac+3",
            salary="",
            skills=["Excel", "Sage"],
            raw_skills=[],
            normalized_skills=[],
            languages=[],
            extra_data={"company_sector": "comptabilite / gestion / audit"},
            type_opportunite="EMPLOI",
            source=SimpleNamespace(nom="Keejob"),
        )

        combined = prepare_combined_text(opportunity).lower()

        self.assertIn("sousse", combined)
        self.assertIn("comptabilite", combined)
        self.assertIn("1-2 years", combined)
        self.assertIn("excel", combined)
        self.assertIn("rapprochement bancaire", combined)

    def test_prepare_combined_text_handles_future_non_job_opportunity_types(self):
        opportunity = {
            "titre": "Projet de maintenance reseau fibre optique",
            "description": (
                "Avis de consultation: acquisition et maintenance des equipements reseau. "
                "Exigences: fibre optique, configuration routeur, support technique."
            ),
            "organisation_nom": "Office Telecom",
            "ville": "Tunis",
            "type_opportunite": "PROJET",
            "source": {"nom": "MarchesPublics"},
            "extra_data": {"sector": "telecoms"},
        }

        combined = prepare_combined_text(opportunity).lower()

        self.assertIn("projet de maintenance reseau fibre optique", combined)
        self.assertIn("marchespublics", combined)
        self.assertIn("telecoms", combined)
        self.assertIn("fibre optique", combined)
        self.assertIn("support technique", combined)

    def test_prepare_combined_text_prioritizes_llm_matching_fields_for_jobbert(self):
        opportunity = {
            "titre": "Poste technique",
            "description": "Nous recrutons pour renforcer notre equipe.",
            "organisation_nom": "Digital Factory",
            "ville": "Tunis",
            "skills": [],
            "type_opportunite": "EMPLOI",
            "source": {"nom": "Keejob"},
            "extra_data": {
                "llm_enrichment": {
                    "canonical_role": "Frontend Developer",
                    "target_roles": ["React Developer"],
                    "skills": ["React", "JavaScript"],
                    "tools": ["TypeScript"],
                    "soft_skills": ["Communication", "Autonomy"],
                    "domains": ["Web application development"],
                    "years_experience_min": 1,
                    "years_experience_max": 2,
                    "contract_types": ["CDI"],
                    "work_modes": ["Hybrid"],
                    "locations": ["Tunis"],
                    "salary": "1200-1800 TND",
                    "education_level": "Bac+3",
                    "responsibilities": ["Build responsive UI components"],
                    "requirements": ["One year frontend experience"],
                    "evidence": ["React user interfaces"],
                }
            },
        }

        combined = prepare_combined_text(opportunity).lower()

        self.assertIn("extracted role - frontend developer", combined)
        self.assertIn("react developer", combined)
        self.assertIn("react", combined)
        self.assertIn("typescript", combined)
        self.assertIn("soft skills - communication", combined)
        self.assertIn("autonomy", combined)
        self.assertIn("1-2 years", combined)
        self.assertIn("hybrid", combined)
        self.assertIn("1200-1800 tnd", combined)
        self.assertIn("build responsive ui components", combined)
