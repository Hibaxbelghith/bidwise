from django.test import SimpleTestCase

from ai.llm.providers import LLMProviderError
from opportunities.moderation_llm import (
    CATEGORY_ADVERTISEMENT,
    CATEGORY_LEGITIMATE,
    CATEGORY_SCAM,
    CATEGORY_UNCLEAR,
    DECISION_APPROVED,
    DECISION_PENDING_REVIEW,
    DECISION_REJECTED,
    classify_opportunity_with_gemini,
    compact_moderation_payload,
)


class FakeProvider:
    provider_name = "gemini"
    model = "gemini-test"

    def __init__(self, response=None, error=None):
        self.response = response or {}
        self.error = error
        self.prompt = ""
        self.schema = None

    def generate_json(self, prompt, *, schema=None):
        self.prompt = prompt
        self.schema = schema
        if self.error:
            raise self.error
        return self.response


def opportunity_payload(**overrides):
    payload = {
        "type": "EMPLOI",
        "title": "Python Developer",
        "description": "Python backend role in Tunis with Django APIs and PostgreSQL.",
        "contract": "CDI",
        "location": "Tunis",
        "skills": ["Python", "Django"],
    }
    payload.update(overrides)
    return payload


class ModerationLLMTests(SimpleTestCase):
    def test_legitimate_high_confidence_auto_approves(self):
        provider = FakeProvider(
            {
                "category": CATEGORY_LEGITIMATE,
                "decision": DECISION_APPROVED,
                "confidence": 0.9,
                "reason": "The offer describes a real professional role.",
            }
        )

        result = classify_opportunity_with_gemini(opportunity_payload(), provider=provider)

        self.assertFalse(result.skipped)
        self.assertEqual(result.category, CATEGORY_LEGITIMATE)
        self.assertEqual(result.decision, DECISION_APPROVED)
        self.assertEqual(result.provider, "gemini")
        self.assertEqual(result.model, "gemini-test")

    def test_legitimate_low_confidence_stays_pending(self):
        provider = FakeProvider(
            {
                "category": CATEGORY_LEGITIMATE,
                "decision": DECISION_APPROVED,
                "confidence": 0.7,
                "reason": "The offer is probably legitimate but lacks enough clarity.",
            }
        )

        result = classify_opportunity_with_gemini(opportunity_payload(), provider=provider)

        self.assertEqual(result.decision, DECISION_PENDING_REVIEW)

    def test_scam_high_confidence_is_rejected_decision(self):
        provider = FakeProvider(
            {
                "category": CATEGORY_SCAM,
                "decision": DECISION_REJECTED,
                "confidence": 0.95,
                "reason": "The candidate is asked to pay a fee before starting.",
            }
        )

        result = classify_opportunity_with_gemini(opportunity_payload(), provider=provider)

        self.assertEqual(result.category, CATEGORY_SCAM)
        self.assertEqual(result.decision, DECISION_REJECTED)

    def test_scam_low_confidence_stays_pending(self):
        provider = FakeProvider(
            {
                "category": CATEGORY_SCAM,
                "decision": DECISION_REJECTED,
                "confidence": 0.7,
                "reason": "There may be a scam signal but it is not explicit enough.",
            }
        )

        result = classify_opportunity_with_gemini(opportunity_payload(), provider=provider)

        self.assertEqual(result.decision, DECISION_PENDING_REVIEW)

    def test_advertisement_is_rejected_decision(self):
        provider = FakeProvider(
            {
                "category": CATEGORY_ADVERTISEMENT,
                "decision": DECISION_REJECTED,
                "confidence": 0.88,
                "reason": "The content promotes a product instead of offering a job.",
            }
        )

        result = classify_opportunity_with_gemini(opportunity_payload(), provider=provider)

        self.assertEqual(result.decision, DECISION_REJECTED)

    def test_invalid_category_and_decision_fall_back_to_pending(self):
        provider = FakeProvider(
            {
                "category": "unknown",
                "decision": "publish_now",
                "confidence": 0.99,
                "reason": "Invalid output.",
            }
        )

        result = classify_opportunity_with_gemini(opportunity_payload(), provider=provider)

        self.assertEqual(result.category, CATEGORY_UNCLEAR)
        self.assertEqual(result.decision, DECISION_PENDING_REVIEW)
        self.assertEqual(result.raw_category, "unknown")
        self.assertEqual(result.raw_decision, "publish_now")

    def test_decision_is_normalized_and_confidence_is_capped(self):
        provider = FakeProvider(
            {
                "category": "Legitimate_Opportunity ",
                "decision": "Approved ",
                "confidence": 2.5,
                "reason": "Looks coherent.",
            }
        )

        result = classify_opportunity_with_gemini(opportunity_payload(), provider=provider)

        self.assertEqual(result.category, CATEGORY_LEGITIMATE)
        self.assertEqual(result.confidence, 1.0)
        self.assertEqual(result.decision, DECISION_APPROVED)

    def test_invalid_confidence_falls_back_to_zero(self):
        provider = FakeProvider(
            {
                "category": CATEGORY_LEGITIMATE,
                "decision": DECISION_APPROVED,
                "confidence": "high",
                "reason": "Looks coherent.",
            }
        )

        result = classify_opportunity_with_gemini(opportunity_payload(), provider=provider)

        self.assertEqual(result.confidence, 0.0)
        self.assertEqual(result.decision, DECISION_PENDING_REVIEW)

    def test_reason_is_truncated(self):
        provider = FakeProvider(
            {
                "category": CATEGORY_LEGITIMATE,
                "decision": DECISION_APPROVED,
                "confidence": 0.9,
                "reason": "A" * 500,
            }
        )

        result = classify_opportunity_with_gemini(opportunity_payload(), provider=provider)

        self.assertEqual(len(result.reason), 200)

    def test_provider_failure_is_safe_pending(self):
        provider = FakeProvider(error=LLMProviderError("boom"))

        result = classify_opportunity_with_gemini(opportunity_payload(), provider=provider)

        self.assertTrue(result.skipped)
        self.assertEqual(result.category, CATEGORY_UNCLEAR)
        self.assertEqual(result.decision, DECISION_PENDING_REVIEW)
        self.assertEqual(result.confidence, 0.0)

    def test_prompt_contains_real_few_shots_and_anti_hallucination_rule(self):
        provider = FakeProvider(
            {
                "category": CATEGORY_UNCLEAR,
                "decision": DECISION_PENDING_REVIEW,
                "confidence": 0.5,
                "reason": "Insufficient data.",
            }
        )

        classify_opportunity_with_gemini(opportunity_payload(), provider=provider)

        self.assertIn("Opportunity JSON:", provider.prompt)
        self.assertIn('"opportunity_type":"PROJET"', provider.prompt)
        self.assertIn('"category":"scam","decision":"rejected"', provider.prompt)
        self.assertIn("Base your decision ONLY on the data provided.", provider.prompt)
        self.assertIsNotNone(provider.schema)

    def test_compact_payload_excludes_organization_context_and_document_urls(self):
        compact = compact_moderation_payload(
            opportunity_payload(
                type="PROJET",
                project_details={
                    "public_buyer": "Commune de Tunis",
                    "documents": [
                        {
                            "type": "notice",
                            "label": "Avis",
                            "filename": "avis.pdf",
                            "url": "https://res.cloudinary.com/demo/raw/upload/avis.pdf",
                        }
                    ],
                },
            ),
            org_profile={
                "offers_published": 10,
                "days_since_registration": 100,
                "is_verified": True,
            },
        )

        self.assertNotIn("organization_context", compact)
        self.assertNotIn("url", compact["project_details"]["documents"][0])

    def test_to_dict_includes_final_decision(self):
        provider = FakeProvider(
            {
                "category": CATEGORY_LEGITIMATE,
                "decision": DECISION_APPROVED,
                "confidence": 0.9,
                "reason": "Coherent offer.",
            }
        )

        result = classify_opportunity_with_gemini(opportunity_payload(), provider=provider).to_dict()

        self.assertEqual(result["skipped"], False)
        self.assertEqual(result["final_decision"], DECISION_APPROVED)
        self.assertEqual(result["provider"], "gemini")
