from __future__ import annotations

from datetime import date
from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

from ai.esco_normalization_recovery import (
    TARGET_OPPORTUNITIES,
    TARGET_PROFILES,
    TARGET_RESUMES,
    build_esco_normalization_report,
    run_backfill_for_target,
)
from ai.esco_skill_index import clear_esco_skill_index_cache
from ai.models import ESCOSkill
from opportunities.core.pipeline_flow import process_opportunity
from opportunities.models import Opportunite, SourceOpportunite, StatutOpportunite, TypeOpportunite
from users.models import ProfileResume, Utilisateur
from users.resume_semantic.models import ResumeSemanticSignals, SkillCandidate
from users.tasks import parse_profile_resume


PYTHON_URI = "http://data.europa.eu/esco/skill/ccd0a1d9-afda-43d9-b901-96344886e14d"


def _create_official_skill(
    *,
    uri: str,
    preferred_label: str,
    preferred_label_en: str = "",
    preferred_label_fr: str = "",
    alt_labels_en: list[str] | None = None,
    alt_labels_fr: list[str] | None = None,
):
    return ESCOSkill.objects.create(
        uri=uri,
        preferred_label=preferred_label,
        alt_labels=[*(alt_labels_en or []), *(alt_labels_fr or [])],
        preferred_label_en=preferred_label_en,
        preferred_label_fr=preferred_label_fr,
        alt_labels_en=alt_labels_en or [],
        alt_labels_fr=alt_labels_fr or [],
        hidden_labels_en=[],
        hidden_labels_fr=[],
        search_text_multilingual="",
    )


