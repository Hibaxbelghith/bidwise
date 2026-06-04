import json
import statistics
import time
from datetime import date, timedelta

from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIRequestFactory

from opportunities.models import Opportunite, SourceOpportunite, StatutOpportunite, TypeOpportunite
from opportunities.views import OpportuniteViewSet


class Command(BaseCommand):
    help = "Benchmark opportunity filtering, faceting, search, and pagination through the DRF view."

    def add_arguments(self, parser):
        parser.add_argument("--synthetic-size", type=int, default=0)
        parser.add_argument("--iterations", type=int, default=3)
        parser.add_argument("--json", action="store_true")
        parser.add_argument("--preserve-cache", action="store_true")

    def handle(self, *args, **options):
        synthetic_size = max(0, int(options["synthetic_size"]))
        iterations = max(1, int(options["iterations"]))
        preserve_cache = bool(options["preserve_cache"])

        if synthetic_size:
            self._ensure_synthetic_dataset(synthetic_size)

        scenarios = [
            ("baseline_quality", {"page": 1, "page_size": 20, "sort": "quality"}),
            ("newest_page_3", {"page": 3, "page_size": 20, "sort": "newest"}),
            ("job_remote_tunis", {"type": "EMPLOI", "work_mode": "REMOTE", "location": "Tunis"}),
            ("search_python", {"search": "python", "page_size": 20, "sort": "relevance"}),
            ("facets_job", {"type": "EMPLOI", "page_size": 1}),
        ]

        results = []
        for name, params in scenarios:
            timings = []
            query_counts = []
            for _iteration in range(iterations):
                if not preserve_cache:
                    cache.clear()
                elapsed_ms, query_count, count = self._run_list_request(params)
                timings.append(elapsed_ms)
                query_counts.append(query_count)

            results.append(
                {
                    "scenario": name,
                    "params": params,
                    "count": count,
                    "avg_ms": round(statistics.mean(timings), 2),
                    "worst_ms": round(max(timings), 2),
                    "avg_queries": round(statistics.mean(query_counts), 2),
                    "worst_queries": max(query_counts),
                }
            )

        if options["json"]:
            self.stdout.write(
                json.dumps(
                    {
                        "iterations": iterations,
                        "cache_mode": "preserved" if preserve_cache else "cold_facets",
                        "results": results,
                    },
                    indent=2,
                )
            )
            return

        cache_mode = "preserved" if preserve_cache else "cold_facets"
        self.stdout.write(f"Opportunity search benchmark, iterations={iterations}, cache={cache_mode}")
        for item in results:
            self.stdout.write(
                "{scenario}: count={count} avg={avg_ms}ms worst={worst_ms}ms "
                "avg_queries={avg_queries} worst_queries={worst_queries}".format(**item)
            )

    def _run_list_request(self, params):
        factory = APIRequestFactory()
        request = factory.get("/api/opportunities/", params)
        view = OpportuniteViewSet.as_view({"get": "list"})

        started_at = time.perf_counter()
        with CaptureQueriesContext(connection) as captured:
            response = view(request)
            response.render()
        elapsed_ms = (time.perf_counter() - started_at) * 1000

        if response.status_code >= 400:
            raise RuntimeError(f"Benchmark request failed: {response.status_code} {response.data}")

        return elapsed_ms, len(captured), int(response.data.get("count") or 0)

    def _ensure_synthetic_dataset(self, target_size):
        source, _created = SourceOpportunite.objects.get_or_create(
            nom="BenchmarkSearch",
            defaults={
                "url": "https://benchmark.local/opportunities",
                "type_source": "SITE_EMPLOI",
            },
        )
        existing = Opportunite.objects.filter(source=source, external_id__startswith="benchmark-search-").count()
        missing = max(0, target_size - existing)
        if missing == 0:
            self.stdout.write(f"Synthetic benchmark dataset already has {existing} rows.")
            return

        types = [
            TypeOpportunite.EMPLOI,
            TypeOpportunite.STAGE,
            TypeOpportunite.PROJET,
        ]
        cities = ["Tunis", "Sfax", "Sousse", "Ariana", "Remote"]
        work_modes = ["REMOTE", "HYBRID", "ON_SITE", "UNSPECIFIED"]
        skills = ["Python", "Django", "React", "SQL", "Data", "Finance"]
        today = date.today()
        batch = []

        for index in range(existing, existing + missing):
            skill = skills[index % len(skills)]
            batch.append(
                Opportunite(
                    titre=f"{skill} Opportunity {index}",
                    description=f"{skill} role with APIs, reporting, and multi-source delivery.",
                    organisation_nom=f"Benchmark Company {index % 20}",
                    ville=cities[index % len(cities)],
                    type_opportunite=types[index % len(types)],
                    statut=StatutOpportunite.ACTIVE if index % 9 else StatutOpportunite.EXPIREE,
                    date_publication=today - timedelta(days=index % 90),
                    date_limite=today + timedelta(days=10 + (index % 45)),
                    source=source,
                    external_id=f"benchmark-search-{index}",
                    quality_score=(index % 100) / 100,
                    normalized_work_mode=work_modes[index % len(work_modes)],
                    experience_min=index % 8,
                    experience_max=(index % 8) + 2,
                    skills=[skill.lower()],
                )
            )
            if len(batch) >= 1000:
                Opportunite.objects.bulk_create(batch, batch_size=1000)
                batch.clear()

        if batch:
            Opportunite.objects.bulk_create(batch, batch_size=1000)

        self.stdout.write(f"Created {missing} synthetic benchmark opportunities.")
