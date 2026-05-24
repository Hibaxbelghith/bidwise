from datetime import date
from types import SimpleNamespace

from django.test import SimpleTestCase, override_settings

from ai.recommendation_service import rank_opportunities
from ai.user_features import build_user_features


def _normalized_skill(uri, raw_skill, canonical_skill, *, match_type="alt_label", language="en"):
    return {
        "raw_skill": raw_skill,
        "canonical_skill": canonical_skill,
        "canonical_skill_en": canonical_skill,
        "canonical_skill_fr": None,
        "esco_uri": uri,
        "match_type": match_type,
        "similarity": 1.0 if match_type != "semantic" else 0.82,
        "embedding_model": None if match_type != "semantic" else "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        "embedding_version": None if match_type != "semantic" else "prod-v1-fr",
        "embedding_dimensions": None if match_type != "semantic" else 384,
        "language": language,
        "matched_label": raw_skill,
    }


def _vector_with_similarity(similarity):
    return [float(similarity), max(0.0, 1.0 - float(similarity) ** 2) ** 0.5]


class _FakeResumeQuerySet:
    def __init__(self, resumes):
        self.resumes = resumes

    def only(self, *fields):
        return self

    def first(self):
        return self.resumes[0] if self.resumes else None


class _FakeResumeManager:
    def __init__(self, resumes):
        self.resumes = resumes

    def filter(self, **kwargs):
        filtered = self.resumes
        for key, expected in kwargs.items():
            filtered = [resume for resume in filtered if getattr(resume, key, None) == expected]
        return _FakeResumeQuerySet(filtered)


class UserFeatureNormalizedSkillTests(SimpleTestCase):
    def test_build_user_features_exposes_normalized_skill_payloads(self):
        profile = SimpleNamespace(
            competences=["ReactJS"],
            normalized_skills=[
                _normalized_skill(
                    "http://data.europa.eu/esco/skill/react",
                    "ReactJS",
                    "React",
                )
            ],
            resumes=_FakeResumeManager(
                [
                    SimpleNamespace(
                        is_active=True,
                        parsed_text="",
                        semantic_resume_status="SUCCEEDED",
                        semantic_resume_confidence=0.91,
                        extracted_skills=["JavaScript"],
                        extracted_normalized_skills=[
                            _normalized_skill(
                                "http://data.europa.eu/esco/skill/javascript",
                                "JS",
                                "JavaScript",
                            )
                        ],
                        extracted_domains=[],
                        extracted_tools=[],
                        extracted_languages=[],
                    )
                ]
            ),
        )

        features = build_user_features(profile)

        self.assertEqual(len(features["normalized_profile_skills"]), 1)
        self.assertEqual(len(features["normalized_resume_skills"]), 1)
        self.assertEqual(len(features["normalized_skills"]), 2)


