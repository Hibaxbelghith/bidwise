from __future__ import annotations

import json
from collections import Counter
from statistics import mean
from typing import Any

from django.core.management.base import BaseCommand
from django.db.models import Count, Q
from django.db.models.functions import Length

from ai.jobbert import jobbert_model_name
from opportunities.models import Opportunite, StatutOpportunite
from opportunities.nlp.nlp_preprocessing import prepare_combined_text


def _pct(part: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(part * 100 / total, 1)


def _has_llm_enrichment(opportunity: Opportunite) -> bool:
    extra_data = getattr(opportunity, "extra_data", None)
    return isinstance(extra_data, dict) and isinstance(extra_data.get("llm_enrichment"), dict)


def _llm_data(opportunity: Opportunite) -> dict[str, Any]:
    extra_data = getattr(opportunity, "extra_data", None)
    if not isinstance(extra_data, dict):
        return {}
    value = extra_data.get("llm_enrichment")
    return value if isinstance(value, dict) else {}


def _list_len(value: Any) -> int:
    return len(value) if isinstance(value, list) else 0


def _source_label(value: Any) -> str:
    return str(value or "Unknown").strip() or "Unknown"


class Command(BaseCommand):
    help = "Audit data readiness for Ollama enrichment, JobBERT matching, and recommendation quality."

    def add_arguments(self, parser):
        parser.add_argument("--source", default="all", help="Source name to audit, or 'all'.")
        parser.add_argument("--sample-size", type=int, default=80, help="Rows sampled per source for deeper metrics.")
        parser.add_argument("--examples", type=int, default=5, help="Weak candidate examples per source.")
        parser.add_argument("--json", action="store_true")

    def handle(self, *args, **options):
        source_filter = str(options.get("source") or "all").strip()
        sample_size = max(10, min(int(options.get("sample_size") or 80), 500))
        example_count = max(0, min(int(options.get("examples") or 5), 20))
        model_name = jobbert_model_name()

        base = (
            Opportunite.objects.filter(statut=StatutOpportunite.ACTIVE)
            .select_related("source")
            .annotate(description_length=Length("description"))
        )
        if source_filter.casefold() != "all":
            base = base.filter(source__nom__iexact=source_filter)

        total = base.count()
        source_rows = (
            base.values("source__nom")
            .annotate(total=Count("id"))
            .order_by("-total", "source__nom")
        )

        sources = []
        for row in source_rows:
            source_name = _source_label(row["source__nom"])
            qs = base.filter(source__nom=source_name)
            count = int(row["total"])
            if count <= 0:
                continue

            aggregate = {
                "active": count,
                "with_description": qs.exclude(description="").count(),
                "long_description_300": qs.filter(description_length__gte=300).count(),
                "very_long_description_3000": qs.filter(description_length__gte=3000).count(),
                "with_structured_skills": qs.exclude(skills=[]).count(),
                "with_raw_skills": qs.exclude(raw_skills=[]).count(),
                "with_normalized_skills": qs.exclude(normalized_skills=[]).count(),
                "with_location": qs.exclude(ville="").count(),
                "with_contract": qs.exclude(contract_type="").count(),
                "with_experience": qs.filter(Q(experience_min__isnull=False) | Q(experience_max__isnull=False)).count(),
                "with_education": qs.exclude(education_level="").count(),
                "with_languages": qs.filter(Q(languages__len__gt=0) | Q(languages_fallback__len__gt=0)).count(),
                "llm_enriched": qs.filter(extra_data__llm_enrichment__isnull=False).count(),
                "jobbert_embedded": qs.filter(
                    jobbert_embedding_vector__isnull=False,
                    jobbert_embedding_model=model_name,
                ).count(),
            }

            sample = list(
                qs.only(
                    "id",
                    "titre",
                    "description",
                    "ville",
                    "contract_type",
                    "experience_min",
                    "experience_max",
                    "education_level",
                    "skills",
                    "raw_skills",
                    "normalized_skills",
                    "extra_data",
                    "jobbert_embedding_vector",
                    "jobbert_embedding_model",
                    "source__nom",
                )
                .order_by("-date_publication", "-id")[:sample_size]
            )

            semantic_lengths = []
            llm_family_counts: Counter[str] = Counter()
            llm_quality = Counter()
            for opportunity in sample:
                semantic_text = " ".join(prepare_combined_text(opportunity).split())
                if semantic_text:
                    semantic_lengths.append(len(semantic_text))
                llm = _llm_data(opportunity)
                if llm:
                    for family in llm.get("business_families") or []:
                        llm_family_counts[str(family)] += 1
                    if _list_len(llm.get("responsibilities")):
                        llm_quality["with_responsibilities"] += 1
                    if _list_len(llm.get("requirements")):
                        llm_quality["with_requirements"] += 1
                    if _list_len(llm.get("skills")) or _list_len(llm.get("tools")):
                        llm_quality["with_skills_or_tools"] += 1
                    if _list_len(llm.get("soft_skills")):
                        llm_quality["with_soft_skills"] += 1
                    if llm.get("applied_to_skills"):
                        llm_quality["applied_to_skills"] += 1

            weak_examples = []
            for opportunity in qs.filter(description_length__gte=300).order_by("-date_publication", "-id")[:80]:
                skills_count = len(getattr(opportunity, "skills", []) or [])
                if skills_count > 1 and _has_llm_enrichment(opportunity):
                    continue
                weak_examples.append(
                    {
                        "id": opportunity.id,
                        "title": opportunity.titre,
                        "description_length": int(getattr(opportunity, "description_length", 0) or 0),
                        "skills_count": skills_count,
                        "llm_enriched": _has_llm_enrichment(opportunity),
                    }
                )
                if len(weak_examples) >= example_count:
                    break

            sources.append(
                {
                    "source": source_name,
                    "counts": aggregate,
                    "coverage_pct": {
                        "structured_skills": _pct(aggregate["with_structured_skills"], count),
                        "normalized_skills": _pct(aggregate["with_normalized_skills"], count),
                        "location": _pct(aggregate["with_location"], count),
                        "contract": _pct(aggregate["with_contract"], count),
                        "experience": _pct(aggregate["with_experience"], count),
                        "education": _pct(aggregate["with_education"], count),
                        "llm_enriched": _pct(aggregate["llm_enriched"], count),
                        "jobbert_embedded": _pct(aggregate["jobbert_embedded"], count),
                        "long_description_300": _pct(aggregate["long_description_300"], count),
                    },
                    "sample": {
                        "size": len(sample),
                        "semantic_text_avg_chars": round(mean(semantic_lengths), 1) if semantic_lengths else 0.0,
                        "semantic_text_max_chars": max(semantic_lengths) if semantic_lengths else 0,
                        "llm_quality_counts": dict(llm_quality),
                        "llm_families_top": llm_family_counts.most_common(8),
                    },
                    "next_weak_examples": weak_examples,
                }
            )

        payload = {
            "scope": {
                "source": source_filter,
                "active_total": total,
                "jobbert_model": model_name,
                "sample_size_per_source": sample_size,
            },
            "sources": sources,
            "recommendations": [
                "Use Ollama/Gemini first on sources with long descriptions but weak structured skills.",
                "Generate JobBERT embeddings after enrichment; missing embeddings mean recommendations use poorer candidate pools.",
                "Inspect sources with low location/experience/contract coverage before adding hard pre-filters.",
                "Keep --no-apply-skills for local Ollama batches unless normalized skill support is strong.",
            ],
        }

        if options.get("json"):
            self.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2))
            return

        self.stdout.write(f"AI recommendation readiness: active_total={total} jobbert_model={model_name}")
        for item in sources:
            counts = item["counts"]
            coverage = item["coverage_pct"]
            self.stdout.write(f"\n{item['source']} ({counts['active']} active)")
            self.stdout.write(
                "  coverage: "
                f"skills={coverage['structured_skills']}% "
                f"normalized={coverage['normalized_skills']}% "
                f"llm={coverage['llm_enriched']}% "
                f"jobbert={coverage['jobbert_embedded']}% "
                f"location={coverage['location']}% "
                f"experience={coverage['experience']}%"
            )
            self.stdout.write(
                "  semantic text sample: "
                f"avg={item['sample']['semantic_text_avg_chars']} chars "
                f"max={item['sample']['semantic_text_max_chars']} chars"
            )
            if item["next_weak_examples"]:
                self.stdout.write("  next weak examples:")
                for example in item["next_weak_examples"]:
                    self.stdout.write(
                        f"    [{example['id']}] {example['title']} "
                        f"desc={example['description_length']} skills={example['skills_count']} "
                        f"llm={example['llm_enriched']}"
                    )
