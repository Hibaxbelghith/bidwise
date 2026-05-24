from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIRequestFactory

from ai.business_families import profile_business_families
from ai.user_features import build_user_features
from users.models import ProfileResume, Utilisateur
from users.resume_parsing.service import parse_resume_file
from users.resume_semantic.service import process_profile_resume_semantics


@dataclass(frozen=True)
class CVScenario:
    key: str
    filename: str
    desired_title: str
    experience_level: str
    years_experience: float
    locations: tuple[str, ...]
    contract_types: tuple[str, ...]
    expected_families: tuple[str, ...]
    expected_title_terms: tuple[str, ...]
    expected_sector_terms: tuple[str, ...] = ()


SCENARIOS: tuple[CVScenario, ...] = (
    CVScenario(
        key="comptable_junior",
        filename="cv_comptable_junior.pdf",
        desired_title="Comptable junior",
        experience_level="DEBUTANT",
        years_experience=1,
        locations=("Tunis", "Ben Arous"),
        contract_types=("CDI", "CDD"),
        expected_families=("accounting_finance", "accounting_finance_audit"),
        expected_title_terms=("comptable", "accounting", "audit", "finance"),
        expected_sector_terms=("compt", "audit", "finance"),
    ),
    CVScenario(
        key="support_it_junior",
        filename="cv_support_it_junior.pdf",
        desired_title="Technicien support informatique",
        experience_level="JUNIOR",
        years_experience=1,
        locations=("Tunis", "Ben Arous"),
        contract_types=("CDI", "CDD"),
        expected_families=("it_network_support", "it_support_network"),
        expected_title_terms=("support", "helpdesk", "system", "système", "reseau", "réseau", "informatique"),
        expected_sector_terms=("informatique", "telecom", "télécom"),
    ),
    CVScenario(
        key="assistante_admin",
        filename="cv_assistante_admin.pdf",
        desired_title="Assistante administrative",
        experience_level="JUNIOR",
        years_experience=1,
        locations=("Tunis", "Ben Arous"),
        contract_types=("CDI", "CDD"),
        expected_families=("administration", "hr_administration"),
        expected_title_terms=("assistante", "assistant", "administrative", "administratif", "secrétaire", "secretaire"),
        expected_sector_terms=("administr", "secr", "assistan"),
    ),
    CVScenario(
        key="marketing_junior",
        filename="cv_marketing_junior.pdf",
        desired_title="Chargé marketing digital",
        experience_level="JUNIOR",
        years_experience=1,
        locations=("Tunis", "Ben Arous"),
        contract_types=("CDI", "CDD"),
        expected_families=("marketing", "marketing_communication"),
        expected_title_terms=("marketing", "community", "digital", "seo", "communication"),
        expected_sector_terms=("marketing", "communication"),
    ),
    CVScenario(
        key="commercial_senior",
        filename="cv_commercial.pdf",
        desired_title="Commercial senior",
        experience_level="SENIOR",
        years_experience=5,
        locations=("Tunis", "Ben Arous", "Sousse"),
        contract_types=("CDI",),
        expected_families=("sales", "sales_business"),
        expected_title_terms=("commercial", "sales", "vente", "business", "account"),
        expected_sector_terms=("vente", "commerce", "commercial"),
    ),
    CVScenario(
        key="data_ai_junior",
        filename="cv_data_ai.pdf",
        desired_title="Data analyst junior",
        experience_level="JUNIOR",
        years_experience=1,
        locations=("Tunis", "Ben Arous"),
        contract_types=("CDI", "CDD"),
        expected_families=("data_ai",),
        expected_title_terms=("data", "bi", "analyst", "ia", "ai", "machine learning"),
        expected_sector_terms=("data", "informatique", "ai", "ia"),
    ),
    CVScenario(
        key="backend_senior",
        filename="cv_developpeur_backend.pdf",
        desired_title="Développeur backend senior",
        experience_level="SENIOR",
        years_experience=10,
        locations=("Tunis", "Ben Arous", "Ariana"),
        contract_types=("CDI",),
        expected_families=("backend", "software_web"),
        expected_title_terms=("backend", "python", "django", "developer", "développeur", "developpeur", "software"),
        expected_sector_terms=("informatique", "software", "web"),
    ),
    CVScenario(
        key="infirmier_junior",
        filename="cv_infirmier.pdf",
        desired_title="Infirmier",
        experience_level="JUNIOR",
        years_experience=1,
        locations=("Tunis", "Ben Arous", "Sousse"),
        contract_types=("CDI", "CDD"),
        expected_families=("healthcare",),
        expected_title_terms=("infirmier", "infirmière", "infirmiere", "nurse", "santé", "sante", "medical"),
        expected_sector_terms=("sant", "medical", "paramed"),
    ),
)


