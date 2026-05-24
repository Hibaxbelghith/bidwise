from __future__ import annotations

from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from ai.esco_skill_index import clear_esco_skill_index_cache
from ai.esco_skill_normalization import normalize_skills_to_esco
from ai.models import BidWiseSkillAlias, ESCOSkill


DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
DEFAULT_VERSION = "prod-v1-fr"
DEFAULT_DIMENSIONS = 384


def _embedded_skill(
    *,
    uri: str,
    preferred_label: str,
    preferred_label_en: str = "",
) -> ESCOSkill:
    return ESCOSkill.objects.create(
        uri=uri,
        preferred_label=preferred_label,
        alt_labels=[],
        preferred_label_en=preferred_label_en,
        preferred_label_fr="",
        alt_labels_en=[],
        alt_labels_fr=[],
        hidden_labels_en=[],
        hidden_labels_fr=[],
        search_text_multilingual="",
        embedding=None,
        embedding_model="",
        embedding_dimensions=None,
        embedding_version="",
        embedding_updated_at=None,
    )


class BidWiseSkillAliasTests(TestCase):
    def setUp(self):
        clear_esco_skill_index_cache()

    def tearDown(self):
        clear_esco_skill_index_cache()

    def test_normalize_skills_to_esco_matches_active_custom_alias_before_semantic(self):
        react = _embedded_skill(
            uri="http://data.europa.eu/esco/skill/react",
            preferred_label="React",
            preferred_label_en="React",
        )
        BidWiseSkillAlias.objects.create(
            alias="React Native",
            normalized_key="react native",
            language="en",
            target_skill=react,
            source="manual_review",
            status=BidWiseSkillAlias.Status.ACTIVE,
            notes="Approved local alias",
        )

        result = normalize_skills_to_esco(["React Native"])[0]

        self.assertEqual(result.esco_uri, react.uri)
        self.assertEqual(result.match_type, "custom_alias")
        self.assertEqual(result.language, "en")

    def test_disabled_custom_alias_is_ignored(self):
        react = _embedded_skill(
            uri="http://data.europa.eu/esco/skill/react",
            preferred_label="React",
            preferred_label_en="React",
        )
        BidWiseSkillAlias.objects.create(
            alias="React Native",
            normalized_key="react native",
            language="en",
            target_skill=react,
            source="manual_review",
            status=BidWiseSkillAlias.Status.DISABLED,
        )

        result = normalize_skills_to_esco(["React Native"])[0]

        self.assertIsNone(result.esco_uri)
        self.assertEqual(result.match_type, "unmatched")

    def test_load_bidwise_skill_aliases_command_creates_and_updates_rows(self):
        react = _embedded_skill(
            uri="http://data.europa.eu/esco/skill/react",
            preferred_label="React",
            preferred_label_en="React",
        )

        with TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "aliases.csv"
            csv_path.write_text(
                "alias,target_esco_uri,language,source,status,notes\n"
                f"React Native,{react.uri},en,seed,ACTIVE,First import\n",
                encoding="utf-8",
            )

            stdout = StringIO()
            call_command("load_bidwise_skill_aliases", str(csv_path), stdout=stdout)
            self.assertIn("creates=1", stdout.getvalue())

            alias = BidWiseSkillAlias.objects.get(alias="React Native")
            self.assertEqual(alias.target_skill_id, react.id)
            self.assertEqual(alias.status, BidWiseSkillAlias.Status.ACTIVE)
            self.assertEqual(alias.notes, "First import")

            csv_path.write_text(
                "alias,target_esco_uri,language,source,status,notes\n"
                f"React Native,{react.uri},fr,review,REVIEW,Updated import\n",
                encoding="utf-8",
            )
            stdout = StringIO()
            call_command("load_bidwise_skill_aliases", str(csv_path), stdout=stdout)
            self.assertIn("updates=1", stdout.getvalue())

            alias.refresh_from_db()
            self.assertEqual(alias.language, "fr")
            self.assertEqual(alias.source, "review")
            self.assertEqual(alias.status, BidWiseSkillAlias.Status.REVIEW)
            self.assertEqual(alias.notes, "Updated import")

