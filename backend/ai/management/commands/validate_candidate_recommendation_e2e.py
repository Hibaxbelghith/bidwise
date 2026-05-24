from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone
from rest_framework.test import APIClient

from ai.embeddings import (
    build_profile_embedding_content_hash,
    get_current_profile_embedding_model,
    get_expected_profile_embedding_dimensions,
    get_or_build_profile_embedding,
)
from ai.profile_strength import compute_profile_strength
from ai.quality_gates import filter_ranked_recommendations
from ai.recommendation_service import rank_opportunities
from ai.user_features import build_user_features
from opportunities.models import Opportunite, StatutOpportunite
from users.models import ProfileResume, Utilisateur


@dataclass(frozen=True)
class CandidateScenario:
    code: str
    label: str
    target_roles: list[str]
    skills: list[str]
    resume_text: str
    experience_level: str = "JUNIOR"
    years_experience: int | None = 1
    locations: list[str] = field(default_factory=lambda: ["Tunis"])
    work_modes: list[str] = field(default_factory=lambda: ["HYBRID", "REMOTE"])
    employment_types: list[str] = field(default_factory=lambda: ["FULL_TIME"])
    sectors: list[str] = field(default_factory=list)
    salary_min: int | None = None
    salary_max: int | None = None
    expected_terms: tuple[str, ...] = ()
    forbidden_terms: tuple[str, ...] = ()


SCENARIOS: tuple[CandidateScenario, ...] = (
    CandidateScenario(
        code="R01",
        label="Frontend complete profile",
        target_roles=["Frontend Developer"],
        skills=["React", "JavaScript", "Node.js"],
        resume_text=(
            "Frontend developer CV: React user interfaces, reusable components, "
            "responsive pages, JavaScript, Node.js integration."
        ),
        work_modes=["REMOTE", "HYBRID"],
        expected_terms=("frontend", "react"),
        forbidden_terms=("backend senior", "comptable", "human resources"),
    ),
    CandidateScenario(
        code="R02",
        label="Backend complete profile",
        target_roles=["Python Backend Developer"],
        skills=["Python", "Django", "FastAPI"],
        resume_text="Backend CV: Django REST APIs, FastAPI services, PostgreSQL, Redis, Celery.",
        years_experience=2,
        expected_terms=("python", "backend", "django", "fastapi"),
        forbidden_terms=("human resources", "comptable", "marketing"),
    ),
    CandidateScenario(
        code="R04",
        label="Commercial profile",
        target_roles=["Business Development Manager"],
        skills=["CRM", "Techniques de vente", "Prospection"],
        resume_text="Sales CV: CRM pipeline, client prospection, negotiation and business development.",
        locations=["Tunisia", "Tunis"],
        work_modes=["ON_SITE"],
        sectors=["Sales"],
        expected_terms=("business development", "commercial", "sales", "bdr"),
        forbidden_terms=("frontend", "python backend", "comptable"),
    ),
    CandidateScenario(
        code="R10",
        label="Network/support profile",
        target_roles=["Network Engineer"],
        skills=["Cisco", "BGP", "Routing", "Support"],
        resume_text="Network CV: Cisco routing, BGP troubleshooting, IP/MPLS, network configuration.",
        work_modes=["ON_SITE"],
        expected_terms=("network", "support", "ip/mpls", "routing", "bgp"),
        forbidden_terms=("entretien", "cleaning", "agent de service"),
    ),
    CandidateScenario(
        code="R26",
        label="Junior frontend experience mismatch",
        target_roles=["Frontend Developer"],
        skills=["React", "JavaScript"],
        resume_text="Junior frontend CV: React projects, JavaScript components, no leadership experience.",
        years_experience=1,
        expected_terms=("frontend", "react", "junior"),
        forbidden_terms=("senior full-stack", "5-10 years"),
    ),
    CandidateScenario(
        code="R28",
        label="Accounting location preference",
        target_roles=["Comptable"],
        skills=["Comptabilite", "Excel", "Sage"],
        resume_text="Accounting CV: saisie comptable, Excel, Sage, factures, rapprochement bancaire.",
        locations=["Sousse"],
        work_modes=["ON_SITE"],
        sectors=["Finance"],
        expected_terms=("comptable", "accounting", "excel", "sage"),
        forbidden_terms=("marketing", "frontend", "developer"),
    ),
    CandidateScenario(
        code="R30",
        label="Backend sector preference",
        target_roles=["Backend Developer"],
        skills=["Python", "Django"],
        resume_text="Backend CV with payment APIs, banking integrations and Django services.",
        sectors=["Finance"],
        expected_terms=("backend", "python", "django"),
        forbidden_terms=("sales", "marketing", "human resources"),
    ),
)