def _norm(value: Any) -> str:
    return " ".join(str(value or "").casefold().split())


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    normalized = _norm(text)
    return any(_norm(term) in normalized for term in terms if _norm(term))


def _scenario_email(key: str) -> str:
    return f"benchmark.cv.{key}@bidwise.local"


def _setup_user(scenario: CVScenario, parsed_text: str) -> tuple[Utilisateur, ProfileResume]:
    email = _scenario_email(scenario.key)
    user, _ = Utilisateur.objects.get_or_create(
        email=email,
        defaults={
            "username": email,
            "first_name": "Benchmark",
            "last_name": scenario.key,
        },
    )
    if not user.username:
        user.username = email
        user.save(update_fields=["username"])

    profile = user.profil
    profile.prenom = "Benchmark"
    profile.nom = scenario.key
    profile.target_roles = [scenario.desired_title]
    profile.competences = []
    profile.domaines_interet = []
    profile.niveau_experience = scenario.experience_level
    profile.annees_experience = scenario.years_experience
    profile.preferred_locations = list(scenario.locations)
    profile.employment_types = list(scenario.contract_types)
    profile.opportunity_types = ["JOB"]
    profile.onboarding_completed = True
    profile.save()

    ProfileResume.objects.filter(profile=profile, is_active=True).update(is_active=False)
    resume = ProfileResume.objects.create(
        profile=profile,
        parsed_text=parsed_text,
        parsing_status=ProfileResume.ParsingStatus.SUCCEEDED,
        parsed_at=timezone.now(),
        is_active=True,
        source_type=ProfileResume.SourceType.BUILDER,
        metadata={"benchmark_key": scenario.key},
    )
    return user, resume


def _serialize_result(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item.get("id"),
        "title": item.get("title"),
        "company": item.get("company"),
        "location": item.get("location"),
        "score": item.get("match_score") or item.get("score"),
        "confidence": item.get("recommendation_confidence"),
        "reasons": item.get("reasons") or item.get("reason") or [],
        "gaps": item.get("gaps") or [],
        "evidence": item.get("evidence_summary") or {},
    }


def _evaluate(scenario: CVScenario, recommendations: list[dict[str, Any]], families: set[str]) -> dict[str, Any]:
    top5 = recommendations[:5]
    top10 = recommendations[:10]
    expected_family_ok = bool(families.intersection(set(scenario.expected_families)))
    top5_title_hits = sum(
        1 for item in top5 if _contains_any(item.get("title", ""), scenario.expected_title_terms)
    )
    top10_title_hits = sum(
        1 for item in top10 if _contains_any(item.get("title", ""), scenario.expected_title_terms)
    )
    fallback_count = sum(1 for item in top10 if float(item.get("match_score") or item.get("score") or 0.0) <= 0.0)
    cv_signal_count = sum(
        1 for item in top10 if "CV" in {str(label) for label in item.get("tags", []) or []}
        or bool((item.get("evidence_summary") or {}).get("resume_signal"))
    )

    issues = []
    if not expected_family_ok:
        issues.append("profile_family_mismatch")
    if top5_title_hits < 2:
        issues.append("weak_top5_title_relevance")
    if fallback_count:
        issues.append("fallback_in_top10")
    if not recommendations:
        issues.append("no_recommendations")

    status = "PASS"
    if "profile_family_mismatch" in issues or "no_recommendations" in issues:
        status = "FAIL"
    elif issues:
        status = "REVIEW"

    return {
        "status": status,
        "issues": issues,
        "expected_family_ok": expected_family_ok,
        "top5_title_hits": top5_title_hits,
        "top10_title_hits": top10_title_hits,
        "fallback_count_top10": fallback_count,
        "cv_signal_count_top10": cv_signal_count,
    }


