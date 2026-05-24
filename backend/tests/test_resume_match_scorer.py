from __future__ import annotations

from types import SimpleNamespace

from django.test import TestCase

from resume_match.scorer import analyze_resume_skill_match
from users.models import ProfileResume, Utilisateur


PYTHON_URI = "http://data.europa.eu/esco/skill/python"
DJANGO_URI = "http://data.europa.eu/esco/skill/django"
REDIS_URI = "http://data.europa.eu/esco/skill/redis"
JAVASCRIPT_URI = "http://data.europa.eu/esco/skill/javascript"


def _normalized_skill(uri: str, raw_skill: str, canonical_skill: str, *, match_type: str = "preferred_label") -> dict[str, object]:
    return {
        "raw_skill": raw_skill,
        "canonical_skill": canonical_skill,
        "canonical_skill_en": canonical_skill,
        "canonical_skill_fr": "",
        "esco_uri": uri,
        "match_type": match_type,
        "similarity": 1.0 if match_type != "semantic" else 0.82,
        "embedding_model": None,
        "embedding_version": None,
        "embedding_dimensions": None,
        "language": "en",
        "matched_label": raw_skill,
    }


class ResumeSkillMatchScorerTests(TestCase):
    def setUp(self):
        self.user = Utilisateur.objects.create_user(
            username="resume_match_candidate",
            email="resume_match_candidate@example.com",
            password="pass1234",
        )
        self.profile = self.user.profil

    def test_overlap_normal(self):
        ProfileResume.objects.create(
            profile=self.profile,
            source_type=ProfileResume.SourceType.UPLOAD,
            parsing_status=ProfileResume.ParsingStatus.SUCCEEDED,
            is_active=True,
            extracted_normalized_skills=[
                _normalized_skill(PYTHON_URI, "Python", "Python"),
                _normalized_skill(DJANGO_URI, "Django", "Django"),
            ],
        )
        opportunity = SimpleNamespace(
            normalized_skills=[
                _normalized_skill(PYTHON_URI, "Python", "Python"),
                _normalized_skill(REDIS_URI, "Redis", "Redis"),
            ]
        )

        result = analyze_resume_skill_match(self.profile, opportunity)

        self.assertEqual(result["match_score"], 50)
        self.assertEqual(result["matched_skills"], ["Python"])
        self.assertEqual(result["missing_skills"], ["Redis"])

    def test_no_active_resume(self):
        ProfileResume.objects.create(
            profile=self.profile,
            source_type=ProfileResume.SourceType.UPLOAD,
            parsing_status=ProfileResume.ParsingStatus.SUCCEEDED,
            is_active=False,
            extracted_normalized_skills=[
                _normalized_skill(PYTHON_URI, "Python", "Python"),
            ],
        )
        opportunity = SimpleNamespace(
            normalized_skills=[
                _normalized_skill(PYTHON_URI, "Python", "Python"),
                _normalized_skill(REDIS_URI, "Redis", "Redis"),
            ]
        )

        result = analyze_resume_skill_match(self.profile, opportunity)

        self.assertEqual(result["match_score"], 0)
        self.assertEqual(result["matched_skills"], [])
        self.assertEqual(result["missing_skills"], ["Python", "Redis"])

    def test_no_opportunity_skills(self):
        ProfileResume.objects.create(
            profile=self.profile,
            source_type=ProfileResume.SourceType.UPLOAD,
            parsing_status=ProfileResume.ParsingStatus.SUCCEEDED,
            is_active=True,
            extracted_normalized_skills=[
                _normalized_skill(PYTHON_URI, "Python", "Python"),
            ],
        )
        opportunity = SimpleNamespace(normalized_skills=[])

        result = analyze_resume_skill_match(self.profile, opportunity)

        self.assertEqual(
            result,
            {
                "match_score": 0,
                "matched_skills": [],
                "missing_skills": [],
            },
        )

    def test_canonical_skills_matching_uses_shared_esco_uri(self):
        ProfileResume.objects.create(
            profile=self.profile,
            source_type=ProfileResume.SourceType.UPLOAD,
            parsing_status=ProfileResume.ParsingStatus.SUCCEEDED,
            is_active=True,
            extracted_normalized_skills=[
                _normalized_skill(JAVASCRIPT_URI, "JS", "JavaScript", match_type="alt_label"),
            ],
        )
        opportunity = SimpleNamespace(
            normalized_skills=[
                _normalized_skill(JAVASCRIPT_URI, "JavaScript", "JavaScript", match_type="preferred_label"),
            ]
        )

        result = analyze_resume_skill_match(self.profile, opportunity)

        self.assertEqual(result["match_score"], 100)
        self.assertEqual(result["matched_skills"], ["JavaScript"])
        self.assertEqual(result["missing_skills"], [])
