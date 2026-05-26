from __future__ import annotations

import json
import time

from django.core.management.base import BaseCommand, CommandError

from ai.llm import enrich_opportunity_text, enrich_resume_text, get_llm_provider
from ai.llm.providers import LLMProviderError, LLMProviderUnavailable, LLMRateLimitError
from opportunities.models import Opportunite, StatutOpportunite
from users.models import ProfileResume


class Command(BaseCommand):
    help = "Benchmark Gemini structured extraction on recent resumes or opportunities without writing results."

    def add_arguments(self, parser):
        parser.add_argument(
            "--target",
            choices=["resumes", "opportunities"],
            required=True,
            help="Entity type to enrich.",
        )
        parser.add_argument("--limit", type=int, default=5, help="Maximum rows to inspect.")
        parser.add_argument("--from-id", type=int, default=None, help="Optional primary-key lower bound.")
        parser.add_argument(
            "--delay-seconds",
            type=float,
            default=12.0,
            help="Delay between LLM calls to respect free-tier rate limits.",
        )
        parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")

    def handle(self, *args, **options):
        limit = max(1, min(int(options["limit"] or 5), 25))
        from_id = options.get("from_id")
        if from_id is not None and int(from_id) < 0:
            raise CommandError("--from-id must be >= 0")

        provider = get_llm_provider()
        rows = self._load_rows(str(options["target"]), limit=limit, from_id=from_id)
        results = []
        delay_seconds = max(0.0, float(options["delay_seconds"] or 0.0))

        for index, row in enumerate(rows):
            if index > 0 and delay_seconds:
                time.sleep(delay_seconds)
            try:
                if options["target"] == "resumes":
                    text = getattr(row, "parsed_text", "") or getattr(row, "resume_text_embedding_source", "")
                    extraction = enrich_resume_text(text, provider=provider)
                    title = f"resume:{row.pk}"
                else:
                    extraction = enrich_opportunity_text(row, provider=provider)
                    title = getattr(row, "titre", "") or f"opportunity:{row.pk}"
            except LLMProviderUnavailable as exc:
                raise CommandError(str(exc)) from exc
            except LLMRateLimitError as exc:
                results.append(
                    {
                        "id": row.pk,
                        "title": getattr(row, "titre", "") or f"{options['target']}:{row.pk}",
                        "error": str(exc),
                    }
                )
                break
            except LLMProviderError as exc:
                results.append(
                    {
                        "id": row.pk,
                        "title": getattr(row, "titre", "") or f"{options['target']}:{row.pk}",
                        "error": str(exc),
                    }
                )
                continue

            payload = {
                "id": row.pk,
                "title": title,
                "extraction": extraction.as_dict(),
            }
            results.append(payload)

        if bool(options["json"]):
            self.stdout.write(json.dumps(results, ensure_ascii=False, indent=2))
            return

        self.stdout.write(self.style.SUCCESS(f"Gemini enrichment benchmark: {options['target']}"))
        for item in results:
            if item.get("error"):
                self.stdout.write(f"[{item['id']}] {item['title']}")
                self.stdout.write(f"  error: {item['error']}")
                continue
            extraction = item["extraction"]
            self.stdout.write(f"[{item['id']}] {item['title']}")
            self.stdout.write(f"  roles: {', '.join(extraction['target_roles'][:5]) or '-'}")
            self.stdout.write(f"  families: {', '.join(extraction['business_families']) or '-'}")
            self.stdout.write(f"  skills: {', '.join(extraction['skills'][:8]) or '-'}")
            self.stdout.write(f"  tools: {', '.join(extraction['tools'][:8]) or '-'}")
            self.stdout.write(f"  confidence: {extraction['confidence']}")

    def _load_rows(self, target: str, *, limit: int, from_id: int | None):
        if target == "resumes":
            queryset = (
                ProfileResume.objects.filter(is_active=True)
                .exclude(parsed_text="")
                .only("id", "parsed_text", "resume_text_embedding_source")
                .order_by("-uploaded_at", "-id")
            )
        else:
            queryset = (
                Opportunite.objects.filter(statut=StatutOpportunite.ACTIVE)
                .only(
                    "id",
                    "titre",
                    "description",
                    "organisation_nom",
                    "ville",
                    "contract_type",
                    "availability",
                    "skills",
                )
                .order_by("-date_publication", "-id")
            )
        if from_id is not None:
            queryset = queryset.filter(id__gte=int(from_id))
        return list(queryset[:limit])
