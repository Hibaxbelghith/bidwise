from django.test import SimpleTestCase

from opportunities.scoring.quality import compute_quality_score, compute_quality_score_v3


class QualityScoreV3Tests(SimpleTestCase):
    def test_missing_location_gets_final_hard_penalty(self):
        with_location = compute_quality_score_v3(
            titre="Senior Data Engineer",
            organisation_nom="ACME Data",
            ville="Tunis, Tunisia",
            description="Build reliable data pipelines.\n- Python\n- SQL\n- Airflow",
            description_html="<p>Build reliable data pipelines.</p><ul><li>Python</li><li>SQL</li></ul>",
            source_item_url="https://www.linkedin.com/jobs/view/senior-data-engineer-123",
            date_confidence="ESTIMATED",
            skills=["python", "sql", "airflow"],
            source_name="LinkedIn",
            debug=True,
        )
        without_location = compute_quality_score_v3(
            titre="Senior Data Engineer",
            organisation_nom="ACME Data",
            ville="",
            description="Build reliable data pipelines.\n- Python\n- SQL\n- Airflow",
            description_html="<p>Build reliable data pipelines.</p><ul><li>Python</li><li>SQL</li></ul>",
            source_item_url="https://www.linkedin.com/jobs/view/senior-data-engineer-123",
            date_confidence="ESTIMATED",
            skills=["python", "sql", "airflow"],
            source_name="LinkedIn",
            debug=True,
        )

        self.assertFalse(without_location["available"]["location"])
        self.assertGreater(without_location["weights"]["location"], 0.0)
        self.assertGreater(without_location["score"], 0.4)
        self.assertGreater(with_location["score"] - without_location["score"], 0.1)

    def test_title_quality_filters_generic_or_location_only_titles(self):
        generic = compute_quality_score_v3(
            titre="Tunisia Job",
            organisation_nom="ACME",
            ville="Tunis",
            description="Detailed description with concrete responsibilities and stack.",
            source_item_url="https://example.com/jobs/view/123",
            date_confidence="EXACT",
            source_name="Keejob",
            debug=True,
        )
        specific = compute_quality_score_v3(
            titre="Finance Manager",
            organisation_nom="ACME",
            ville="Tunis",
            description="Detailed description with concrete responsibilities and reporting scope.",
            source_item_url="https://example.com/jobs/view/123",
            date_confidence="EXACT",
            source_name="Keejob",
            debug=True,
        )

        self.assertLess(generic["details"]["title"], 0.5)
        self.assertGreater(specific["details"]["title"], generic["details"]["title"])

    def test_skills_score_rewards_diversity_over_duplicates(self):
        duplicated = compute_quality_score_v3(
            titre="Data Engineer",
            organisation_nom="ACME",
            ville="Tunis",
            description="Build data pipelines with SQL and Python.",
            source_item_url="https://example.com/jobs/view/123",
            date_confidence="EXACT",
            skills=["python", "python", "python", "sql"],
            source_name="LinkedIn",
            debug=True,
        )
        diverse = compute_quality_score_v3(
            titre="Data Engineer",
            organisation_nom="ACME",
            ville="Tunis",
            description="Build data pipelines with SQL and Python.",
            source_item_url="https://example.com/jobs/view/123",
            date_confidence="EXACT",
            skills=["python", "sql", "airflow", "aws"],
            source_name="LinkedIn",
            debug=True,
        )

        self.assertLess(duplicated["details"]["skills"], diverse["details"]["skills"])

    def test_source_reliability_is_light_adjustment_only(self):
        keejob = compute_quality_score_v3(
            titre="Backend Engineer",
            organisation_nom="ACME",
            ville="Tunis",
            description="Strong description with enough context to score well.",
            source_item_url="https://www.keejob.com/offres-emploi/backend-engineer-123/",
            date_confidence="EXACT",
            skills=["python", "django", "sql"],
            source_name="Keejob",
            debug=True,
        )
        linkedin = compute_quality_score_v3(
            titre="Backend Engineer",
            organisation_nom="ACME",
            ville="Tunis",
            description="Strong description with enough context to score well.",
            source_item_url="https://www.linkedin.com/jobs/view/backend-engineer-123/",
            date_confidence="EXACT",
            skills=["python", "django", "sql"],
            source_name="LinkedIn",
            debug=True,
        )

        self.assertGreater(keejob["score"], linkedin["score"])
        self.assertLess(keejob["score"] - linkedin["score"], 0.03)

    def test_debug_mode_returns_breakdown_and_wrapper_stays_backward_compatible(self):
        debug_payload = compute_quality_score_v3(
            titre="Finance Manager",
            organisation_nom="CLASQUIN",
            ville="Tunis, Tunisia",
            description="Analyse financiere, reporting et cash management.",
            source_item_url="https://tn.linkedin.com/jobs/view/finance-manager-123",
            date_confidence="ESTIMATED",
            skills=["financial analysis", "reporting", "cash management"],
            source_name="LinkedIn",
            debug=True,
        )
        legacy_score = compute_quality_score(
            organisation_nom="CLASQUIN",
            ville="Tunis, Tunisia",
            description="Analyse financiere, reporting et cash management.",
            source_item_url="https://tn.linkedin.com/jobs/view/finance-manager-123",
            date_confidence="ESTIMATED",
        )

        self.assertIn("score", debug_payload)
        self.assertIn("details", debug_payload)
        self.assertIn("weights", debug_payload)
        self.assertIn("source_multiplier", debug_payload)
        self.assertIsInstance(legacy_score, float)
        self.assertGreaterEqual(debug_payload["score"], 0.0)
        self.assertLessEqual(debug_payload["score"], 1.0)

    def test_project_scoring_uses_project_bonus_and_ignores_job_skill_signals(self):
        project_payload = compute_quality_score_v3(
            titre="Acquisition de matériels roulants",
            organisation_nom="Municipalité Ben Arous",
            ville="Ben Arous",
            description="Acquisition de matériels roulants pour la commune de Ben Arous. Procédure: appel d'offres ouvert.",
            source_item_url="https://www.marchespublics.gov.tn/fr/appels-doffres/Tender-101425",
            date_confidence="EXACT",
            date_publication="2026-04-08",
            source_name="MarchesPublics",
            type_opportunite="PROJET",
            date_limite="2026-05-11",
            extra_data={
                "procedure": "Appel d'offres ouvert",
                "financement": "Budget",
                "type_commande": "Biens",
                "region_execution": "BEN AROUS",
                "lots": [{"lot": "Lot 1", "objet": "Acquisition de voitures de services"}],
                "pdf_url": "https://www.marchespublics.gov.tn/storage/tender/avis.pdf",
                "documents": [
                    {
                        "type": "avis_appel_offres",
                        "url": "https://www.marchespublics.gov.tn/storage/tender/avis.pdf",
                        "label": "Avis d'appel d'offres",
                    }
                ],
            },
            skills=["python", "sql"],
            debug=True,
        )

        self.assertNotIn("skills", project_payload["details"])
        self.assertGreaterEqual(project_payload["project_bonus"], 0.5)
        self.assertGreater(project_payload["score"], 0.8)
