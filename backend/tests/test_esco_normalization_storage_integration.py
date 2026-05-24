from datetime import date
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from ai.tasks import (
    normalize_opportunity_skills_storage,
    normalize_profile_skills_storage,
)
from ai.esco_skill_index import clear_esco_skill_index_cache
from ai.models import ESCOSkill
from opportunities.models import (
    Opportunite,
    RawOpportunite,
    RawOpportuniteProcessingStatus,
    SourceOpportunite,
    StatutOpportunite,
    TypeOpportunite,
)
from opportunities.processing import process_raw_opportunity
from users.models import Profil, ProfileResume, Utilisateur
from users.resume_semantic.models import ResumeSemanticSignals, SkillCandidate
from users.resume_semantic.service import process_profile_resume_semantics
from users.serializers import ProfilUpdateSerializer


PYTHON_URI = "http://data.europa.eu/esco/skill/python"
MARKETING_URI = "http://data.europa.eu/esco/skill/marketing-analysis"


def _create_official_skill(
    *,
    uri: str,
    preferred_label: str,
    preferred_label_en: str = "",
    preferred_label_fr: str = "",
    alt_labels_en: list[str] | None = None,
    alt_labels_fr: list[str] | None = None,
    hidden_labels_en: list[str] | None = None,
):
    return ESCOSkill.objects.create(
        uri=uri,
        preferred_label=preferred_label,
        alt_labels=[*(alt_labels_en or []), *(alt_labels_fr or [])],
        preferred_label_en=preferred_label_en,
        preferred_label_fr=preferred_label_fr,
        alt_labels_en=alt_labels_en or [],
        alt_labels_fr=alt_labels_fr or [],
        hidden_labels_en=hidden_labels_en or [],
        hidden_labels_fr=[],
        search_text_multilingual="",
    )


