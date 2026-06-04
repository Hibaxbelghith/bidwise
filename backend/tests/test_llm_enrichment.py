from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, override_settings

from ai.llm import enrich_opportunity_text, enrich_resume_text, get_llm_provider
from ai.llm.providers import (
    FallbackLLMProvider,
    GeminiProvider,
    LLMProviderUnavailable,
    LLMRateLimitError,
    LLMTransientProviderError,
    OllamaProvider,
)
from ai.llm.providers import _extract_json_object
from ai.llm.schemas import validate_llm_extraction


class FakeProvider:
    provider_name = "fake"
    model = "fake-model"

    def __init__(self, payload):
        self.payload = payload
        self.prompts = []

    def generate_json(self, prompt, *, schema=None):
        self.prompts.append(prompt)
        assert schema is not None
        return self.payload


class FailingTransientProvider:
    provider_name = "failing"
    model = "failing-model"

    def generate_json(self, prompt, *, schema=None):
        raise LLMTransientProviderError("temporary")


class FailingRateLimitProvider:
    provider_name = "rate-limited"
    model = "rate-limited-model"

    def __init__(self):
        self.calls = 0

    def generate_json(self, prompt, *, schema=None):
        self.calls += 1
        raise LLMRateLimitError("quota", retry_after_seconds=54)