class ESCONormalizationRecoveryTests(TestCase):
    def setUp(self):
        clear_esco_skill_index_cache()

    def tearDown(self):
        clear_esco_skill_index_cache()

    @patch("ai.tasks.enqueue_opportunity_skill_normalization")
    @patch("opportunities.core.pipeline_flow.materialize_opportunity")
    @patch("opportunities.core.pipeline_flow.evaluate_opportunity")
    @patch("opportunities.core.pipeline_flow.enrich_opportunity_text")
    @patch("opportunities.core.pipeline_flow.normalize_raw_opportunity")
    def test_pipeline_flow_schedules_opportunity_normalization(
        self,
        mock_normalize_raw,
        mock_enrich,
        mock_evaluate,
        mock_materialize,
        mock_enqueue,
    ):
        mock_normalize_raw.return_value = {"skills": ["Python3"]}
        mock_enrich.return_value = {}
        mock_evaluate.side_effect = lambda payload: {**payload, "is_usable": True}
        mock_materialize.return_value = SimpleNamespace(pk=77)

        with self.captureOnCommitCallbacks(execute=True):
            process_opportunity(SimpleNamespace())

        mock_enqueue.assert_called_once_with(77)

    def test_backfill_opportunities_recovers_rows_with_only_legacy_skills(self):
        _create_official_skill(
            uri=PYTHON_URI,
            preferred_label="Python (computer programming)",
            preferred_label_en="Python (computer programming)",
            preferred_label_fr="Python (programmation informatique)",
            alt_labels_en=["Python3", "Py3K"],
        )
        source = SourceOpportunite.objects.create(
            nom="TestSource",
            url="https://example.com",
            type_source="SITE_EMPLOI",
        )
        opportunity = Opportunite.objects.create(
            titre="Backend Engineer",
            description="APIs with Python",
            organisation_nom="BidWise",
            ville="Tunis",
            contract_type="CDI",
            skills=["Python3"],
            raw_skills=[],
            normalized_skills=[],
            type_opportunite=TypeOpportunite.EMPLOI,
            statut=StatutOpportunite.ACTIVE,
            date_publication=date(2026, 5, 15),
            source=source,
        )

        before = build_esco_normalization_report(target=TARGET_OPPORTUNITIES, top_n=5)
        stats = run_backfill_for_target(TARGET_OPPORTUNITIES, chunk_size=10)
        after = build_esco_normalization_report(target=TARGET_OPPORTUNITIES, top_n=5)

        opportunity.refresh_from_db()
        self.assertEqual(before[TARGET_OPPORTUNITIES]["pending_entities"], 1)
        self.assertEqual(stats.updated, 1)
        self.assertEqual(stats.matched_entities, 1)
        self.assertEqual(opportunity.raw_skills, ["Python3"])
        self.assertEqual(len(opportunity.normalized_skills), 1)
        self.assertEqual(
            after[TARGET_OPPORTUNITIES]["entities_with_official_match"],
            1,
        )

    def test_backfill_profiles_recovers_rows_with_only_competences(self):
        _create_official_skill(
            uri=PYTHON_URI,
            preferred_label="Python (computer programming)",
            preferred_label_en="Python (computer programming)",
            preferred_label_fr="Python (programmation informatique)",
            alt_labels_en=["Py3K"],
        )
        user = Utilisateur.objects.create_user(
            username="recovery_profile",
            email="recovery_profile@example.com",
            password="pass1234",
        )
        profile = user.profil
        profile.competences = ["Py3K"]
        profile.raw_skills = []
        profile.normalized_skills = []
        profile.save(update_fields=["competences", "raw_skills", "normalized_skills"])

        stats = run_backfill_for_target(TARGET_PROFILES, chunk_size=10)

        profile.refresh_from_db()
        self.assertEqual(stats.updated, 1)
        self.assertEqual(stats.matched_entities, 1)
        self.assertEqual(profile.raw_skills, ["Py3K"])
        self.assertEqual(profile.normalized_skills[0]["esco_uri"], PYTHON_URI)

    @patch("users.resume_semantic.service.enrich_resume_text")
    def test_backfill_resumes_processes_historical_pending_rows(self, mock_enrich_resume_text):
        _create_official_skill(
            uri=PYTHON_URI,
            preferred_label="Python (computer programming)",
            preferred_label_en="Python (computer programming)",
            preferred_label_fr="Python (programmation informatique)",
            alt_labels_en=["Python3"],
        )
        user = Utilisateur.objects.create_user(
            username="recovery_resume",
            email="recovery_resume@example.com",
            password="pass1234",
        )
        resume = ProfileResume.objects.create(
            profile=user.profil,
            source_type=ProfileResume.SourceType.UPLOAD,
            parsed_text="Python backend engineer",
            resume_text_embedding_source="Python backend engineer",
            parsing_status=ProfileResume.ParsingStatus.SUCCEEDED,
            semantic_resume_status="PENDING",
            is_active=False,
        )
        mock_enrich_resume_text.return_value = ResumeSemanticSignals(
            skills=["python"],
            domains=[],
            tools=[],
            languages_detected=["en"],
            semantic_confidence=0.92,
            raw_candidates=[SkillCandidate(text="Python3", source="lexical", confidence=0.9)],
            mapped_candidates=[],
            warnings=[],
        )

        stats = run_backfill_for_target(TARGET_RESUMES, chunk_size=10)

        resume.refresh_from_db()
        self.assertEqual(stats.updated, 1)
        self.assertEqual(stats.matched_entities, 1)
        self.assertEqual(resume.semantic_resume_status, "SUCCEEDED")
        self.assertEqual(resume.extracted_raw_skills, ["Python3"])
        self.assertEqual(resume.extracted_normalized_skills[0]["esco_uri"], PYTHON_URI)

    @patch("users.resume_semantic.service.enrich_resume_text")
    def test_resume_candidate_cleanup_mode_reuses_stored_candidates_without_full_semantic_rerun(
        self,
        mock_enrich_resume_text,
    ):
        _create_official_skill(
            uri=PYTHON_URI,
            preferred_label="Python (computer programming)",
            preferred_label_en="Python (computer programming)",
            preferred_label_fr="Python (programmation informatique)",
            alt_labels_en=["Python3"],
        )
        user = Utilisateur.objects.create_user(
            username="resume_cleanup_user",
            email="resume_cleanup_user@example.com",
            password="pass1234",
        )
        resume = ProfileResume.objects.create(
            profile=user.profil,
            source_type=ProfileResume.SourceType.UPLOAD,
            parsed_text="Python backend engineer",
            resume_text_embedding_source="Python backend engineer",
            parsing_status=ProfileResume.ParsingStatus.SUCCEEDED,
            extracted_raw_skills=["Python3", "opportunités"],
            extracted_normalized_skills=[],
            semantic_resume_metadata={
                "raw_candidates": [
                    {"text": "Python3", "source": "stored", "confidence": 0.9},
                    {"text": "opportunités", "source": "stored", "confidence": 0.5},
                ]
            },
        )

        stats = run_backfill_for_target(
            TARGET_RESUMES,
            chunk_size=10,
            resume_mode="candidate_cleanup",
        )

        resume.refresh_from_db()
        mock_enrich_resume_text.assert_not_called()
        self.assertEqual(stats.updated, 1)
        self.assertEqual(resume.extracted_raw_skills, ["Python3"])
        self.assertEqual(resume.extracted_normalized_skills[0]["esco_uri"], PYTHON_URI)
        self.assertEqual(
            resume.semantic_resume_metadata["rejected_raw_candidates"][0]["reason"],
            "generic_business_term",
        )

    @patch("users.tasks.close_old_connections")
    @patch("users.tasks.enqueue_profile_embedding_refresh")
    @patch("users.tasks.process_profile_resume_semantics")
    @patch("users.tasks.parse_resume_file")
    def test_resume_parse_runs_semantics_even_for_inactive_resume(
        self,
        mock_parse_resume_file,
        mock_process_semantics,
        mock_enqueue_profile_embedding_refresh,
        _mock_close_old_connections,
    ):
        user = Utilisateur.objects.create_user(
            username="inactive_resume_user",
            email="inactive_resume_user@example.com",
            password="pass1234",
        )
        resume = ProfileResume.objects.create(
            profile=user.profil,
            source_type=ProfileResume.SourceType.UPLOAD,
            is_active=False,
        )
        mock_parse_resume_file.return_value = SimpleNamespace(
            text="Inactive resume with Python",
            parser="stub",
            truncated=False,
        )
        mock_process_semantics.return_value = {"status": "SUCCEEDED", "resume_id": resume.id}

        parse_profile_resume.run(resume.id)

        mock_process_semantics.assert_called_once()
        mock_enqueue_profile_embedding_refresh.assert_not_called()

    def test_report_command_emits_json_summary(self):
        out = StringIO()
        call_command("report_esco_normalization", "--target", "profiles", "--json", stdout=out)
        self.assertIn('"profiles"', out.getvalue())

    @patch("ai.management.commands.backfill_esco_normalization.backfill_esco_normalization")
    def test_backfill_command_forwards_resume_mode(self, mock_backfill):
        mock_backfill.return_value = {"resumes": {"updated": 1}}

        call_command(
            "backfill_esco_normalization",
            "--target",
            "resumes",
            "--resume-mode",
            "candidate_cleanup",
        )

        self.assertEqual(mock_backfill.call_args.kwargs["resume_mode"], "candidate_cleanup")

    def test_resume_report_surfaces_unmatched_and_rejected_candidate_reasons(self):
        user = Utilisateur.objects.create_user(
            username="resume_report_user",
            email="resume_report_user@example.com",
            password="pass1234",
        )
        ProfileResume.objects.create(
            profile=user.profil,
            source_type=ProfileResume.SourceType.UPLOAD,
            parsed_text="resume text",
            resume_text_embedding_source="resume text",
            parsing_status=ProfileResume.ParsingStatus.SUCCEEDED,
            extracted_raw_skills=["Drive"],
            extracted_normalized_skills=[
                {
                    "raw_skill": "Drive",
                    "canonical_skill": None,
                    "esco_uri": None,
                    "match_type": "unmatched",
                    "unmatched_reason": "query_too_short_for_semantic",
                }
            ],
            semantic_resume_metadata={
                "rejected_raw_candidates": [
                    {
                        "text": "et développer un portefeuille de clients",
                        "reason": "phrase_fragment",
                    }
                ]
            },
        )

        report = build_esco_normalization_report(target=TARGET_RESUMES, top_n=5)[TARGET_RESUMES]

        self.assertEqual(report["top_unmatched_reasons"][0]["label"], "query_too_short_for_semantic")
        self.assertEqual(report["top_rejected_candidate_reasons"][0]["label"], "phrase_fragment")
