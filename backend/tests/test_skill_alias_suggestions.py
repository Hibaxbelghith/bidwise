from __future__ import annotations

from datetime import date
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from ai.esco_skill_index import clear_esco_skill_index_cache
from ai.skill_alias_suggestions import (
    TARGET_ALL,
    build_skill_alias_suggestions,
    summarize_skill_alias_suggestions,
)
from ai.models import ESCOSkill
from opportunities.models import Opportunite, SourceOpportunite, StatutOpportunite, TypeOpportunite
from users.models import ProfileResume, Utilisateur


DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
DEFAULT_VERSION = "prod-v1-fr"
DEFAULT_DIMENSIONS = 384


def _unit_vector(index: int) -> list[float]:
    vector = [0.0] * DEFAULT_DIMENSIONS
    vector[index] = 1.0
    return vector


def _embedded_skill(
    *,
    uri: str,
    preferred_label: str,
    preferred_label_en: str = "",
    preferred_label_fr: str = "",
    alt_labels_en: list[str] | None = None,
    alt_labels_fr: list[str] | None = None,
    embedding: list[float] | None = None,
) -> ESCOSkill:
    return ESCOSkill.objects.create(
        uri=uri,
        preferred_label=preferred_label,
        alt_labels=[],
        preferred_label_en=preferred_label_en,
        preferred_label_fr=preferred_label_fr,
        alt_labels_en=alt_labels_en or [],
        alt_labels_fr=alt_labels_fr or [],
        hidden_labels_en=[],
        hidden_labels_fr=[],
        search_text_multilingual="",
        embedding=embedding,
        embedding_model=DEFAULT_MODEL if embedding is not None else "",
        embedding_dimensions=DEFAULT_DIMENSIONS if embedding is not None else None,
        embedding_version=DEFAULT_VERSION if embedding is not None else "",
        embedding_updated_at=timezone.now() if embedding is not None else None,
    )


class SkillAliasSuggestionsTests(TestCase):
    def setUp(self):
        clear_esco_skill_index_cache()

    def tearDown(self):
        clear_esco_skill_index_cache()

    def test_build_skill_alias_suggestions_classifies_official_match_noise_and_semantic_candidate(self):
        _embedded_skill(
            uri="http://data.europa.eu/esco/skill/react",
            preferred_label="React",
            preferred_label_en="React",
            alt_labels_en=["ReactJS"],
            embedding=_unit_vector(0),
        )
        _embedded_skill(
            uri="http://data.europa.eu/esco/skill/nodejs",
            preferred_label="Node.js",
            preferred_label_en="Node.js",
            alt_labels_en=["NodeJS"],
            embedding=_unit_vector(1),
        )

        source = SourceOpportunite.objects.create(
            nom="AliasSource",
            url="https://example.com",
            type_source="SITE_EMPLOI",
        )
        Opportunite.objects.create(
            titre="Frontend role",
            description="React work",
            organisation_nom="BidWise",
            ville="Tunis",
            contract_type="CDI",
            skills=["ReactJS", "Node runtime", "opportunites"],
            raw_skills=["ReactJS", "Node runtime", "opportunites"],
            normalized_skills=[
                {"raw_skill": "ReactJS", "esco_uri": None, "match_type": "unmatched", "unmatched_reason": "legacy_uri_filtered"},
                {"raw_skill": "Node runtime", "esco_uri": None, "match_type": "unmatched", "unmatched_reason": "semantic_below_threshold"},
                {"raw_skill": "opportunites", "esco_uri": None, "match_type": "unmatched", "unmatched_reason": "generic_business_term"},
            ],
            type_opportunite=TypeOpportunite.EMPLOI,
            statut=StatutOpportunite.ACTIVE,
            date_publication=date(2026, 5, 15),
            source=source,
        )

        with patch("ai.skill_alias_suggestions.embedding_service.generate_embeddings_batch") as mock_embeddings:
            mock_embeddings.return_value = [_unit_vector(1)]
            suggestions = build_skill_alias_suggestions(
                target=TARGET_ALL,
                top_n=10,
                min_count=1,
                semantic_candidate_limit=3,
            )

        by_skill = {item.raw_skill: item for item in suggestions}
        self.assertEqual(by_skill["ReactJS"].recommended_action, "official_match")
        self.assertEqual(by_skill["ReactJS"].top_candidate_label, "React")
        self.assertEqual(by_skill["Node runtime"].recommended_action, "custom_alias_candidate")
        self.assertEqual(by_skill["Node runtime"].top_candidate_label, "Node.js")
        self.assertEqual(by_skill["opportunites"].recommended_action, "noise")
        self.assertEqual(by_skill["opportunites"].suggestion_method, "heuristic_noise_filter")
        mock_embeddings.assert_called_once()

    def test_resume_and_profile_unmatched_entries_are_aggregated_with_source_breakdown(self):
        user = Utilisateur.objects.create_user(
            username="alias_profile_user",
            email="alias_profile_user@example.com",
            password="pass1234",
        )
        profile = user.profil
        profile.normalized_skills = [
            {"raw_skill": "Excel", "esco_uri": None, "match_type": "unmatched", "unmatched_reason": "semantic_below_threshold"}
        ]
        profile.save(update_fields=["normalized_skills"])
        ProfileResume.objects.create(
            profile=profile,
            source_type=ProfileResume.SourceType.UPLOAD,
            parsed_text="Excel resume",
            resume_text_embedding_source="Excel resume",
            parsing_status=ProfileResume.ParsingStatus.SUCCEEDED,
            extracted_raw_skills=["Excel"],
            extracted_normalized_skills=[
                {"raw_skill": "Excel", "esco_uri": None, "match_type": "unmatched", "unmatched_reason": "semantic_below_threshold"}
            ],
        )

        suggestions = build_skill_alias_suggestions(target=TARGET_ALL, top_n=5, min_count=1)
        excel_row = next(item for item in suggestions if item.raw_skill == "Excel")

        self.assertEqual(excel_row.total_count, 2)
        self.assertEqual(excel_row.source_breakdown["profiles"], 1)
        self.assertEqual(excel_row.source_breakdown["resumes"], 1)

    def test_command_writes_csv_and_json_summary(self):
        user = Utilisateur.objects.create_user(
            username="alias_command_user",
            email="alias_command_user@example.com",
            password="pass1234",
        )
        user.profil.normalized_skills = [
            {"raw_skill": "Excel", "esco_uri": None, "match_type": "unmatched", "unmatched_reason": "semantic_below_threshold"}
        ]
        user.profil.save(update_fields=["normalized_skills"])

        with TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "alias_review.csv"
            stdout = StringIO()
            call_command(
                "suggest_skill_aliases",
                "--target",
                "profiles",
                "--top-n",
                "5",
                "--min-count",
                "1",
                "--output",
                str(output_path),
                "--json",
                stdout=stdout,
            )

            self.assertTrue(output_path.exists())
            content = output_path.read_text(encoding="utf-8")
            self.assertIn("raw_skill", content)
            self.assertIn("Excel", content)
            self.assertIn('"summary"', stdout.getvalue())

    def test_summary_counts_actions(self):
        suggestions = build_skill_alias_suggestions(target=TARGET_ALL, top_n=5, min_count=10)
        summary = summarize_skill_alias_suggestions(suggestions)

        self.assertEqual(summary["total_suggestions"], 0)
        self.assertEqual(summary["action_breakdown"], {})