class LLMEnrichmentTests(SimpleTestCase):
    def test_validate_llm_extraction_sanitizes_payload(self):
        result = validate_llm_extraction(
            {
                "target_roles": ["Backend Developer", "Backend Developer", ""],
                "skills": ["Python", "Django"],
                "tools": ["PostgreSQL"],
                "domains": ["SaaS"],
                "business_families": ["backend", "engineering_construction", "invalid_family"],
                "family_confidence": 0.92,
                "seniority": "mid",
                "experience_level": "CONFIRMÉ",
                "years_experience": 3,
                "years_experience_min": 5,
                "years_experience_max": 2,
                "languages": ["French", "English"],
                "contract_types": ["CDI"],
                "work_modes": ["Hybrid"],
                "evidence": ["Python Django APIs"],
                "warnings": ["limited_text"],
                "confidence": 1.8,
            },
            provider="gemini",
            model="gemini-2.5-flash",
        )

        self.assertEqual(result.target_roles, ["Backend Developer"])
        self.assertEqual(result.business_families, ["backend", "engineering_construction"])
        self.assertEqual(result.family_confidence, 0.92)
        self.assertEqual(result.experience_level, "CONFIRME")
        self.assertEqual(result.years_experience, 3)
        self.assertEqual(result.years_experience_min, 2)
        self.assertEqual(result.years_experience_max, 5)
        self.assertEqual(result.confidence, 1.0)

    def test_validate_llm_extraction_dedupes_soft_skills_from_skills(self):
        result = validate_llm_extraction(
            {
                "target_roles": ["Instrumentiste"],
                "canonical_role": "Instrumentiste",
                "skills": ["Rigueur", "Bloc opératoire", "Communication"],
                "tools": [],
                "soft_skills": ["Rigueur", "Communication"],
                "domains": ["Healthcare"],
                "business_families": ["healthcare"],
                "family_confidence": 0.9,
                "seniority": "",
                "experience_level": "",
                "years_experience": None,
                "languages": [],
                "evidence": [],
                "warnings": [],
                "confidence": 0.8,
            },
            provider="test",
            model="test",
        )

        self.assertEqual(result.skills, ["Bloc opératoire"])
        self.assertEqual(result.soft_skills, ["Rigueur", "Communication"])

    def test_extract_json_object_accepts_markdown_fenced_json(self):
        payload = _extract_json_object('```json\n{"skills":["Python"],"confidence":0.8}\n```')

        self.assertEqual(payload["skills"], ["Python"])

    def test_resume_enrichment_uses_structured_prompt_and_provider(self):
        provider = FakeProvider(
            {
                "target_roles": ["Python Backend Developer"],
                "skills": ["Python", "Django", "FastAPI"],
                "tools": ["PostgreSQL"],
                "domains": ["Backend web services"],
                "business_families": ["backend"],
                "family_confidence": 0.9,
                "seniority": "mid",
                "experience_level": "CONFIRME",
                "years_experience": 2,
                "languages": ["English"],
                "evidence": ["Python Django FastAPI"],
                "warnings": [],
                "confidence": 0.92,
            }
        )

        result = enrich_resume_text("Python Django FastAPI PostgreSQL backend engineer.", provider=provider)

        self.assertEqual(result.target_roles, ["Python Backend Developer"])
        self.assertEqual(result.business_families, ["backend"])
        self.assertIn("Python", result.skills)
        self.assertIn("CV text:", provider.prompts[0])

    def test_opportunity_enrichment_extracts_from_job_context(self):
        provider = FakeProvider(
            {
                "target_roles": ["Frontend React Developer"],
                "skills": ["React", "JavaScript", "TypeScript"],
                "tools": [],
                "domains": ["Frontend development"],
                "business_families": ["frontend"],
                "family_confidence": 0.9,
                "seniority": "junior",
                "experience_level": "JUNIOR",
                "years_experience": 1,
                "languages": ["English"],
                "evidence": ["Create React and TypeScript user interfaces"],
                "warnings": [],
                "confidence": 0.89,
            }
        )
        opportunity = SimpleNamespace(
            titre="Frontend React Developer",
            description="Create React and TypeScript user interfaces.",
            organisation_nom="PixelWorks",
            ville="Tunis",
            contract_type="CDI",
            availability="Remote",
            skills=[],
        )

        result = enrich_opportunity_text(opportunity, provider=provider)

        self.assertEqual(result.business_families, ["frontend"])
        self.assertIn("React", result.skills)
        self.assertIn("Title: Frontend React Developer", provider.prompts[0])

    def test_opportunity_prompt_guides_engineering_without_tech_family_guessing(self):
        provider = FakeProvider(
            {
                "target_roles": ["Hydraulic Engineer"],
                "canonical_role": "Hydraulic Engineer",
                "skills": ["Infrastructure hydraulique", "AutoCAD"],
                "tools": [],
                "domains": ["Hydraulic infrastructure"],
                "business_families": ["engineering_construction"],
                "family_confidence": 0.9,
                "seniority": "senior",
                "experience_level": "SENIOR",
                "years_experience": 5,
                "languages": ["French"],
                "evidence": ["Etudes d'infrastructures hydrauliques"],
                "warnings": [],
                "confidence": 0.9,
            }
        )
        opportunity = SimpleNamespace(
            titre="Ingénieur Hydraulique confirmé",
            description="Etudes d'infrastructures hydrauliques et aménagements hydroagricoles.",
            organisation_nom="Engineering Office",
            ville="Tunis",
            contract_type="CDI",
            availability="Plein temps",
            skills=[],
        )

        result = enrich_opportunity_text(opportunity, provider=provider)

        self.assertEqual(result.business_families, ["engineering_construction"])
        self.assertIn("Use engineering_construction", provider.prompts[0])
        self.assertIn("business_families is secondary", provider.prompts[0])
        self.assertIn("family_confidence", provider.prompts[0])
        self.assertIn("experience_level must be one of DEBUTANT, JUNIOR, CONFIRME, SENIOR", provider.prompts[0])
        self.assertIn("Do not expand acronyms", provider.prompts[0])
        self.assertIn("Do not return legacy aliases for opportunities", provider.prompts[0])
        self.assertIn("operating room", provider.prompts[0])
        self.assertIn("Do not use engineering_construction for operating room", provider.prompts[0])
        self.assertIn("Prefer deriving skills from mission/responsibility/action sections", provider.prompts[0])
        self.assertIn("For security_safety roles, derive skills from operational duties", provider.prompts[0])
        self.assertIn("Apply this candidate-relevance test", provider.prompts[0])
        self.assertIn("Existing skills are candidate signals", provider.prompts[0])
        self.assertIn("company history, culture, values, employee benefits", provider.prompts[0])
        self.assertIn("Candidate-facing fields", provider.prompts[0])
        self.assertIn("collaborating with QA or Project Management", provider.prompts[0])
        self.assertIn("Prefer omission over guessing", provider.prompts[0])

    @override_settings(LLM_ENRICHMENT_ENABLED=False)
    def test_provider_is_disabled_by_default(self):
        provider = get_llm_provider()

        with self.assertRaises(LLMProviderUnavailable):
            provider.generate_json("{}", schema={})

    @override_settings(
        LLM_ENRICHMENT_ENABLED=True,
        LLM_PROVIDER="gemini",
        GEMINI_API_KEY="test-key",
        GEMINI_MODEL="gemini-test",
        GEMINI_FALLBACK_MODELS="",
        GEMINI_API_BASE_URL="https://example.test/v1beta",
        GEMINI_TIMEOUT_SECONDS=3.0,
        GEMINI_TEMPERATURE=0.0,
        GEMINI_MAX_OUTPUT_TOKENS=200,
    )
    def test_gemini_provider_parses_json_response(self):
        response = Mock()
        response.status_code = 200
        response.json.return_value = {
            "candidates": [
                {"content": {"parts": [{"text": '{"skills":["Python"],"confidence":0.8}'}]}}
            ]
        }

        with patch("ai.llm.providers.requests.post", return_value=response) as post:
            provider = get_llm_provider()
            payload = provider.generate_json("extract", schema={"type": "object"})

        self.assertIsInstance(provider, GeminiProvider)
        self.assertEqual(payload["skills"], ["Python"])
        self.assertEqual(post.call_args.kwargs["params"]["key"], "test-key")
        self.assertEqual(post.call_args.kwargs["json"]["generationConfig"]["responseMimeType"], "application/json")

    @override_settings(
        LLM_ENRICHMENT_ENABLED=True,
        LLM_PROVIDER="gemini",
        GEMINI_API_KEY="test-key",
        GEMINI_MODEL="gemini-test",
        GEMINI_FALLBACK_MODELS="",
        GEMINI_API_BASE_URL="https://example.test/v1beta",
    )
    def test_gemini_provider_raises_rate_limit_error_on_429(self):
        response = Mock()
        response.status_code = 429
        response.text = '{"error":{"status":"RESOURCE_EXHAUSTED"}}'

        with patch("ai.llm.providers.requests.post", return_value=response):
            provider = get_llm_provider()
            with self.assertRaises(LLMRateLimitError):
                provider.generate_json("extract", schema={"type": "object"})

    @override_settings(
        LLM_ENRICHMENT_ENABLED=True,
        LLM_PROVIDER="gemini",
        GEMINI_API_KEY="test-key",
        GEMINI_MODEL="gemini-test",
        GEMINI_FALLBACK_MODELS="",
        GEMINI_API_BASE_URL="https://example.test/v1beta",
    )
    def test_gemini_provider_raises_transient_error_on_503(self):
        response = Mock()
        response.status_code = 503
        response.text = '{"error":{"status":"UNAVAILABLE"}}'

        with patch("ai.llm.providers.requests.post", return_value=response):
            provider = get_llm_provider()
            with self.assertRaises(LLMTransientProviderError):
                provider.generate_json("extract", schema={"type": "object"})

    def test_fallback_provider_tries_next_provider_after_transient_error(self):
        fallback = FallbackLLMProvider(
            providers=(
                FailingTransientProvider(),
                FakeProvider({"skills": ["Excel"], "confidence": 0.8}),
            ),
            max_retries=0,
            retry_delay_seconds=0,
            retry_backoff_factor=1,
        )

        payload = fallback.generate_json("extract", schema={"type": "object"})

        self.assertEqual(payload["skills"], ["Excel"])

    def test_fallback_provider_does_not_retry_rate_limited_provider(self):
        provider = FailingRateLimitProvider()
        fallback = FallbackLLMProvider(
            providers=(provider,),
            max_retries=3,
            retry_delay_seconds=0,
            retry_backoff_factor=1,
        )

        with self.assertRaises(LLMRateLimitError) as context:
            fallback.generate_json("extract", schema={"type": "object"})

        self.assertEqual(provider.calls, 1)
        self.assertEqual(context.exception.retry_after_seconds, 54)

    @override_settings(
        LLM_ENRICHMENT_ENABLED=True,
        LLM_PROVIDER="gemini",
        GEMINI_API_KEY="test-key",
        GEMINI_MODEL="gemini-primary",
        GEMINI_FALLBACK_MODELS="gemini-fallback",
        OLLAMA_FALLBACK_ENABLED=True,
        OLLAMA_MODEL="qwen2.5:7b-instruct",
    )
    def test_provider_factory_builds_hybrid_chain(self):
        provider = get_llm_provider()

        self.assertIsInstance(provider, FallbackLLMProvider)
        self.assertEqual([item.provider_name for item in provider.providers], ["gemini", "gemini", "ollama"])
        self.assertEqual([item.model for item in provider.providers], [
            "gemini-primary",
            "gemini-fallback",
            "qwen2.5:7b-instruct",
        ])

    @override_settings(
        LLM_ENRICHMENT_ENABLED=True,
        LLM_PROVIDER="ollama",
        OLLAMA_MODEL="qwen2.5:7b-instruct",
        OLLAMA_BASE_URL="http://ollama.test",
        OLLAMA_TIMEOUT_SECONDS=3.0,
    )
    def test_ollama_provider_parses_json_response(self):
        response = Mock()
        response.status_code = 200
        response.json.return_value = {"response": '{"skills":["Sage"],"confidence":0.81}'}

        with patch("ai.llm.providers.requests.post", return_value=response) as post:
            provider = get_llm_provider()
            payload = provider.generate_json("extract", schema={"type": "object"})

        self.assertIsInstance(provider, OllamaProvider)
        self.assertEqual(payload["skills"], ["Sage"])
        self.assertEqual(post.call_args.args[0], "http://ollama.test/api/generate")
        self.assertEqual(post.call_args.kwargs["json"]["model"], "qwen2.5:7b-instruct")
