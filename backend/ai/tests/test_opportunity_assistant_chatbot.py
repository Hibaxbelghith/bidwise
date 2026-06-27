from unittest import TestCase
from unittest.mock import patch
from types import SimpleNamespace

from ai.llm.providers import LLMProviderError
from ai.resume_match.chatbot import (
    OPPORTUNITY_ASSISTANT_SCHEMA,
    OpportunityAssistantError,
    answer_opportunity_question,
)
from ai.resume_match.llm import _force_ats_score_in_markdown
from ai.views import (
    _cache_recommendation_contexts,
    _cached_recommendation_context,
    _opportunity_assistant_cache_key,
    _recommendation_context_cache_key,
)


class FakeProvider:
    provider_name = "fake"
    model = "fake-model"

    def __init__(self, payload=None, error=None):
        self.payload = payload
        self.error = error
        self.prompt = ""
        self.schema = None

    def generate_json(self, prompt, *, schema=None):
        self.prompt = prompt
        self.schema = schema
        if self.error:
            raise self.error
        return self.payload


class OpportunityAssistantChatbotTests(TestCase):
    def setUp(self):
        self.evidence = {
            "has_resume": True,
            "status": "READY",
            "opportunity": {
                "title": "Python Backend Developer",
                "company": "Example",
                "skills": ["Python", "Django"],
                "description_excerpt": "Build reliable APIs.",
            },
            "match": {
                "fit_score": 42,
                "verdict": "partial_match",
                "ats": {
                    "keyword_coverage_percent": 50,
                    "covered_keywords": ["Python"],
                    "missing_or_weak_keywords": ["Django"],
                },
            },
            "recommendation": {
                "score_percent": 76,
                "score_label": "Good match",
                "confidence": "MEDIUM",
                "bucket": "STRONG_MATCH",
                "reasons": ["Python Backend Developer role aligned"],
            },
        }

    def test_returns_validated_answer_and_uses_minimal_schema(self):
        provider = FakeProvider(payload={"answer": "Python and Django are required.", "answered": True})

        result = answer_opportunity_question("What skills are required?", self.evidence, provider=provider)

        self.assertEqual(result["answer"], "Python and Django are required.")
        self.assertTrue(result["answered"])
        self.assertEqual(result["provider"], "fake")
        self.assertEqual(provider.schema, OPPORTUNITY_ASSISTANT_SCHEMA)
        self.assertIn('"fit_score":42', provider.prompt)
        self.assertIn('"score_percent":76', provider.prompt)
        self.assertIn("CV-to-job fit score", provider.prompt)
        self.assertIn("Related opportunities to review", provider.prompt)
        self.assertIn("For a simple greeting or thanks", provider.prompt)
        self.assertIn("provide a compact role-specific template", provider.prompt)
        self.assertIn("Do not merely repeat the previous answer", provider.prompt)
        self.assertIn("Component percentages are input signal values", provider.prompt)
        self.assertIn("use recommendation.scoring_mode", provider.prompt)
        self.assertIn("When asked to explain the offer", provider.prompt)
        self.assertIn("70% semantic similarity", provider.prompt)
        self.assertNotIn("resume_text", provider.prompt)

    def test_prompt_answers_multilingual_questions_in_the_question_language(self):
        provider = FakeProvider(payload={"answer": "Le poste exige Python et Django.", "answered": True})

        answer_opportunity_question("Quelles compétences sont requises ?", self.evidence, provider=provider)

        self.assertIn("Understand questions written in English, French, Arabic, or mixed language", provider.prompt)
        self.assertIn("answer in that same language", provider.prompt)
        self.assertIn("If the question is in French, answer entirely in French", provider.prompt)

    def test_includes_recent_history_to_resolve_follow_up_questions(self):
        provider = FakeProvider(payload={"answer": "It is the recommendation score.", "answered": True})
        history = [
            {"role": "user", "content": "What is 53%?"},
            {"role": "assistant", "content": "53% is the recommendation score shown in Your fit."},
        ]

        answer_opportunity_question("How was it calculated?", self.evidence, history=history, provider=provider)

        self.assertIn('"content":"What is 53%?"', provider.prompt)
        self.assertIn('"content":"53% is the recommendation score shown in Your fit."', provider.prompt)

    def test_accepts_context_without_resume(self):
        provider = FakeProvider(
            payload={
                "answer": "The opportunity requires Python and Django, but no resume match is available.",
                "answered": True,
            }
        )
        evidence = {**self.evidence, "has_resume": False, "status": "NO_RESUME", "match": {}}

        result = answer_opportunity_question("What skills are required?", evidence, provider=provider)

        self.assertTrue(result["answered"])
        self.assertIn('"has_resume":false', provider.prompt)

    def test_rejects_invalid_answered_value(self):
        provider = FakeProvider(payload={"answer": "Available.", "answered": "yes"})

        with self.assertRaises(OpportunityAssistantError):
            answer_opportunity_question("Is this available?", self.evidence, provider=provider)

    def test_wraps_provider_errors(self):
        provider = FakeProvider(error=LLMProviderError("private provider failure"))

        with self.assertRaises(OpportunityAssistantError) as raised:
            answer_opportunity_question("What skills are required?", self.evidence, provider=provider)

        self.assertNotIn("private provider failure", str(raised.exception))

    def test_cache_key_changes_when_active_resume_changes(self):
        request = SimpleNamespace(user=SimpleNamespace(id=7))
        opportunity = SimpleNamespace(id=11, date_modification=None)
        first_evidence = {"resume": {"id": 21, "updated_at": "2026-06-04T10:00:00Z"}}
        second_evidence = {"resume": {"id": 22, "updated_at": "2026-06-04T10:05:00Z"}}

        first_key = _opportunity_assistant_cache_key(
            request,
            opportunity,
            first_evidence,
            "Why is my score low?",
        )
        second_key = _opportunity_assistant_cache_key(
            request,
            opportunity,
            second_evidence,
            "Why is my score low?",
        )

        self.assertNotEqual(first_key, second_key)

    def test_cache_key_changes_when_conversation_history_changes(self):
        request = SimpleNamespace(user=SimpleNamespace(id=7))
        opportunity = SimpleNamespace(id=11, date_modification=None)
        first_evidence = {
            "conversation_history": [{"role": "assistant", "content": "53% is the recommendation score."}]
        }
        second_evidence = {
            "conversation_history": [{"role": "assistant", "content": "100% is the ATS score."}]
        }

        first_key = _opportunity_assistant_cache_key(request, opportunity, first_evidence, "How was it calculated?")
        second_key = _opportunity_assistant_cache_key(request, opportunity, second_evidence, "How was it calculated?")

        self.assertNotEqual(first_key, second_key)

    @patch("ai.views._recommendations_cache_key", return_value="recommendations-key")
    @patch("ai.views.cache.get")
    def test_reads_displayed_recommendation_score_from_server_cache(self, cache_get, _cache_key):
        cache_get.return_value = [
            {
                "id": 11,
                "match_score": 0.76,
                "semantic_score": 0.64,
                "business_score": 0.18,
                "feedback_score": 0.02,
                "score_label": "Good match",
                "recommendation_confidence": "MEDIUM",
                "recommendation_bucket": "STRONG_MATCH",
                "recommendation_mode": "complete",
                "recommendation_scoring_mode": "complete",
                "reason": ["Python role aligned"],
                "gaps": ["Industry alignment is not established"],
                "evidence_summary": {"skill_matches": ["python"]},
            }
        ]
        request = SimpleNamespace(user=SimpleNamespace(id=7))

        context = _cached_recommendation_context(request, 11)

        self.assertEqual(context["score_percent"], 76)
        self.assertEqual(context["score_label"], "Good match")
        self.assertEqual(context["mode"], "complete")
        self.assertEqual(context["scoring_mode"], "complete")
        self.assertEqual(context["reasons"], ["Python role aligned"])
        self.assertEqual(context["gaps"], ["Industry alignment is not established"])
        self.assertEqual(context["semantic_score_percent"], 64)
        self.assertEqual(context["business_score_percent"], 18)
        self.assertEqual(context["feedback_score_percent"], 2)
        self.assertEqual(context["evidence_summary"], {"skill_matches": ["python"]})

    @patch("ai.views._recommendations_cache_key", return_value="recommendations-state")
    def test_caches_and_reads_displayed_recommendation_independently_of_list_limit(self, _cache_key):
        request = SimpleNamespace(user=SimpleNamespace(id=7))
        recommendation = {
            "id": 11,
            "match_score": 0.53,
            "score_label": "Worth a look",
            "recommendation_confidence": "MEDIUM",
        }

        _cache_recommendation_contexts(request, [recommendation])
        context = _cached_recommendation_context(request, 11)

        self.assertEqual(context["score_percent"], 53)
        self.assertEqual(context["score_label"], "Worth a look")
        self.assertTrue(_recommendation_context_cache_key(request, 11).startswith("ai:recommendation-context:"))

    @patch("ai.views._recommendations_cache_key", return_value="recommendations-key")
    @patch("ai.views.cache.get", return_value=None)
    def test_recommendation_context_is_empty_when_server_cache_is_missing(self, _cache_get, _cache_key):
        request = SimpleNamespace(user=SimpleNamespace(id=7))

        context = _cached_recommendation_context(request, 11)

        self.assertEqual(context, {})

    def test_forces_deterministic_ats_score_in_generated_markdown(self):
        markdown = (
            "## 4. ATS analysis\n"
            "- BidWise ATS Score: 99%\n"
            "- ATS compatibility level: Good"
        )

        normalized = _force_ats_score_in_markdown(markdown, 100)

        self.assertIn("BidWise ATS Score: 100%", normalized)
        self.assertNotIn("99%", normalized)
