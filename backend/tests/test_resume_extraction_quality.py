from __future__ import annotations

import json
from io import StringIO
from pathlib import Path

from django.core.management import call_command
from django.test import SimpleTestCase


class ResumeExtractionQualityBenchmarkTests(SimpleTestCase):
    def test_real_resume_fixtures_meet_keyword_expectations(self):
        backend_dir = Path(__file__).resolve().parent.parent
        resume_dir = backend_dir / "benchmark_inputs" / "cvs"
        expectations_path = (
            backend_dir
            / "tests"
            / "recommendation_benchmark"
            / "resumes"
            / "cv_extraction_expectations.json"
        )

        stdout = StringIO()
        call_command(
            "benchmark_resume_extraction_quality",
            str(resume_dir),
            "--expectations",
            str(expectations_path),
            "--fail-under-average-recall",
            "0.95",
            "--fail-on-fixture-failure",
            "--json",
            stdout=stdout,
        )

        payload = json.loads(stdout.getvalue())
        summary = payload["summary"]
        rows_by_file = {row["file"]: row for row in payload["rows"]}

        self.assertEqual(summary["total_files"], 10)
        self.assertEqual(summary["parsed_success_count"], 10)
        self.assertEqual(summary["parsed_failure_count"], 0)
        self.assertEqual(summary["failed_files"], [])
        self.assertEqual(summary["parser_distribution"], {"pymupdf": 10})
        self.assertGreaterEqual(summary["average_keyword_recall"], 0.95)

        self.assertEqual(
            rows_by_file["cv_developpeur_backend.pdf"]["matched_keywords"],
            ["developpeuse backend", "apis rest", "django"],
        )
        self.assertEqual(
            rows_by_file["cv_devops_engineer.pdf"]["matched_keywords"],
            ["devops engineer", "docker", "kubernetes"],
        )
        self.assertGreaterEqual(rows_by_file["cv_infirmier.pdf"]["text_chars"], 500)
