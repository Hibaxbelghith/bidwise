from django.test import SimpleTestCase

from ai.hierarchy import (
    build_profile_hierarchy_signal,
    extract_hierarchy_signal,
    validate_hierarchy_match,
)


class HierarchyValidationTests(SimpleTestCase):
    def test_junior_profile_is_penalized_against_senior_opportunity(self):
        profile = build_profile_hierarchy_signal(
            {
                "target_roles": ["Frontend Developer"],
                "skills": ["React", "TypeScript"],
                "experience_level": "JUNIOR",
            }
        )
        opportunity = extract_hierarchy_signal("Senior React Developer 5+ years")

        validation = validate_hierarchy_match(profile, opportunity)

        self.assertEqual(validation.hierarchy_issue, "seniority_gap")
        self.assertLess(validation.score_multiplier, 0.75)
        self.assertFalse(validation.needs_llm)

    def test_engineer_profile_to_technician_opportunity_is_reviewable_scope(self):
        profile = build_profile_hierarchy_signal(
            {
                "target_roles": ["Ingenieur genie civil travaux"],
                "education_level": "Bac+5",
                "experience_level": "JUNIOR",
            }
        )
        opportunity = extract_hierarchy_signal("Technicien superieur en genie civil")

        validation = validate_hierarchy_match(profile, opportunity)

        self.assertEqual(validation.hierarchy_issue, "overqualified_scope")
        self.assertLess(validation.score_multiplier, 1.0)

    def test_same_level_accountant_is_compatible(self):
        profile = build_profile_hierarchy_signal(
            {
                "target_roles": ["Comptable"],
                "skills": ["comptabilite", "audit"],
                "experience_level": "JUNIOR",
            }
        )
        opportunity = extract_hierarchy_signal("Comptable Junior")

        validation = validate_hierarchy_match(profile, opportunity)

        self.assertEqual(validation.hierarchy_issue, "none")
        self.assertEqual(validation.score_multiplier, 1.0)

    def test_zero_years_overrides_default_mid_level(self):
        signal = extract_hierarchy_signal("Assistant Comptable", years=0)

        self.assertEqual(signal.seniority, 0)
        self.assertEqual(signal.seniority_terms, ("0 years",))

    def test_small_qualification_gap_alone_does_not_require_llm(self):
        profile = build_profile_hierarchy_signal(
            {
                "target_roles": ["Comptable"],
                "education_level": "Bac+3",
                "experience_level": "JUNIOR",
            }
        )
        opportunity = extract_hierarchy_signal(
            "Comptable Junior",
            experience_level="JUNIOR",
            education_level="Bac+5",
        )

        validation = validate_hierarchy_match(profile, opportunity)

        self.assertEqual(validation.hierarchy_issue, "none")
        self.assertEqual(validation.score_multiplier, 1.0)
        self.assertFalse(validation.needs_llm)

    def test_default_opportunity_seniority_without_terms_does_not_require_llm(self):
        profile = build_profile_hierarchy_signal(
            {
                "target_roles": ["Comptable"],
                "experience_level": "JUNIOR",
            }
        )
        opportunity = extract_hierarchy_signal("Comptable General")

        validation = validate_hierarchy_match(profile, opportunity)

        self.assertEqual(validation.hierarchy_issue, "none")
        self.assertFalse(validation.needs_llm)
