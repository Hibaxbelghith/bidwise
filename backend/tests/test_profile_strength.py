from types import SimpleNamespace

from django.test import SimpleTestCase

from ai.profile_strength import compute_profile_strength, recommendation_mode_for_profile


class ProfileStrengthTests(SimpleTestCase):
    def test_empty_profile_is_low_strength(self):
        result = compute_profile_strength(SimpleNamespace(onboarding_completed=False), {})

        self.assertEqual(result["score"], 0)
        self.assertEqual(result["level"], "LOW")
        self.assertEqual(recommendation_mode_for_profile(result), "SPARSE_PROFILE")

    def test_python_only_profile_is_low_strength(self):
        result = compute_profile_strength(
            SimpleNamespace(onboarding_completed=False),
            {"skills": ["Python"]},
        )

        self.assertEqual(result["level"], "LOW")
        self.assertTrue(result["signals"]["skills"])
        self.assertFalse(result["signals"]["roles"])

    def test_complete_cv_backed_profile_is_high_strength(self):
        result = compute_profile_strength(
            SimpleNamespace(onboarding_completed=True),
            {
                "skills": ["Python", "Django", "PostgreSQL"],
                "target_roles": ["Backend Developer"],
                "resume_text": "Backend Django APIs Redis Celery",
                "interests": ["SAAS"],
                "locations": ["Tunis"],
                "work_modes": ["REMOTE"],
                "employment_types": ["FULL_TIME"],
                "experience_level": "JUNIOR",
                "experience_years": 2,
            },
        )

        self.assertEqual(result["level"], "HIGH")
        self.assertGreaterEqual(result["score"], 71)
        self.assertEqual(recommendation_mode_for_profile(result), "STANDARD")

    def test_medium_profile_has_stable_signals(self):
        result = compute_profile_strength(
            SimpleNamespace(onboarding_completed=False),
            {
                "skills": ["React", "JavaScript"],
                "target_roles": ["Frontend Developer"],
                "locations": ["Tunis"],
                "employment_types": ["FULL_TIME"],
            },
        )

        self.assertEqual(result["level"], "MEDIUM")
        self.assertTrue(result["signals"]["skills"])
        self.assertTrue(result["signals"]["roles"])
        self.assertTrue(result["signals"]["locations"])