class Command(BaseCommand):
    help = "Run a final CV-based recommendation benchmark over local PDF resumes."

    def add_arguments(self, parser):
        parser.add_argument("--cv-dir", default="backend/benchmark_inputs/cvs")
        parser.add_argument("--top", type=int, default=20)
        parser.add_argument("--profiles", default="", help="Comma-separated scenario keys to run.")
        parser.add_argument("--skip-llm", action="store_true", help="Disable resume LLM enrichment for a fast baseline.")
        parser.add_argument(
            "--fast-semantic",
            action="store_true",
            help="Disable heavy model/semantic ESCO mapping during resume semantic extraction.",
        )
        parser.add_argument("--skip-profile-embedding", action="store_true", help="Skip JobBERT profile embedding refresh.")
        parser.add_argument("--output-json", default="")
        parser.add_argument("--json", action="store_true")
        parser.add_argument("--trace", action="store_true", help="Print per-step timings while auditing.")
        parser.add_argument("--trace-file", default="", help="Write per-step timings to this file.")

    def handle(self, *args, **options):
        if options.get("trace"):
            print("[cv-audit] command started", file=sys.stderr, flush=True)
        cv_dir = Path(str(options.get("cv_dir") or "")).resolve()
        if not cv_dir.exists():
            raise CommandError(f"CV directory not found: {cv_dir}")

        top_n = max(1, min(int(options.get("top") or 20), 50))
        selected_keys = {
            key.strip()
            for key in str(options.get("profiles") or "").split(",")
            if key.strip()
        }
        scenarios = [scenario for scenario in SCENARIOS if not selected_keys or scenario.key in selected_keys]
        if selected_keys and len(scenarios) != len(selected_keys):
            known = {scenario.key for scenario in SCENARIOS}
            missing = sorted(selected_keys - known)
            raise CommandError(f"Unknown scenario keys: {', '.join(missing)}")
        factory = APIRequestFactory()
        rows = []
        counters = {"PASS": 0, "REVIEW": 0, "FAIL": 0}
        output_json = str(options.get("output_json") or "").strip()
        out_path = Path(output_json) if output_json else None
        trace_enabled = bool(options.get("trace"))
        trace_path = Path(str(options.get("trace_file") or "")) if options.get("trace_file") else None

        def trace(message: str, step_started=None) -> None:
            if not trace_enabled and not trace_path:
                return
            suffix = ""
            if step_started is not None:
                suffix = f" ({round((timezone.now() - step_started).total_seconds(), 3)}s)"
            line = f"[cv-audit] {timezone.now().isoformat()} {message}{suffix}"
            if trace_enabled:
                self.stderr.write(line)
            if trace_path:
                trace_path.parent.mkdir(parents=True, exist_ok=True)
                with trace_path.open("a", encoding="utf-8") as handle:
                    handle.write(f"{line}\n")

        def write_partial() -> None:
            if not out_path:
                return
            payload = {
                "generated_at": timezone.now().isoformat(),
                "cv_dir": str(cv_dir),
                "summary": {
                    "scenario_count": len(rows),
                    **counters,
                },
                "rows": rows,
            }
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

        for scenario in scenarios:
            started = timezone.now()
            path = cv_dir / scenario.filename
            if not path.exists():
                row = {
                    "key": scenario.key,
                    "label": scenario.desired_title,
                    "status": "FAIL",
                    "issues": ["missing_cv_file"],
                    "cv_file": str(path),
                }
                rows.append(row)
                counters["FAIL"] += 1
                write_partial()
                continue

            trace(f"{scenario.key}: parsing {path.name}")
            step_started = timezone.now()
            with path.open("rb") as handle:
                parsed = parse_resume_file(File(handle, name=path.name), filename=path.name)
            trace(f"{scenario.key}: parsed chars={len(parsed.text)} parser={parsed.parser}", step_started)

            step_started = timezone.now()
            user, resume = _setup_user(scenario, parsed.text)
            trace(f"{scenario.key}: benchmark user/profile ready user_id={user.id} profile_id={user.profil.id}", step_started)

            step_started = timezone.now()
            semantic_kwargs = {
                "force": True,
                "use_model": not options.get("fast_semantic"),
                "allow_semantic_mapping": not options.get("fast_semantic"),
            }
            if options.get("skip_llm"):
                with override_settings(LLM_ENRICHMENT_ENABLED=False):
                    semantic = process_profile_resume_semantics(resume, **semantic_kwargs)
            else:
                semantic = process_profile_resume_semantics(resume, **semantic_kwargs)
            trace(f"{scenario.key}: semantic status={semantic.get('status')}", step_started)

            embedding_result = {"status": "skipped", "reason": "skip_profile_embedding"}
            if not options.get("skip_profile_embedding"):
                from users.tasks import generate_profile_embedding

                step_started = timezone.now()
                embedding_result = generate_profile_embedding(user.profil.id)
                trace(f"{scenario.key}: profile embedding {embedding_result}", step_started)

            step_started = timezone.now()
            features = build_user_features(user.profil)
            families = profile_business_families(features)
            trace(f"{scenario.key}: features families={sorted(families)}", step_started)

            step_started = timezone.now()
            request = factory.get(f"/api/recommendations/?limit={top_n}")
            request.user = user
            from ai.views import recommendations_view

            response = recommendations_view(request)
            recommendations = list(response.data or [])
            trace(f"{scenario.key}: recommendations count={len(recommendations)}", step_started)
            evaluation = _evaluate(scenario, recommendations, families)
            counters[evaluation["status"]] += 1

            rows.append(
                {
                    "key": scenario.key,
                    "label": scenario.desired_title,
                    "cv_file": str(path),
                    "parsed_chars": len(parsed.text),
                    "parser": parsed.parser,
                    "semantic_status": semantic.get("status"),
                    "semantic_confidence": semantic.get("semantic_confidence"),
                    "semantic_skills": semantic.get("skills", []),
                    "semantic_domains": semantic.get("domains", []),
                    "profile_embedding": embedding_result,
                    "profile_business_families": sorted(families),
                    "expected_families": list(scenario.expected_families),
                    "duration_seconds": round((timezone.now() - started).total_seconds(), 3),
                    **evaluation,
                    "top_results": [_serialize_result(item) for item in recommendations[:top_n]],
                }
            )
            write_partial()

        payload = {
            "generated_at": timezone.now().isoformat(),
            "cv_dir": str(cv_dir),
            "summary": {
                "scenario_count": len(rows),
                **counters,
            },
            "rows": rows,
        }

        if out_path:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

        if options.get("json"):
            self.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2))
            return

        self.stdout.write("CV recommendation benchmark")
        self.stdout.write(json.dumps(payload["summary"], ensure_ascii=False, indent=2))
        for row in rows:
            self.stdout.write(
                f"[{row['status']}] {row['key']} families={row.get('profile_business_families')} "
                f"top5_hits={row.get('top5_title_hits')} issues={row.get('issues')}"
            )
            for item in row.get("top_results", [])[:5]:
                self.stdout.write(f"  - {item['score']}: {item['title']} ({item['company']})")
