from __future__ import annotations

from types import SimpleNamespace

from django.test import TestCase

from users.models import ProfileResume, Utilisateur
from users.resume_semantic.models import (
    SEMANTIC_RESUME_VERSION,
    SEMANTIC_STATUS_EMPTY,
    SEMANTIC_STATUS_SKIPPED,
    SEMANTIC_STATUS_SUCCEEDED,
)
from users.resume_semantic.service import process_profile_resume_semantics
from users.resume_semantic.normalization import clean_resume_semantic_text
from users.resume_semantic.structured_llm import extract_structured_resume_signals


class FakeProvider:
    provider_name = "test"
    model = "qwen-test"

    def __init__(self, payload):
        self.payload = payload
        self.prompts = []

    def generate_json(self, prompt, *, schema=None):
        self.prompts.append(prompt)
        assert schema is not None
        return self.payload


def qwen_payload(**overrides):
    payload = {
        "target_roles": ["Data Engineer"],
        "canonical_role": "Data Engineer",
        "skills": ["Python", "SQL", "ETL Pipelines"],
        "tools": ["Apache Spark", "Apache Airflow"],
        "domains": ["Data Engineering", "Big Data"],
        "business_families": ["data_ai"],
        "family_confidence": 0.96,
        "experience_level": "CONFIRME",
        "years_experience": 3,
        "languages": [],
        "contract_types": ["CDI / CDD"],
        "locations": ["Tunis / Ben Arous, Tunisia"],
        "confidence": 0.94,
    }
    payload.update(overrides)
    return payload


class StructuredResumeExtractionTests(TestCase):
    def test_semantic_text_truncation_keeps_late_tools_section(self):
        long_experience = " ".join(f"mission backend {index}" for index in range(180))
        resume_text = f"""
Hiba Belghith
Développeuse Backend Senior

Expérience Professionnelle
{long_experience}

Technologies & Outils
Python Django PostgreSQL Redis Celery Docker JWT
"""

        cleaned = clean_resume_semantic_text(resume_text, max_chars=450)

        self.assertIn("Python", cleaned)
        self.assertIn("Django", cleaned)
        self.assertIn("PostgreSQL", cleaned)
        self.assertLessEqual(len(cleaned), 450)

    def test_resume_tools_preserve_mixed_case_product_names(self):
        signals = extract_structured_resume_signals(
            "Backend developer using PostgreSQL / MySQL / MongoDB.",
            provider=FakeProvider(
                qwen_payload(
                    skills=[],
                    tools=["PostgreSQL / MySQL / MongoDB"],
                )
            ),
        )

        self.assertEqual(signals.tools, ["PostgreSQL", "MySQL", "MongoDB"])

    def test_resume_labels_restore_exact_source_surface_form(self):
        signals = extract_structured_resume_signals(
            "Comptable junior using Microsoft Excel, PowerPoint and Sage Comptabilité.",
            provider=FakeProvider(
                qwen_payload(
                    canonical_role="Comptable Junior",
                    target_roles=["Comptable Junior"],
                    skills=["Reporting Comptable"],
                    tools=["Microsoft Excel", "Power Point", "Sage Comptabilité"],
                    business_families=["accounting_finance_audit"],
                    domains=["Comptabilité"],
                )
            ),
        )

        self.assertIn("PowerPoint", signals.tools)
        self.assertNotIn("Power Point", signals.tools)
        self.assertIn("PowerPoint", signals.llm_enrichment["profile_suggestions"]["competences"])

    def test_qwen_extraction_produces_profile_ready_signals(self):
        signals = extract_structured_resume_signals(
            "Data Engineer with Python SQL Spark Airflow ETL in Tunis.",
            provider=FakeProvider(qwen_payload()),
        )

        self.assertEqual(signals.business_families, ["data_ai"])
        self.assertEqual(signals.canonical_role, "Data Engineer")
        self.assertEqual(signals.target_roles, ["Data Engineer"])
        self.assertIn("Python", signals.skills)
        self.assertIn("Apache Spark", signals.tools)
        self.assertEqual(signals.languages_detected, [])

        suggestions = signals.llm_enrichment["profile_suggestions"]
        self.assertEqual(suggestions["domaines_interet"], ["data_ai"])
        self.assertEqual(suggestions["target_roles"], ["Data Engineer"])
        self.assertEqual(suggestions["employment_types"], ["CDI", "CDD"])
        self.assertEqual(suggestions["preferred_locations"], ["Tunis", "Ben Arous"])

    def test_family_ids_are_not_allowed_as_roles(self):
        signals = extract_structured_resume_signals(
            "Data Engineer with Python SQL Spark Airflow ETL in Tunis.",
            provider=FakeProvider(
                qwen_payload(
                    target_roles=["data_ai"],
                    canonical_role="data_ai",
                )
            ),
        )

        self.assertEqual(signals.business_families, ["data_ai"])
        self.assertEqual(signals.canonical_role, "")
        self.assertEqual(signals.target_roles, [])


class ResumeSemanticServiceTests(TestCase):
    def setUp(self):
        self.user = Utilisateur.objects.create_user(
            username="semantic_resume_user",
            email="semantic_resume_user@example.com",
            password="x",
        )
        self.profile = self.user.profil

    def create_resume(self, text):
        return ProfileResume.objects.create(
            profile=self.profile,
            parsed_text=text,
            resume_text_embedding_source=text,
            parsing_status=ProfileResume.ParsingStatus.SUCCEEDED,
            is_active=True,
        )

    def test_process_resume_persists_qwen_structured_fields(self):
        resume = self.create_resume("Data Engineer Python SQL Apache Spark Airflow ETL Tunis CDI CDD")

        provider = FakeProvider(qwen_payload())
        original = extract_structured_resume_signals

        def fake_extract(text, *, provider=None):
            return original(text, provider=provider or FakeProvider(qwen_payload()))

        from users.resume_semantic import service

        service.extract_structured_resume_signals = lambda text: original(text, provider=provider)
        try:
            result = process_profile_resume_semantics(resume, force=True)
        finally:
            service.extract_structured_resume_signals = original

        resume.refresh_from_db()
        self.assertEqual(result["status"], SEMANTIC_STATUS_SUCCEEDED)
        self.assertEqual(resume.semantic_resume_version, SEMANTIC_RESUME_VERSION)
        self.assertEqual(resume.extracted_skills, ["Python", "SQL", "ETL Pipelines"])
        self.assertEqual(resume.extracted_tools, ["Apache Spark", "Apache Airflow"])
        self.assertEqual(resume.extracted_domains, ["Data Engineering", "Big Data"])
        self.assertEqual(resume.semantic_resume_metadata["business_families"], ["data_ai"])
        self.assertEqual(
            resume.semantic_resume_metadata["llm_enrichment"]["profile_suggestions"]["target_roles"],
            ["Data Engineer"],
        )

        second = process_profile_resume_semantics(resume)
        self.assertEqual(second["status"], SEMANTIC_STATUS_SKIPPED)

    def test_empty_resume_is_safe(self):
        resume = self.create_resume("")

        result = process_profile_resume_semantics(resume)

        resume.refresh_from_db()
        self.assertEqual(result["status"], SEMANTIC_STATUS_EMPTY)
        self.assertEqual(resume.extracted_skills, [])
        self.assertEqual(resume.semantic_resume_confidence, 0.0)