class ESCONormalizationStorageIntegrationTests(TestCase):
    def setUp(self):
        clear_esco_skill_index_cache()

    def tearDown(self):
        clear_esco_skill_index_cache()

    @patch("ai.tasks.enqueue_opportunity_skill_normalization")
    @patch("opportunities.processing.evaluate_opportunity")
    @patch("opportunities.processing.enrich_opportunity_text")
    @patch("opportunities.processing.normalize_raw_opportunity")
    def test_process_raw_opportunity_stores_raw_skills_and_schedules_normalization(
        self,
        mock_normalize_raw,
        mock_enrich,
        mock_evaluate,
        mock_enqueue,
    ):
        source = SourceOpportunite.objects.create(
            nom="LinkedIn",
            url="https://example.com",
            type_source="SITE_EMPLOI",
        )
        raw = RawOpportunite.objects.create(
            source=source,
            raw_payload={"skills": ["Python3", "Py3K"]},
            raw_titre="Backend Engineer",
            raw_description="Build APIs with Python",
            payload_hash="abc123",
            processing_status=RawOpportuniteProcessingStatus.NEW,
        )
        mock_normalize_raw.return_value = {
            "raw_id": raw.pk,
            "source": source,
            "titre": "Backend Engineer",
            "description": "Build APIs with Python and Django in Tunis.",
            "organisation_nom": "BidWise",
            "ville": "Tunis",
            "date_publication": date(2026, 5, 14),
            "type_opportunite": TypeOpportunite.EMPLOI,
            "statut": StatutOpportunite.ACTIVE,
            "source_item_url": "https://example.com/jobs/1",
            "skills": ["Python3", "Py3K"],
        }
        mock_enrich.return_value = {}
        mock_evaluate.side_effect = lambda payload: {**payload, "is_usable": True}

        with self.captureOnCommitCallbacks(execute=True):
            opportunity = process_raw_opportunity(raw)

        self.assertIsNotNone(opportunity)
        raw.refresh_from_db()
        opportunity.refresh_from_db()
        self.assertEqual(raw.processing_status, RawOpportuniteProcessingStatus.MATERIALIZED)
        self.assertEqual(opportunity.skills, ["Python3", "Py3K"])
        self.assertEqual(opportunity.raw_skills, ["Python3", "Py3K"])
        self.assertEqual(opportunity.normalized_skills, [])
        mock_enqueue.assert_called_once_with(opportunity.id)

    def test_normalize_opportunity_skills_storage_persists_official_matches_and_skips_fresh_runs(self):
        _create_official_skill(
            uri=PYTHON_URI,
            preferred_label="Python (computer programming)",
            preferred_label_en="Python (computer programming)",
            preferred_label_fr="Python (programmation informatique)",
            alt_labels_en=["Python3", "Py3K"],
            alt_labels_fr=["programmation python"],
        )
        opportunity = Opportunite.objects.create(
            titre="Backend Engineer",
            description="Build APIs",
            organisation_nom="BidWise",
            ville="Tunis",
            contract_type="CDI",
            salary="",
            skills=["Python3", "Py3K"],
            raw_skills=["Python3", "Py3K", "Python3"],
            type_opportunite=TypeOpportunite.EMPLOI,
            statut=StatutOpportunite.ACTIVE,
            date_publication=date(2026, 5, 14),
            source=SourceOpportunite.objects.create(
                nom="Keejob",
                url="https://example.com",
                type_source="SITE_EMPLOI",
            ),
        )

        result = normalize_opportunity_skills_storage.run(opportunity.id)

        opportunity.refresh_from_db()
        self.assertEqual(result["status"], "updated")
        self.assertEqual(opportunity.raw_skills, ["Python3", "Py3K"])
        self.assertEqual(len(opportunity.normalized_skills), 2)
        self.assertTrue(all(item["esco_uri"] == PYTHON_URI for item in opportunity.normalized_skills))
        self.assertEqual(opportunity.skills_normalization_error, "")
        self.assertIsNotNone(opportunity.skills_normalization_updated_at)

        with patch("ai.tasks.build_skill_normalization_payload") as mock_build_payload:
            second = normalize_opportunity_skills_storage.run(opportunity.id)
        self.assertEqual(second["status"], "skipped")
        self.assertEqual(second["reason"], "fresh")
        mock_build_payload.assert_not_called()

    @patch("users.serializers.enqueue_profile_skill_normalization")
    def test_profile_update_stores_raw_skills_and_task_persists_normalized_skills(self, mock_enqueue):
        _create_official_skill(
            uri=PYTHON_URI,
            preferred_label="Python (computer programming)",
            preferred_label_en="Python (computer programming)",
            preferred_label_fr="Python (programmation informatique)",
            alt_labels_en=["Python3"],
            alt_labels_fr=["programmation python"],
        )
        user = Utilisateur.objects.create_user(
            username="candidate1",
            email="candidate1@example.com",
            password="pass1234",
        )
        profile = user.profil

        serializer = ProfilUpdateSerializer(
            profile,
            data={"competences": ["Python3", "programmation python", "Python3"]},
            partial=True,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        with self.captureOnCommitCallbacks(execute=True):
            serializer.save()

        profile.refresh_from_db()
        self.assertEqual(profile.raw_skills, ["Python3", "programmation python"])
        self.assertEqual(profile.normalized_skills, [])
        mock_enqueue.assert_called_once_with(profile.id)

        task_result = normalize_profile_skills_storage.run(profile.id)
        profile.refresh_from_db()

        self.assertEqual(task_result["status"], "updated")
        self.assertEqual(len(profile.normalized_skills), 2)
        self.assertTrue(all(item["esco_uri"] == PYTHON_URI for item in profile.normalized_skills))
        self.assertEqual(profile.skills_normalization_error, "")

    @patch("users.serializers.enqueue_profile_skill_normalization")
    def test_profile_update_invalidates_stale_esco_payload_for_python_django_react(self, mock_enqueue):
        user = Utilisateur.objects.create_user(
            username="candidate-stack",
            email="candidate-stack@example.com",
            password="pass1234",
        )
        profile = user.profil
        profile.competences = ["Old skill"]
        profile.raw_skills = ["Old skill"]
        profile.normalized_skills = [
            {
                "raw_skill": "Old skill",
                "esco_uri": "http://data.europa.eu/esco/skill/old",
                "canonical_skill": "old skill",
                "match_type": "preferred_label",
            }
        ]
        profile.skills_normalization_hash = "stale-hash"
        profile.skills_normalization_updated_at = timezone.now()
        profile.skills_normalization_error = "stale error"
        profile.embedding = [0.1, 0.2, 0.3]
        profile.embedding_features_hash = "old-embedding"
        profile.embedding_model = "old-model"
        profile.embedding_dimensions = 3
        profile.embedding_updated_at = timezone.now()
        profile.embedding_content_hash = "old-content"
        profile.save()

        serializer = ProfilUpdateSerializer(
            profile,
            data={"competences": ["Python", "Django", "React", "Python"]},
            partial=True,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        with self.captureOnCommitCallbacks(execute=True):
            serializer.save()

        profile.refresh_from_db()
        self.assertEqual(profile.competences, ["Python", "Django", "React"])
        self.assertEqual(profile.raw_skills, ["Python", "Django", "React"])
        self.assertEqual(profile.normalized_skills, [])
        self.assertEqual(profile.skills_normalization_hash, "")
        self.assertIsNone(profile.skills_normalization_updated_at)
        self.assertEqual(profile.skills_normalization_error, "")
        self.assertIsNone(profile.embedding)
        self.assertEqual(profile.embedding_features_hash, "")
        self.assertEqual(profile.embedding_model, "")
        self.assertIsNone(profile.embedding_dimensions)
        self.assertIsNone(profile.embedding_updated_at)
        self.assertEqual(profile.embedding_content_hash, "")
        mock_enqueue.assert_called_once_with(profile.id)

    def test_profile_skill_normalization_failure_preserves_raw_skills(self):
        user = Utilisateur.objects.create_user(
            username="candidate2",
            email="candidate2@example.com",
            password="pass1234",
        )
        profile = user.profil
        profile.competences = ["Python3"]
        profile.raw_skills = ["Python3"]
        profile.save(update_fields=["competences", "raw_skills"])

        with patch("ai.tasks.build_skill_normalization_payload", side_effect=RuntimeError("boom")):
            result = normalize_profile_skills_storage.run(profile.id)

        profile.refresh_from_db()
        self.assertEqual(result["status"], "updated")
        self.assertEqual(profile.raw_skills, ["Python3"])
        self.assertEqual(profile.normalized_skills, [])
        self.assertIn("boom", profile.skills_normalization_error)
        self.assertIsNotNone(profile.skills_normalization_updated_at)

    @patch("users.resume_semantic.service.enrich_resume_text")
    def test_process_profile_resume_semantics_stores_raw_and_normalized_skills(self, mock_enrich_resume_text):
        _create_official_skill(
            uri=MARKETING_URI,
            preferred_label="marketing analysis",
            preferred_label_en="marketing analysis",
            preferred_label_fr="analyse marketing",
            alt_labels_fr=["marketing digital"],
        )
        user = Utilisateur.objects.create_user(
            username="candidate3",
            email="candidate3@example.com",
            password="pass1234",
        )
        resume = ProfileResume.objects.create(
            profile=user.profil,
            source_type=ProfileResume.SourceType.UPLOAD,
            parsed_text="Analyse marketing et études de marché",
            parsing_status=ProfileResume.ParsingStatus.SUCCEEDED,
            is_active=True,
        )
        mock_enrich_resume_text.return_value = ResumeSemanticSignals(
            skills=["marketing analysis"],
            domains=[],
            tools=[],
            languages_detected=["fr"],
            semantic_confidence=0.91,
            raw_candidates=[
                SkillCandidate(text="analyse marketing", source="lexical", confidence=0.9),
                SkillCandidate(text="marketing digital", source="lexical", confidence=0.9),
            ],
            mapped_candidates=[],
            warnings=[],
        )

        result = process_profile_resume_semantics(resume, force=True)

        resume.refresh_from_db()
        self.assertEqual(result["status"], "SUCCEEDED")
        self.assertEqual(resume.extracted_skills, ["marketing analysis"])
        self.assertEqual(
            resume.extracted_raw_skills,
            ["analyse marketing", "marketing digital"],
        )
        self.assertEqual(len(resume.extracted_normalized_skills), 2)
        self.assertTrue(all(item["esco_uri"] == MARKETING_URI for item in resume.extracted_normalized_skills))
        self.assertEqual(resume.extracted_skills_normalization_error, "")
        self.assertIsNotNone(resume.extracted_skills_normalization_updated_at)
