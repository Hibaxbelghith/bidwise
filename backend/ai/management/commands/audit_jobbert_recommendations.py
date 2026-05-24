from __future__ import annotations

import json
import math
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from opportunities.models import Opportunite, StatutOpportunite
from opportunities.nlp.nlp_preprocessing import prepare_combined_text


DEFAULT_JOBBERT_MODEL = "TechWolf/JobBERT-v3"
DEFAULT_PROFILE_TEXT = (
    "Role: Technicien méthodes. Skills: amélioration continue, procédés industriels, "
    "gammes de fabrication, chronométrage, qualité, production, Lean manufacturing. "
    "Experience: junior. Location: Sousse or Tunis. Work mode: on-site."
)


def _clean_text(value: str, max_chars: int) -> str:
    text = " ".join(str(value or "").split())
    if max_chars > 0 and len(text) > max_chars:
        return text[:max_chars].rstrip()
    return text


def _dot(left, right) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    score = 0.0
    for left_value, right_value in zip(left, right):
        try:
            score += float(left_value) * float(right_value)
        except (TypeError, ValueError):
            return 0.0
    if not math.isfinite(score):
        return 0.0
    return score


def _load_sentence_transformer(model_name: str):
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:  # pragma: no cover - environment guard
        raise CommandError("sentence-transformers is required to run JobBERT audit.") from exc
    return SentenceTransformer(model_name, device="cpu")


class Command(BaseCommand):
    help = (
        "Audit local job-domain semantic matching with TechWolf/JobBERT-v3. "
        "This is non-destructive and does not write embeddings to the database."
    )

    def add_arguments(self, parser):
        parser.add_argument("--model", default=DEFAULT_JOBBERT_MODEL)
        parser.add_argument("--profile-text", default="")
        parser.add_argument("--profile-file", default="")
        parser.add_argument("--source", default="Keejob")
        parser.add_argument("--candidate-limit", type=int, default=100)
        parser.add_argument("--top", type=int, default=10)
        parser.add_argument("--max-text-chars", type=int, default=2500)
        parser.add_argument("--json", action="store_true")

    def handle(self, *args, **options):
        profile_text = str(options.get("profile_text") or "").strip()
        profile_file = str(options.get("profile_file") or "").strip()
        if profile_file:
            path = Path(profile_file)
            if not path.exists():
                raise CommandError(f"Profile file not found: {profile_file}")
            profile_text = path.read_text(encoding="utf-8").strip()
        if not profile_text:
            profile_text = DEFAULT_PROFILE_TEXT

        model_name = str(options.get("model") or DEFAULT_JOBBERT_MODEL).strip()
        source_name = str(options.get("source") or "").strip()
        candidate_limit = max(1, min(int(options.get("candidate_limit") or 100), 1000))
        top_n = max(1, min(int(options.get("top") or 10), 50))
        max_text_chars = max(500, int(options.get("max_text_chars") or 2500))

        queryset = (
            Opportunite.objects.filter(statut=StatutOpportunite.ACTIVE)
            .select_related("source")
            .only(
                "id",
                "titre",
                "description",
                "organisation_nom",
                "ville",
                "contract_type",
                "availability",
                "skills",
                "extra_data",
                "source__nom",
            )
            .order_by("-date_publication", "-id")
        )
        if source_name and source_name.casefold() != "all":
            queryset = queryset.filter(source__nom__iexact=source_name)

        candidates = []
        candidate_texts = []
        for opportunity in queryset.iterator(chunk_size=200):
            text = _clean_text(prepare_combined_text(opportunity), max_text_chars)
            if not text:
                continue
            candidates.append(opportunity)
            candidate_texts.append(text)
            if len(candidates) >= candidate_limit:
                break

        if not candidates:
            raise CommandError("No candidates found for JobBERT audit.")

        model = _load_sentence_transformer(model_name)
        encoded = model.encode(
            [_clean_text(profile_text, max_text_chars), *candidate_texts],
            batch_size=16,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        profile_vector = encoded[0].tolist()
        candidate_vectors = [vector.tolist() for vector in encoded[1:]]

        rows = []
        for opportunity, vector in zip(candidates, candidate_vectors):
            source = getattr(getattr(opportunity, "source", None), "nom", "") or ""
            rows.append(
                {
                    "id": opportunity.pk,
                    "title": opportunity.titre,
                    "company": opportunity.organisation_nom,
                    "location": opportunity.ville,
                    "source": source,
                    "skills": list(opportunity.skills or [])[:8],
                    "score": round(_dot(profile_vector, vector), 4),
                }
            )
        rows.sort(key=lambda item: item["score"], reverse=True)
        rows = rows[:top_n]

        payload = {
            "model": model_name,
            "profile_text": _clean_text(profile_text, 1000),
            "source": source_name or "all",
            "candidate_count": len(candidates),
            "top": rows,
        }
        if bool(options.get("json")):
            self.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2))
            return

        self.stdout.write(self.style.SUCCESS(f"JobBERT audit model={model_name} candidates={len(candidates)}"))
        for index, row in enumerate(rows, start=1):
            self.stdout.write(
                f"{index}. {row['score']:.4f} | {row['title']} | {row['company']} | "
                f"{row['location']} | {row['source']}"
            )
            if row["skills"]:
                self.stdout.write(f"   skills: {', '.join(row['skills'])}")