class RecommendationNormalizedSkillBonusTests(SimpleTestCase):
    databases = {"default"}

    def test_reactjs_profile_gets_small_bonus_for_react_opportunity(self):
        features = {
            "skills": ["ReactJS"],
            "normalized_skills": [
                _normalized_skill(
                    "http://data.europa.eu/esco/skill/react",
                    "ReactJS",
                    "React",
                )
            ],
        }
        baseline = SimpleNamespace(
            id=1,
            titre="Frontend Developer",
            skills=["React"],
            normalized_skills=[],
            embedding_vector=_vector_with_similarity(0.62),
            date_publication=date(2026, 1, 1),
        )
        enriched = SimpleNamespace(
            id=2,
            titre="Frontend Developer",
            skills=["React"],
            normalized_skills=[
                _normalized_skill(
                    "http://data.europa.eu/esco/skill/react",
                    "React",
                    "React",
                    match_type="preferred_label",
                )
            ],
            embedding_vector=_vector_with_similarity(0.62),
            date_publication=date(2026, 1, 1),
        )

        baseline_ranked = rank_opportunities([1.0, 0.0], [baseline], features=features)[0]
        enriched_ranked = rank_opportunities([1.0, 0.0], [enriched], features=features)[0]

        self.assertAlmostEqual(baseline_ranked.business_score, 0.0, places=4)
        self.assertAlmostEqual(enriched_ranked.business_score, 0.01, places=4)
        self.assertGreater(enriched_ranked.match_score, baseline_ranked.match_score)
        self.assertEqual(enriched_ranked.recommendation_debug["normalized_skill_novel_overlap_count"], 1)
        self.assertEqual(enriched_ranked.recommendation_debug["raw_skill_match_count"], 0)

    def test_js_profile_gets_small_bonus_for_javascript_opportunity(self):
        features = {
            "skills": ["JS"],
            "normalized_skills": [
                _normalized_skill(
                    "http://data.europa.eu/esco/skill/javascript",
                    "JS",
                    "JavaScript",
                )
            ],
        }
        opportunity = SimpleNamespace(
            id=1,
            titre="Frontend Engineer",
            skills=["JavaScript"],
            normalized_skills=[
                _normalized_skill(
                    "http://data.europa.eu/esco/skill/javascript",
                    "JavaScript",
                    "JavaScript",
                    match_type="preferred_label",
                )
            ],
            embedding_vector=_vector_with_similarity(0.61),
            date_publication=date(2026, 1, 1),
        )

        ranked = rank_opportunities([1.0, 0.0], [opportunity], features=features)[0]

        self.assertAlmostEqual(ranked.business_score, 0.01, places=4)
        self.assertEqual(ranked.recommendation_debug["normalized_skill_overlap_labels"], ["JavaScript"])

    def test_python3_profile_gets_small_bonus_for_python_opportunity(self):
        features = {
            "skills": ["Python3"],
            "normalized_skills": [
                _normalized_skill(
                    "http://data.europa.eu/esco/skill/python",
                    "Python3",
                    "Python",
                )
            ],
        }
        baseline = SimpleNamespace(
            id=1,
            titre="Backend Engineer",
            skills=["Python"],
            normalized_skills=[],
            embedding_vector=_vector_with_similarity(0.61),
            date_publication=date(2026, 1, 1),
        )
        enriched = SimpleNamespace(
            id=1,
            titre="Backend Engineer",
            skills=["Python"],
            normalized_skills=[
                _normalized_skill(
                    "http://data.europa.eu/esco/skill/python",
                    "Python",
                    "Python",
                    match_type="preferred_label",
                )
            ],
            embedding_vector=_vector_with_similarity(0.61),
            date_publication=date(2026, 1, 1),
        )

        baseline_ranked = rank_opportunities([1.0, 0.0], [baseline], features=features)[0]
        enriched_ranked = rank_opportunities([1.0, 0.0], [enriched], features=features)[0]

        self.assertAlmostEqual(enriched_ranked.business_score, 0.01, places=4)
        self.assertGreater(enriched_ranked.match_score, baseline_ranked.match_score)

    def test_seo_profile_does_not_boost_react_opportunity(self):
        features = {
            "skills": ["SEO"],
            "normalized_skills": [
                _normalized_skill(
                    "http://data.europa.eu/esco/skill/seo",
                    "SEO",
                    "Search engine optimisation",
                )
            ],
        }
        opportunity = SimpleNamespace(
            id=1,
            titre="React Developer",
            skills=["React"],
            normalized_skills=[
                _normalized_skill(
                    "http://data.europa.eu/esco/skill/react",
                    "React",
                    "React",
                    match_type="preferred_label",
                )
            ],
            embedding_vector=_vector_with_similarity(0.72),
            date_publication=date(2026, 1, 1),
        )

        ranked = rank_opportunities([1.0, 0.0], [opportunity], features=features)[0]

        self.assertAlmostEqual(ranked.business_score, 0.0, places=4)
        self.assertEqual(ranked.recommendation_debug["normalized_skill_overlap_count"], 0)

    def test_marketing_profile_does_not_boost_ml_opportunity(self):
        features = {
            "skills": ["Marketing Digital"],
            "normalized_skills": [
                _normalized_skill(
                    "http://data.europa.eu/esco/skill/digital_marketing",
                    "Marketing Digital",
                    "Digital marketing",
                )
            ],
        }
        opportunity = SimpleNamespace(
            id=1,
            titre="ML Engineer",
            skills=["Machine learning"],
            normalized_skills=[
                _normalized_skill(
                    "http://data.europa.eu/esco/skill/machine_learning",
                    "Machine learning",
                    "Machine learning",
                    match_type="preferred_label",
                )
            ],
            embedding_vector=_vector_with_similarity(0.70),
            date_publication=date(2026, 1, 1),
        )

        ranked = rank_opportunities([1.0, 0.0], [opportunity], features=features)[0]

        self.assertAlmostEqual(ranked.business_score, 0.0, places=4)
        self.assertEqual(ranked.recommendation_debug["normalized_skill_bonus"], 0.0)

    def test_existing_raw_skill_overlap_is_not_double_counted(self):
        features = {
            "skills": ["Python"],
            "normalized_skills": [
                _normalized_skill(
                    "http://data.europa.eu/esco/skill/python",
                    "Python",
                    "Python",
                    match_type="preferred_label",
                )
            ],
        }
        opportunity = SimpleNamespace(
            id=1,
            titre="Backend Developer",
            skills=["Python"],
            normalized_skills=[
                _normalized_skill(
                    "http://data.europa.eu/esco/skill/python",
                    "Python",
                    "Python",
                    match_type="preferred_label",
                )
            ],
            embedding_vector=_vector_with_similarity(0.40),
            date_publication=date(2026, 1, 1),
        )

        ranked = rank_opportunities([1.0, 0.0], [opportunity], features=features)[0]

        self.assertAlmostEqual(ranked.business_score, 0.025, places=4)
        self.assertEqual(ranked.recommendation_debug["normalized_skill_bonus"], 0.0)
        self.assertEqual(ranked.recommendation_debug["normalized_skill_raw_equivalent_overlap_count"], 1)

    @override_settings(RECOMMENDATION_ENABLE_NORMALIZED_SKILL_BONUS=False)
    def test_normalized_skill_bonus_is_easy_to_disable(self):
        features = {
            "skills": ["ReactJS"],
            "normalized_skills": [
                _normalized_skill(
                    "http://data.europa.eu/esco/skill/react",
                    "ReactJS",
                    "React",
                )
            ],
        }
        opportunity = SimpleNamespace(
            id=1,
            titre="Frontend Developer",
            skills=["React"],
            normalized_skills=[
                _normalized_skill(
                    "http://data.europa.eu/esco/skill/react",
                    "React",
                    "React",
                    match_type="preferred_label",
                )
            ],
            embedding_vector=_vector_with_similarity(0.62),
            date_publication=date(2026, 1, 1),
        )

        ranked = rank_opportunities([1.0, 0.0], [opportunity], features=features)[0]

        self.assertAlmostEqual(ranked.business_score, 0.0, places=4)
        self.assertEqual(ranked.recommendation_debug["normalized_skill_overlap_count"], 1)
        self.assertEqual(ranked.recommendation_debug["normalized_skill_bonus"], 0.0)
