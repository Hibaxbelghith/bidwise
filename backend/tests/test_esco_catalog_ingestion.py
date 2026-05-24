from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.test import TestCase

from ai.esco_skill_index import clear_esco_skill_index_cache, get_esco_skill_index
from ai.models import ESCOOccupationCatalog, ESCOOccupationSkillRelation, ESCOSkill


def _write_csv(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8-sig", newline="")


class ESCOCatalogImportCommandTests(TestCase):
    def tearDown(self):
        clear_esco_skill_index_cache()

    def test_import_esco_catalog_merges_multilingual_rows_and_relations(self):
        with TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            _write_csv(
                base_dir / "skills_en.csv",
                (
                    "conceptType,conceptUri,skillType,reuseLevel,preferredLabel,altLabels,hiddenLabels,status,modifiedDate,scopeNote,definition,inScheme,description\n"
                    "KnowledgeSkillCompetence,http://data.europa.eu/esco/skill/skill-1,skill/competence,sector-specific,Python,\"python programming\nPy\",,released,2023-01-01,,,,\n"
                ),
            )
            _write_csv(
                base_dir / "skills_fr.csv",
                (
                    "conceptType,conceptUri,skillType,reuseLevel,preferredLabel,altLabels,hiddenLabels,status,modifiedDate,scopeNote,definition,inScheme,description\n"
                    "KnowledgeSkillCompetence,http://data.europa.eu/esco/skill/skill-1,skill/competence,sector-specific,Python,\"programmation python\",,\"released\",2023-01-01,,,,\n"
                ),
            )
            _write_csv(
                base_dir / "occupations_en.csv",
                (
                    "conceptType,conceptUri,iscoGroup,preferredLabel,altLabels,hiddenLabels,status,modifiedDate,regulatedProfessionNote,scopeNote,definition,inScheme,description,code,naceCode\n"
                    "Occupation,http://data.europa.eu/esco/occupation/occ-1,2512,Backend developer,\"API developer\",,released,2023-01-01,,,,,2512,62.01\n"
                ),
            )
            _write_csv(
                base_dir / "occupations_fr.csv",
                (
                    "conceptType,conceptUri,iscoGroup,preferredLabel,altLabels,hiddenLabels,status,modifiedDate,regulatedProfessionNote,scopeNote,definition,inScheme,description,code,naceCode\n"
                    "Occupation,http://data.europa.eu/esco/occupation/occ-1,2512,Développeur backend,\"développeur API\",,released,2023-01-01,,,,,2512,62.01\n"
                ),
            )
            _write_csv(
                base_dir / "occupationSkillRelations_en.csv",
                (
                    "occupationUri,occupationLabel,relationType,skillType,skillUri,skillLabel\n"
                    "http://data.europa.eu/esco/occupation/occ-1,Backend developer,essential,skill/competence,http://data.europa.eu/esco/skill/skill-1,Python\n"
                ),
            )
            _write_csv(
                base_dir / "occupationSkillRelations_fr.csv",
                (
                    "occupationUri,occupationLabel,relationType,skillType,skillUri,skillLabel\n"
                    "http://data.europa.eu/esco/occupation/occ-1,Développeur backend,essential,skill/competence,http://data.europa.eu/esco/skill/skill-1,Python\n"
                ),
            )
            _write_csv(base_dir / "skillsHierarchy_en.csv", "Level 0 URI,Level 0 preferred term\n")
            _write_csv(base_dir / "skillsHierarchy_fr.csv", "Level 0 URI,Level 0 preferred term\n")

            call_command("import_esco_catalog", base_dir=str(base_dir))

        skill = ESCOSkill.objects.get(uri="http://data.europa.eu/esco/skill/skill-1")
        occupation = ESCOOccupationCatalog.objects.get(uri="http://data.europa.eu/esco/occupation/occ-1")
        relation = ESCOOccupationSkillRelation.objects.get(occupation=occupation, skill=skill)

        self.assertEqual(skill.preferred_label_en, "Python")
        self.assertEqual(skill.preferred_label_fr, "Python")
        self.assertIn("python programming", skill.alt_labels_en)
        self.assertIn("programmation python", skill.alt_labels_fr)
        self.assertIn("programmation python", skill.search_text_multilingual)
        self.assertEqual(skill.preferred_label, "Python")
        self.assertEqual(occupation.preferred_label_en, "Backend developer")
        self.assertEqual(occupation.preferred_label_fr, "Développeur backend")
        self.assertEqual(relation.relation_type, "essential")

    def test_import_esco_catalog_is_idempotent(self):
        with TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            _write_csv(
                base_dir / "skills_en.csv",
                (
                    "conceptType,conceptUri,skillType,reuseLevel,preferredLabel,altLabels,hiddenLabels,status,modifiedDate,scopeNote,definition,inScheme,description\n"
                    "KnowledgeSkillCompetence,http://data.europa.eu/esco/skill/skill-1,skill/competence,sector-specific,Python,,,released,2023-01-01,,,,\n"
                ),
            )
            _write_csv(base_dir / "skills_fr.csv", "conceptType,conceptUri,skillType,reuseLevel,preferredLabel,altLabels,hiddenLabels,status,modifiedDate,scopeNote,definition,inScheme,description\n")
            _write_csv(
                base_dir / "occupations_en.csv",
                (
                    "conceptType,conceptUri,iscoGroup,preferredLabel,altLabels,hiddenLabels,status,modifiedDate,regulatedProfessionNote,scopeNote,definition,inScheme,description,code,naceCode\n"
                    "Occupation,http://data.europa.eu/esco/occupation/occ-1,2512,Backend developer,,,released,2023-01-01,,,,,2512,62.01\n"
                ),
            )
            _write_csv(base_dir / "occupations_fr.csv", "conceptType,conceptUri,iscoGroup,preferredLabel,altLabels,hiddenLabels,status,modifiedDate,regulatedProfessionNote,scopeNote,definition,inScheme,description,code,naceCode\n")
            _write_csv(
                base_dir / "occupationSkillRelations_en.csv",
                (
                    "occupationUri,occupationLabel,relationType,skillType,skillUri,skillLabel\n"
                    "http://data.europa.eu/esco/occupation/occ-1,Backend developer,essential,skill/competence,http://data.europa.eu/esco/skill/skill-1,Python\n"
                ),
            )
            _write_csv(base_dir / "occupationSkillRelations_fr.csv", "occupationUri,occupationLabel,relationType,skillType,skillUri,skillLabel\n")
            _write_csv(base_dir / "skillsHierarchy_en.csv", "Level 0 URI,Level 0 preferred term\n")
            _write_csv(base_dir / "skillsHierarchy_fr.csv", "Level 0 URI,Level 0 preferred term\n")

            call_command("import_esco_catalog", base_dir=str(base_dir))
            call_command("import_esco_catalog", base_dir=str(base_dir))

        self.assertEqual(ESCOSkill.objects.filter(uri="http://data.europa.eu/esco/skill/skill-1").count(), 1)
        self.assertEqual(ESCOOccupationCatalog.objects.filter(uri="http://data.europa.eu/esco/occupation/occ-1").count(), 1)
        self.assertEqual(ESCOOccupationSkillRelation.objects.count(), 1)

    def test_import_esco_catalog_preserves_cached_lookup_behavior(self):
        with TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            _write_csv(
                base_dir / "skills_en.csv",
                (
                    "conceptType,conceptUri,skillType,reuseLevel,preferredLabel,altLabels,hiddenLabels,status,modifiedDate,scopeNote,definition,inScheme,description\n"
                    "KnowledgeSkillCompetence,http://data.europa.eu/esco/skill/skill-1,skill/competence,sector-specific,Python,\"python programming\",,released,2023-01-01,,,,\n"
                ),
            )
            _write_csv(base_dir / "skills_fr.csv", "conceptType,conceptUri,skillType,reuseLevel,preferredLabel,altLabels,hiddenLabels,status,modifiedDate,scopeNote,definition,inScheme,description\n")
            _write_csv(base_dir / "occupations_en.csv", "conceptType,conceptUri,iscoGroup,preferredLabel,altLabels,hiddenLabels,status,modifiedDate,regulatedProfessionNote,scopeNote,definition,inScheme,description,code,naceCode\n")
            _write_csv(base_dir / "occupations_fr.csv", "conceptType,conceptUri,iscoGroup,preferredLabel,altLabels,hiddenLabels,status,modifiedDate,regulatedProfessionNote,scopeNote,definition,inScheme,description,code,naceCode\n")
            _write_csv(base_dir / "occupationSkillRelations_en.csv", "occupationUri,occupationLabel,relationType,skillType,skillUri,skillLabel\n")
            _write_csv(base_dir / "occupationSkillRelations_fr.csv", "occupationUri,occupationLabel,relationType,skillType,skillUri,skillLabel\n")
            _write_csv(base_dir / "skillsHierarchy_en.csv", "Level 0 URI,Level 0 preferred term\n")
            _write_csv(base_dir / "skillsHierarchy_fr.csv", "Level 0 URI,Level 0 preferred term\n")

            call_command("import_esco_catalog", base_dir=str(base_dir))

        index = get_esco_skill_index()
        skill = index.by_uri["http://data.europa.eu/esco/skill/skill-1"]
        self.assertEqual(skill.preferred_label, "Python")
        self.assertIn("python programming", skill.alt_labels)
