from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from ai.crossencoder.models import CrossEncoderCandidateScore
from ai.crossencoder.service import rerank_ranked_opportunities
from ai.profile_strength import compute_profile_strength
from ai.quality_gates import filter_ranked_recommendations


def opportunity(identifier, title, *, score=0.7, skills=None, description=""):
    return SimpleNamespace(
        id=identifier,
        titre=title,
        description=description or title,
        skills=skills or [],
        organisation_nom="BenchmarkCo",
        ville="Tunis",
        date_publication=date(2026, 5, 1),
        match_score=score,
        score=score,
        similarity_score=score,
        semantic_score=score,
        business_score=0.1,
        feedback_score=0.0,
        score_label="Good match",
        score_level="MEDIUM",
        reason=[],
    )


def ce_scores(*values):
    return [
        CrossEncoderCandidateScore(score=value, raw_score=value, metadata={"pair_index": index})
        for index, value in enumerate(values)
    ]


@override_settings(
    CROSS_ENCODER_ENABLED=True,
    CROSS_ENCODER_WEIGHT=0.25,
    CROSS_ENCODER_MAX_CANDIDATES=30,
)
class CrossEncoderRerankingTests(SimpleTestCase):
    def test_devops_profile_demotes_hr_false_positive(self):
        hr = opportunity(1, "HR Talent Acquisition Specialist", score=0.90, skills=["Recruitment"])
        devops = opportunity(
            2,
            "DevOps Platform Engineer",
            score=0.80,
            skills=["Docker", "Kubernetes", "Terraform"],
        )

        with patch("ai.crossencoder.service.score_opportunities", return_value=ce_scores(0.05, 0.96)):
            ranked = rerank_ranked_opportunities(
                [hr, devops],
                features={"skills": ["Docker", "Kubernetes", "Terraform"], "roles": ["DevOps Engineer"]},
            )

        self.assertEqual(ranked[0].id, devops.id)
        self.assertLess(hr.match_score, devops.match_score)

    def test_python_backend_profile_demotes_accounting_job(self):
        accounting = opportunity(1, "Accounting Assistant", score=0.88, skills=["Excel", "Finance"])
        backend = opportunity(2, "Python Backend Developer", score=0.78, skills=["Python", "Django"])

        with patch("ai.crossencoder.service.score_opportunities", return_value=ce_scores(0.02, 0.98)):
            ranked = rerank_ranked_opportunities(
                [accounting, backend],
                features={"skills": ["Python", "Django"], "roles": ["Backend Developer"]},
            )

        self.assertEqual(ranked[0].titre, "Python Backend Developer")

    def test_frontend_react_profile_demotes_recruiter_job(self):
        recruiter = opportunity(1, "Technical Recruiter", score=0.86, skills=["Recruitment"])
        frontend = opportunity(2, "Frontend React Developer", score=0.77, skills=["React", "TypeScript"])

        with patch("ai.crossencoder.service.score_opportunities", return_value=ce_scores(0.08, 0.95)):
            ranked = rerank_ranked_opportunities(
                [recruiter, frontend],
                features={"skills": ["React", "TypeScript"], "roles": ["Frontend Developer"]},
            )

        self.assertEqual(ranked[0].id, frontend.id)

    def test_sparse_profile_keeps_quality_gate_safeguards(self):
        python_job = opportunity(1, "Python Developer", score=0.42, skills=["Python"])
        hr = opportunity(2, "HR Assistant", score=0.44, skills=["Recruitment"])
        features = {"skills": ["Python"]}
        profile_strength = compute_profile_strength(SimpleNamespace(onboarding_completed=False), features)

        with patch("ai.crossencoder.service.score_opportunities", return_value=ce_scores(0.80, 0.95)):
            ranked = rerank_ranked_opportunities([python_job, hr], features=features)
        filtered = filter_ranked_recommendations(
            ranked,
            features=features,
            profile_strength=profile_strength,
            limit=10,
        )

        self.assertEqual([item.id for item in filtered], [python_job.id])

    def test_cv_only_profile_can_be_semantically_reranked(self):
        generic = opportunity(1, "General IT Support", score=0.72, skills=["Windows"])
        platform = opportunity(2, "Cloud Platform Engineer", score=0.69, skills=["Kubernetes", "Terraform"])

        with patch("ai.crossencoder.service.score_opportunities", return_value=ce_scores(0.25, 0.97)):
            ranked = rerank_ranked_opportunities(
                [generic, platform],
                features={"resume_text": "Kubernetes Terraform CI/CD cloud infrastructure"},
            )

        self.assertEqual(ranked[0].id, platform.id)

    def test_arabic_french_english_multilingual_cases_are_supported(self):
        recruiter = opportunity(1, "Chargé de recrutement", score=0.83, skills=["RH"])
        backend = opportunity(2, "Développeur Backend Python", score=0.79, skills=["Python", "Django"])

        with patch("ai.crossencoder.service.score_opportunities", return_value=ce_scores(0.05, 0.93)):
            ranked = rerank_ranked_opportunities(
                [recruiter, backend],
                features={
                    "skills": ["Python", "Django", "بايثون"],
                    "roles": ["Développeur Backend", "مهندس برمجيات"],
                    "resume_text": "Développement APIs Django et PostgreSQL.",
                },
            )

        self.assertEqual(ranked[0].titre, "Développeur Backend Python")

    def test_reranking_is_deterministic(self):
        rows = [
            opportunity(1, "Backend A", score=0.70, skills=["Python"]),
            opportunity(2, "Backend B", score=0.70, skills=["Python"]),
            opportunity(3, "Backend C", score=0.70, skills=["Python"]),
        ]

        with patch("ai.crossencoder.service.score_opportunities", return_value=ce_scores(0.5, 0.5, 0.5)):
            first = rerank_ranked_opportunities(list(rows), features={"skills": ["Python"]})
        with patch("ai.crossencoder.service.score_opportunities", return_value=ce_scores(0.5, 0.5, 0.5)):
            second = rerank_ranked_opportunities(list(rows), features={"skills": ["Python"]})

        self.assertEqual([item.id for item in first], [item.id for item in second])

    @override_settings(CROSS_ENCODER_MAX_CANDIDATES=3)
    def test_candidate_cap_is_enforced(self):
        rows = [
            opportunity(index, f"Python Job {index}", score=0.9 - (index * 0.01), skills=["Python"])
            for index in range(1, 8)
        ]

        def fake_score(features, opportunities):
            self.assertEqual(len(opportunities), 3)
            return ce_scores(0.9, 0.8, 0.7)

        with patch("ai.crossencoder.service.score_opportunities", side_effect=fake_score) as mocked:
            rerank_ranked_opportunities(rows, features={"skills": ["Python"]})

        self.assertEqual(mocked.call_count, 1)
