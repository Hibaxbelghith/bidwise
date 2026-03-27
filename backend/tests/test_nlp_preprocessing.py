import os
import sys
from pathlib import Path

from django.test import SimpleTestCase


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from opportunities.nlp_preprocessing import (  # noqa: E402
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
        self.assertIn("stage data engineer", combined)
        self.assertIn("bidwise", combined)
        self.assertIn("tunis", combined)

    def test_prepare_combined_text_removes_embedding_artifacts_for_jobs(self):
        opportunity = {
            "titre": "Business Analyst Senior H/F Sousse CDI",
            "description": "type: job title: business analyst senior h/f sousse cdi",
            "organization": "BidWise",
            "location": "Sousse",
        }

        combined = prepare_combined_text(opportunity)

        self.assertTrue(combined)
        self.assertNotIn("type: job", combined)
        self.assertNotIn("title:", combined)
