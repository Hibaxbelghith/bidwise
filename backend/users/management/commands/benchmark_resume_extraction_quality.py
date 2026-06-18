from __future__ import annotations

import json
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from users.resume_parsing.service import parse_resume_file


def _base_dir() -> Path:
    configured = getattr(settings, "BASE_DIR", None)
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[4]


def _normalize_lookup_text(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.casefold()
    cleaned = []
    for char in text:
        cleaned.append(char if char.isalnum() else " ")
    return " ".join("".join(cleaned).split())


def _resolve_path(raw_path: str | None, *, default: Path) -> Path:
    if raw_path:
        candidate = Path(raw_path)
        if candidate.exists():
            return candidate
        repo_candidate = _base_dir() / raw_path
        if repo_candidate.exists():
            return repo_candidate
        return candidate
    return default


class Command(BaseCommand):
    help = "Evaluate real CV extraction quality on benchmark PDF/DOCX fixtures."

    def add_arguments(self, parser):
        parser.add_argument(
            "resume_dir",
            nargs="?",
            default=None,
            help="Directory containing benchmark CV files. Defaults to backend/benchmark_inputs/cvs.",
        )
        parser.add_argument(
            "--expectations",
            default=None,
            help=(
                "JSON file containing expected parser, minimum text size and required keywords. "
                "Defaults to backend/tests/recommendation_benchmark/resumes/cv_extraction_expectations.json."
            ),
        )
        parser.add_argument(
            "--fail-under-average-recall",
            type=float,
            default=0.0,
            help="Raise an error if the average keyword recall falls below this value.",
        )
        parser.add_argument(
            "--fail-on-fixture-failure",
            action="store_true",
            help="Raise an error if any single CV fixture misses its expectations.",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            dest="json_output",
            help="Print the full benchmark payload as JSON.",
        )

    def handle(self, *args, **options):
        repo_dir = _base_dir()
        resume_dir = _resolve_path(
            options.get("resume_dir"),
            default=repo_dir / "benchmark_inputs" / "cvs",
        )
        expectations_path = _resolve_path(
            options.get("expectations"),
            default=repo_dir / "tests" / "recommendation_benchmark" / "resumes" / "cv_extraction_expectations.json",
        )

        if not resume_dir.exists() or not resume_dir.is_dir():
            raise CommandError(f"Resume directory not found: {resume_dir}")
        if not expectations_path.exists() or not expectations_path.is_file():
            raise CommandError(f"Expectations file not found: {expectations_path}")

        expectations = self._load_expectations(expectations_path)
        rows = [self._evaluate_fixture(resume_dir, fixture) for fixture in expectations]
        summary = self._build_summary(rows)
        payload = {
            "resume_dir": str(resume_dir),
            "expectations_path": str(expectations_path),
            "summary": summary,
            "rows": rows,
        }

        min_average_recall = float(options.get("fail_under_average_recall") or 0.0)
        fail_on_fixture_failure = bool(options.get("fail_on_fixture_failure"))

        if options.get("json_output"):
            self.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            self._print_human_report(summary, rows)

        if min_average_recall and summary["average_keyword_recall"] < min_average_recall:
            raise CommandError(
                "Average keyword recall "
                f"{summary['average_keyword_recall']:.3f} is below the required threshold {min_average_recall:.3f}."
            )

        if fail_on_fixture_failure and summary["failed_files"]:
            raise CommandError(
                "Some CV fixtures did not meet extraction expectations: "
                + ", ".join(summary["failed_files"])
            )

    def _load_expectations(self, expectations_path: Path) -> list[dict[str, Any]]:
        data = json.loads(expectations_path.read_text(encoding="utf-8"))
        if not isinstance(data, list) or not data:
            raise CommandError("Expectations JSON must contain a non-empty list of fixtures.")
        return data

    def _evaluate_fixture(self, resume_dir: Path, fixture: dict[str, Any]) -> dict[str, Any]:
        file_name = str(fixture.get("file") or "").strip()
        file_path = resume_dir / file_name
        expected_parser = str(fixture.get("expected_parser") or "").strip()
        min_chars = int(fixture.get("min_chars") or 0)
        min_keyword_recall = float(fixture.get("min_keyword_recall") or 0.0)
        required_keywords = [str(keyword).strip() for keyword in fixture.get("required_keywords") or [] if str(keyword).strip()]

        row = {
            "file": file_name,
            "file_path": str(file_path),
            "exists": file_path.exists(),
            "expected_parser": expected_parser,
            "parser": "",
            "text_chars": 0,
            "required_keywords": required_keywords,
            "matched_keywords": [],
            "missing_keywords": [],
            "keyword_recall": 0.0,
            "min_keyword_recall": min_keyword_recall,
            "min_chars": min_chars,
            "meets_expectation": False,
            "error": "",
        }

        if not file_path.exists():
            row["error"] = "resume_file_missing"
            return row

        try:
            with file_path.open("rb") as handle:
                parsed = parse_resume_file(handle, filename=file_name)
        except Exception as exc:  # noqa: BLE001 - benchmark should report fixture failures
            row["error"] = str(exc) or exc.__class__.__name__
            return row

        normalized_text = _normalize_lookup_text(parsed.text)
        matched_keywords = [
            keyword
            for keyword in required_keywords
            if _normalize_lookup_text(keyword) in normalized_text
        ]
        keyword_recall = (
            len(matched_keywords) / len(required_keywords)
            if required_keywords
            else 1.0
        )

        row.update(
            {
                "parser": parsed.parser,
                "text_chars": len(parsed.text),
                "matched_keywords": matched_keywords,
                "missing_keywords": [keyword for keyword in required_keywords if keyword not in matched_keywords],
                "keyword_recall": round(keyword_recall, 4),
                "meets_expectation": (
                    (not expected_parser or parsed.parser == expected_parser)
                    and len(parsed.text) >= min_chars
                    and keyword_recall >= min_keyword_recall
                ),
            }
        )
        return row

    def _build_summary(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        total_files = len(rows)
        parsed_success_count = sum(1 for row in rows if not row["error"])
        average_keyword_recall = (
            round(sum(float(row["keyword_recall"]) for row in rows) / total_files, 4)
            if total_files
            else 0.0
        )
        parser_distribution = Counter(row["parser"] for row in rows if row["parser"])
        failed_files = [row["file"] for row in rows if not row["meets_expectation"]]
        return {
            "total_files": total_files,
            "parsed_success_count": parsed_success_count,
            "parsed_failure_count": total_files - parsed_success_count,
            "average_keyword_recall": average_keyword_recall,
            "parser_distribution": dict(parser_distribution),
            "failed_files": failed_files,
        }

    def _print_human_report(self, summary: dict[str, Any], rows: list[dict[str, Any]]) -> None:
        self.stdout.write("CV extraction quality benchmark")
        self.stdout.write("-----------------------------")
        self.stdout.write(f"Total files: {summary['total_files']}")
        self.stdout.write(f"Parsed successfully: {summary['parsed_success_count']}")
        self.stdout.write(f"Average keyword recall: {summary['average_keyword_recall']:.2%}")
        self.stdout.write(f"Parser distribution: {summary['parser_distribution']}")
        if summary["failed_files"]:
            self.stdout.write(f"Failed fixtures: {', '.join(summary['failed_files'])}")
        else:
            self.stdout.write("Failed fixtures: none")

        self.stdout.write("")
        self.stdout.write("file\tparser\tchars\trecall\tmissing\tstatus")
        for row in rows:
            missing = ", ".join(row["missing_keywords"]) or "-"
            status = "OK" if row["meets_expectation"] else "FAIL"
            self.stdout.write(
                f"{row['file']}\t{row['parser'] or '-'}\t{row['text_chars']}\t"
                f"{row['keyword_recall']:.2%}\t{missing}\t{status}"
            )
