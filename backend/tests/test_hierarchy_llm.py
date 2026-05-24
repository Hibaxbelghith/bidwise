from django.test import SimpleTestCase

from ai.hierarchy_llm import (
    HIERARCHY_VALIDATION_SCHEMA,
    build_hierarchy_validation_prompt,
    normalize_llm_hierarchy_response,
    validate_hierarchy_with_llm,
)


class FakeLLMProvider:
    provider_name = "fake"
    model = "fake-model"

    def __init__(self, payload):
        self.payload = payload
        self.last_prompt = ""
        self.last_schema = None

    def generate_json(self, prompt, *, schema=None):
        self.last_prompt = prompt
        self.last_schema = schema
        return self.payload


class HierarchyLLMTests(SimpleTestCase):
    def test_build_prompt_is_limited_to_hierarchy_validation(self):
        prompt = build_hierarchy_validation_prompt(
            profile_text="Role: IT Helpdesk Officer. Experience: junior.",
            opportunity_title="IT Helpdesk Officer",
            opportunity_description="Support utilisateurs Windows et Microsoft 365.",
            opportunity_skills=["Windows", "Microsoft 365"],
            hierarchy_validation={"needs_llm": True, "seniority_gap": 1},
        )

        self.assertIn("compatibilite hierarchique", prompt)
        self.assertIn("JobBERT", prompt)
        self.assertIn("Role: IT Helpdesk Officer", prompt)
        self.assertIn("Titre: IT Helpdesk Officer", prompt)
        self.assertIn('"is_compatible"', prompt)
        self.assertIn('"issue"', prompt)
        self.assertIn('si "is_compatible" est true', prompt)

    def test_validate_hierarchy_with_llm_normalizes_response_and_metadata(self):
        provider = FakeLLMProvider(
            {
                "is_compatible": False,
                "confidence": 0.91,
                "issue": "seniority_gap",
                "reason": "Trop senior pour un profil junior.",
            }
        )

        result = validate_hierarchy_with_llm(
            profile_text="Role: Comptable. Experience: junior.",
            opportunity_id=1903,
            opportunity_title="Comptable Confirme",
            hierarchy_validation={"needs_llm": True, "seniority_gap": 1},
            provider=provider,
        )

        self.assertFalse(result.is_compatible)
        self.assertEqual(result.confidence, 0.91)
        self.assertEqual(result.issue, "seniority_gap")
        self.assertEqual(result.provider, "fake")
        self.assertEqual(result.model, "fake-model")
        self.assertTrue(result.cache_key)
        self.assertEqual(provider.last_schema, HIERARCHY_VALIDATION_SCHEMA)

    def test_normalize_response_clamps_confidence_and_unknown_issue(self):
        result = normalize_llm_hierarchy_response(
            {
                "is_compatible": True,
                "confidence": 1.7,
                "issue": "unexpected",
                "reason": " " * 20,
            }
        )

        self.assertFalse(result.is_compatible)
        self.assertEqual(result.confidence, 1.0)
        self.assertEqual(result.issue, "unclear")
        self.assertEqual(result.reason, "No explanation provided by LLM.")

    def test_normalize_response_marks_compatible_gap_as_unclear(self):
        result = normalize_llm_hierarchy_response(
            {
                "is_compatible": True,
                "confidence": 0.8,
                "issue": "seniority_gap",
                "reason": "Contradictory response.",
            }
        )

        self.assertFalse(result.is_compatible)
        self.assertEqual(result.issue, "unclear")