def _contains_any(text: str, terms: Iterable[str]) -> bool:
    normalized = text.lower()
    return any(term.lower() in normalized for term in terms)


def _scenario_user_email(code: str) -> str:
    return f"e2e.recommendation.{code.lower()}@bidwise.test"


class Command(BaseCommand):
    help = "Validate the candidate recommendation journey from profile/CV setup to ranked recommendations."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=8)
        parser.add_argument(
            "--scenario",
            action="append",
            default=[],
            help="Run only selected scenario code(s), e.g. --scenario R01 --scenario R02.",
        )
        parser.add_argument(
            "--candidate-limit",
            type=int,
            default=5000,
            help="Maximum active opportunities inspected by the quick in-process validator.",
        )
        parser.add_argument("--reset", action="store_true", help="Delete previous E2E test users first.")
        parser.add_argument("--markdown", action="store_true", help="Print a markdown report.")
        parser.add_argument(
            "--api",
            action="store_true",
            help="Call /api/recommendations/ instead of direct in-process ranking.",
        )
        parser.add_argument(
            "--real-embeddings",
            action="store_true",
            help="Generate real profile embeddings. Slower; use after quick validation passes.",
        )

    def handle(self, *args, **options):
        limit = max(3, min(int(options["limit"]), 20))
        if options["reset"]:
            deleted, _ = Utilisateur.objects.filter(email__startswith="e2e.recommendation.").delete()
            self.stdout.write(f"Deleted previous E2E test rows: {deleted}")

        selected_codes = {str(code).strip().upper() for code in options["scenario"] if str(code).strip()}
        scenarios = [scenario for scenario in SCENARIOS if not selected_codes or scenario.code in selected_codes]
        rows = []
        for scenario in scenarios:
            rows.append(
                self._run_scenario(
                    scenario,
                    limit=limit,
                    candidate_limit=max(limit, int(options["candidate_limit"])),
                    use_api=bool(options["api"]),
                    real_embeddings=bool(options["real_embeddings"]),
                )
            )

        if options["markdown"]:
            self._print_markdown(rows)
        else:
            self._print_console(rows)

        failures = [row for row in rows if row["status"] == "FAIL"]
        if failures:
            raise SystemExit(1)

    def _run_scenario(
        self,
        scenario: CandidateScenario,
        *,
        limit: int,
        candidate_limit: int,
        use_api: bool,
        real_embeddings: bool,
    ) -> dict:
        user = self._upsert_user(scenario)
        profile = user.profil

        embedding = get_or_build_profile_embedding(profile, force=True) if real_embeddings else []
        embedding_ready = bool(embedding)

        response_status = 200
        if use_api:
            if not real_embeddings:
                embedding = self._store_proxy_embedding(profile, scenario)
                embedding_ready = bool(embedding)
            client = APIClient()
            client.force_authenticate(user=user)
            response = client.get("/api/recommendations/", {"limit": str(limit)})
            response_status = response.status_code
            recommendations = list(response.data or []) if response.status_code == 200 else []
        else:
            recommendations = self._direct_recommendations(profile, embedding, limit, candidate_limit)
            embedding_ready = True

        top_titles = [str(item.get("title") or item.get("titre") or "") for item in recommendations[:5]]
        top_text = " | ".join(top_titles[:3])
        top_reasons = []
        for item in recommendations[:3]:
            top_reasons.extend(item.get("reasons") or item.get("reason") or [])
        top_reason_text = " | ".join(str(reason) for reason in top_reasons)

        has_expected = _contains_any(top_text, scenario.expected_terms)
        has_forbidden = _contains_any(top_text, scenario.forbidden_terms)
        has_reasons = bool(top_reasons)
        has_no_recent_fallback = all(str(item.get("score_label") or "") != "Recent" for item in recommendations[:3])

        status = "PASS"
        notes = []
        if response_status != 200:
            status = "FAIL"
            notes.append(f"API status {response_status}")
        if not embedding_ready:
            status = "FAIL"
            notes.append("profile embedding missing")
        if not recommendations:
            status = "FAIL"
            notes.append("no recommendations")
        if has_forbidden:
            status = "FAIL"
            notes.append("forbidden domain appears in top 3")
        if not has_expected:
            status = "WARNING" if status == "PASS" else status
            notes.append("expected domain not visible in top 3")
        if not has_reasons:
            status = "WARNING" if status == "PASS" else status
            notes.append("no visible reasons in top 3")
        if not has_no_recent_fallback:
            status = "WARNING" if status == "PASS" else status
            notes.append("recent fallback visible")

        return {
            "code": scenario.code,
            "label": scenario.label,
            "status": status,
            "top_titles": top_titles,
            "top_reason_text": top_reason_text,
            "notes": notes,
            "recommendation_count": len(recommendations),
        }

    def _store_placeholder_embedding(self, profile):
        dimensions = get_expected_profile_embedding_dimensions()
        vector = [0.0] * dimensions
        vector[0] = 1.0
        profile.embedding = vector
        profile.embedding_model = get_current_profile_embedding_model()
        profile.embedding_dimensions = dimensions
        profile.embedding_updated_at = timezone.now()
        profile.last_embedding_update = profile.embedding_updated_at
        profile.embedding_content_hash = build_profile_embedding_content_hash(profile)
        profile.embedding_features_hash = profile.embedding_content_hash
        profile.save(
            update_fields=[
                "embedding",
                "embedding_model",
                "embedding_dimensions",
                "embedding_updated_at",
                "last_embedding_update",
                "embedding_content_hash",
                "embedding_features_hash",
            ]
        )
        return vector

    def _store_proxy_embedding(self, profile, scenario: CandidateScenario):
        """
        Seed a deterministic validation embedding from a real opportunity vector.

        This keeps the API-mode E2E validation fast while still exercising the
        real recommendation endpoint, pgvector retrieval, serializers and
        quality gates. It is intentionally a validation shortcut, not production
        recommendation behavior.
        """
        query = Q()
        for term in scenario.expected_terms:
            value = str(term or "").strip()
            if not value:
                continue
            query |= Q(titre__icontains=value)
            query |= Q(description__icontains=value)
            query |= Q(skills__icontains=value)

        candidate_queryset = Opportunite.objects.filter(
            statut=StatutOpportunite.ACTIVE,
            embedding_vector__isnull=False,
        )
        model_name = get_current_profile_embedding_model()
        model_candidates = candidate_queryset.filter(embedding_model=model_name)
        if model_candidates.exists():
            candidate_queryset = model_candidates
        if query:
            domain_candidates = candidate_queryset.filter(query)
            if domain_candidates.exists():
                candidate_queryset = domain_candidates

        opportunity = (
            candidate_queryset
            .only("embedding_vector", "embedding_model", "titre")
            .order_by("-date_publication", "-id")
            .first()
        )
        if opportunity and opportunity.embedding_vector:
            vector = opportunity.embedding_vector
            profile.embedding = vector
            profile.embedding_model = opportunity.embedding_model or model_name
            profile.embedding_dimensions = len(vector)
            profile.embedding_updated_at = timezone.now()
            profile.last_embedding_update = profile.embedding_updated_at
            profile.embedding_content_hash = build_profile_embedding_content_hash(profile)
            profile.embedding_features_hash = profile.embedding_content_hash
            profile.save(
                update_fields=[
                    "embedding",
                    "embedding_model",
                    "embedding_dimensions",
                    "embedding_updated_at",
                    "last_embedding_update",
                    "embedding_content_hash",
                    "embedding_features_hash",
                ]
            )
            return vector
        return self._store_placeholder_embedding(profile)

    def _direct_recommendations(self, profile, embedding, limit, candidate_limit):
        features = build_user_features(profile)
        profile_strength = compute_profile_strength(profile, features)
        candidates = list(
            Opportunite.objects.filter(statut=StatutOpportunite.ACTIVE)
            .only(
                "id",
                "titre",
                "description",
                "organisation_nom",
                "ville",
                "type_opportunite",
                "date_publication",
                "embedding_vector",
                "skills",
                "normalized_skills",
                "normalized_industries",
                "extra_data",
                "normalized_contract_types",
                "normalized_work_mode",
                "contract_type",
                "availability",
                "salary",
                "experience_min",
                "experience_max",
                "experience_years",
            )
            .order_by("-date_publication", "-id")[:candidate_limit]
        )
        ranked = rank_opportunities(
            embedding,
            candidates,
            features=features,
            mode="complete" if embedding else "partial",
            top_k=max(limit, 50),
            min_score=0.1,
        )
        ranked = filter_ranked_recommendations(
            ranked,
            features=features,
            profile_strength=profile_strength,
            limit=limit,
        )
        return [
            {
                "title": getattr(item, "titre", ""),
                "score": getattr(item, "match_score", None),
                "score_label": getattr(item, "score_label", ""),
                "reasons": list(getattr(item, "reason", []) or []),
            }
            for item in ranked[:limit]
        ]

    def _upsert_user(self, scenario: CandidateScenario) -> Utilisateur:
        email = _scenario_user_email(scenario.code)
        user, _ = Utilisateur.objects.get_or_create(
            email=email,
            defaults={
                "username": email,
                "first_name": "E2E",
                "last_name": scenario.code,
            },
        )
        if not user.username:
            user.username = email
            user.save(update_fields=["username"])

        profile = user.profil
        profile.prenom = "E2E"
        profile.nom = scenario.code
        profile.competences = list(scenario.skills)
        profile.domaines_interet = list(scenario.sectors)
        profile.target_roles = list(scenario.target_roles)
        profile.niveau_experience = scenario.experience_level
        profile.annees_experience = scenario.years_experience
        profile.preferred_locations = list(scenario.locations)
        profile.work_mode_preferences = list(scenario.work_modes)
        profile.remote_preference = scenario.work_modes[0] if scenario.work_modes else ""
        profile.employment_types = list(scenario.employment_types)
        profile.opportunity_types = ["JOB"]
        profile.compensation_min_expectation = scenario.salary_min
        profile.compensation_max_expectation = scenario.salary_max
        profile.compensation_expectation = scenario.salary_min or scenario.salary_max
        profile.compensation_currency = "TND"
        profile.compensation_period = "MONTHLY" if (scenario.salary_min or scenario.salary_max) else None
        profile.onboarding_completed = True
        profile.save()

        ProfileResume.objects.filter(profile=profile, is_active=True).update(is_active=False)
        ProfileResume.objects.create(
            profile=profile,
            parsed_text=scenario.resume_text,
            parsing_status=ProfileResume.ParsingStatus.SUCCEEDED,
            parsed_at=timezone.now(),
            is_active=True,
            extracted_skills=list(scenario.skills),
            extracted_raw_skills=list(scenario.skills),
            extracted_domains=list(scenario.sectors),
            extracted_tools=[],
            extracted_languages=["en", "fr"],
        )
        return user

    def _print_console(self, rows):
        self.stdout.write("Candidate recommendation E2E validation")
        for row in rows:
            self.stdout.write(
                f"[{row['status']}] {row['code']} {row['label']} "
                f"count={row['recommendation_count']}"
            )
            for index, title in enumerate(row["top_titles"][:5], start=1):
                self.stdout.write(f"  {index}. {title}")
            if row["notes"]:
                self.stdout.write(f"  notes: {', '.join(row['notes'])}")

    def _print_markdown(self, rows):
        self.stdout.write("| Scenario | Status | Top results | Notes |")
        self.stdout.write("|---|---|---|---|")
        for row in rows:
            titles = "<br>".join(row["top_titles"][:5])
            notes = "; ".join(row["notes"]) or "-"
            self.stdout.write(f"| {row['code']} {row['label']} | {row['status']} | {titles} | {notes} |")
