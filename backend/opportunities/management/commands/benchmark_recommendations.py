from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand

from ai.recommendation_benchmark.runner import (
    BenchmarkRunOptions,
    RecommendationBenchmarkRunner,
    format_console_report,
)


class Command(BaseCommand):
    help = "Run the internal BidWise recommendation quality benchmark."

    def add_arguments(self, parser):
        parser.add_argument(
            "--top-k",
            type=int,
            default=None,
            help="Recommendation cutoff for Precision@K/Recall@K. Defaults to benchmark_config.DEFAULT_TOP_K.",
        )
        parser.add_argument(
            "--rebuild-embeddings",
            action="store_true",
            help="Regenerate benchmark fixture embeddings with the current embedding model.",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=32,
            help="Batch size for benchmark opportunity embedding generation.",
        )
        parser.add_argument(
            "--output-dir",
            default=None,
            help="Directory for the machine-readable JSON report.",
        )
        parser.add_argument(
            "--no-write-report",
            action="store_true",
            help="Print the console report without writing JSON.",
        )
        parser.add_argument(
            "--no-crossencoder-comparison",
            action="store_true",
            help="Skip the baseline vs CrossEncoder comparison pass.",
        )

    def handle(self, *args, **options):
        runner = RecommendationBenchmarkRunner()
        top_k = options.get("top_k") or runner.dataset.default_top_k
        run_options = BenchmarkRunOptions(
            top_k=max(1, int(top_k)),
            rebuild_embeddings=bool(options.get("rebuild_embeddings")),
            batch_size=max(1, int(options.get("batch_size") or 32)),
            write_report=not bool(options.get("no_write_report")),
            output_dir=Path(options["output_dir"]) if options.get("output_dir") else None,
            crossencoder_comparison=not bool(options.get("no_crossencoder_comparison")),
        )
        report = runner.run(run_options)
        self.stdout.write(format_console_report(report))
