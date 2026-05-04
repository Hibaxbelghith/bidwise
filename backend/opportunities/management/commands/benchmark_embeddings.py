import logging
import math

from django.core.management.base import BaseCommand, CommandError

from opportunities.embeddings import service
from opportunities.models import Opportunite, TypeOpportunite
from opportunities.nlp.nlp_preprocessing import prepare_combined_text


logger = logging.getLogger(__name__)

BENCHMARK_QUERIES = [
    {"query": "data engineer python sql", "expected_types": {TypeOpportunite.EMPLOI, TypeOpportunite.STAGE}},
    {"query": "stage developpeur web", "expected_types": {TypeOpportunite.STAGE}},
    {"query": "appel d offres consultation", "expected_types": {TypeOpportunite.PROJET, TypeOpportunite.FINANCEMENT}},
    {"query": "financement projet innovation", "expected_types": {TypeOpportunite.FINANCEMENT, TypeOpportunite.PROJET}},
    {"query": "research assistant opportunity", "expected_types": {TypeOpportunite.RECHERCHE, TypeOpportunite.STAGE}},
]


def _dot_similarity(vec_a, vec_b):
    dot = float(sum(a * b for a, b in zip(vec_a, vec_b)))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def _average(values):
    if not values:
        return 0.0
    return float(sum(values) / len(values))


def _top_k_indices(scores, top_k):
    ranked = sorted(range(len(scores)), key=lambda index: scores[index], reverse=True)
    return ranked[:top_k]


class Command(BaseCommand):
    help = "Benchmark multiple embedding models on a real opportunities sample."

    def add_arguments(self, parser):
        parser.add_argument(
            "--models",
            default=",".join(sorted(service.EMBEDDING_MODELS)),
            help="Comma-separated model names to compare.",
        )
        parser.add_argument(
            "--sample-size",
            type=int,
            default=200,
            help="Number of opportunities used for benchmark.",
        )
        parser.add_argument(
            "--top-k",
            type=int,
            default=5,
            help="Top-k used for relevance heuristic.",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=32,
            help="Batch size for encoding.",
        )

    def handle(self, *args, **options):
        raw_models = [m.strip() for m in options["models"].split(",") if m.strip()]
        if not raw_models:
            raise CommandError("No models provided.")

        selected_models = []
        for model_name in raw_models:
            try:
                selected_models.append(service.resolve_model_name(model_name))
            except ValueError as exc:
                raise CommandError(str(exc))

        sample_size = max(1, int(options["sample_size"]))
        top_k = max(1, int(options["top_k"]))
        batch_size = max(1, int(options["batch_size"]))

        rows = list(
            Opportunite.objects.exclude(description="")
            .exclude(titre="")
            .order_by("-date_publication", "-id")[:sample_size]
        )
        if len(rows) < top_k:
            raise CommandError(f"Not enough records for benchmark. Need at least {top_k}, found {len(rows)}.")

        texts = [prepare_combined_text(row) for row in rows]
        types = [row.type_opportunite for row in rows]
        organizations = [row.organisation_nom or "" for row in rows]

        valid_indices = [i for i, text in enumerate(texts) if text]
        if len(valid_indices) < top_k:
            raise CommandError(
                f"Not enough non-empty NLP texts for benchmark. Need at least {top_k}, found {len(valid_indices)}."
            )

        texts = [texts[i] for i in valid_indices]
        types = [types[i] for i in valid_indices]
        organizations = [organizations[i] for i in valid_indices]

        results = []

        self.stdout.write(f"Benchmark sample size: {len(texts)}")
        self.stdout.write(f"Models: {', '.join(selected_models)}")

        for model_name in selected_models:
            self.stdout.write(f"\nRunning benchmark for model: {model_name}")
            try:
                doc_vectors = service.generate_embeddings_batch(
                    texts, model_name=model_name, batch_size=batch_size
                )
                query_vectors = service.generate_embeddings_batch(
                    [item["query"] for item in BENCHMARK_QUERIES],
                    model_name=model_name,
                    batch_size=batch_size,
                )
            except Exception as exc:  # noqa: BLE001 - continue with other models
                logger.exception("Benchmark failed for model %s: %s", model_name, exc)
                self.stdout.write(self.style.WARNING(f"Failed model {model_name}: {exc}"))
                continue

            top_k_precision_scores = []
            for query_vector, query_def in zip(query_vectors, BENCHMARK_QUERIES):
                similarities = [_dot_similarity(query_vector, doc_vector) for doc_vector in doc_vectors]
                indices = _top_k_indices(similarities, top_k=top_k)
                hits = sum(1 for idx in indices if types[idx] in query_def["expected_types"])
                top_k_precision_scores.append(hits / top_k)

            same_org_scores = []
            org_first_seen = {}
            for idx, org in enumerate(organizations):
                if not org:
                    continue
                if org not in org_first_seen:
                    org_first_seen[org] = idx
                    continue
                first_idx = org_first_seen[org]
                same_org_scores.append(_dot_similarity(doc_vectors[first_idx], doc_vectors[idx]))

            nn_scores = []
            for i, current_vector in enumerate(doc_vectors):
                similarities = [
                    _dot_similarity(current_vector, other_vector)
                    for j, other_vector in enumerate(doc_vectors)
                    if i != j
                ]
                if similarities:
                    nn_scores.append(max(similarities))

            relevance = _average(top_k_precision_scores)
            org_consistency = _average(same_org_scores)
            neighborhood_consistency = _average(nn_scores)

            aggregate_score = (0.6 * relevance) + (0.3 * org_consistency) + (0.1 * neighborhood_consistency)
            model_result = {
                "model": model_name,
                "relevance": relevance,
                "org_consistency": org_consistency,
                "nn_consistency": neighborhood_consistency,
                "score": aggregate_score,
            }
            results.append(model_result)

            self.stdout.write(
                "  relevance@k={:.3f} | same_org={:.3f} | nn_consistency={:.3f} | score={:.3f}".format(
                    relevance,
                    org_consistency,
                    neighborhood_consistency,
                    aggregate_score,
                )
            )

        if not results:
            raise CommandError("Benchmark failed for all models.")

        ranked = sorted(results, key=lambda item: item["score"], reverse=True)
        winner = ranked[0]

        self.stdout.write("\nBenchmark Summary")
        self.stdout.write("-" * 60)
        for row in ranked:
            self.stdout.write(
                "{} -> score={:.3f} (relevance={:.3f}, same_org={:.3f}, nn={:.3f})".format(
                    row["model"],
                    row["score"],
                    row["relevance"],
                    row["org_consistency"],
                    row["nn_consistency"],
                )
            )

        self.stdout.write(self.style.SUCCESS(f"\nBest model: {winner['model']}"))
