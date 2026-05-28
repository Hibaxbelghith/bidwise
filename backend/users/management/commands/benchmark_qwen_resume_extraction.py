from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from ai.llm.providers import _extract_json_object
from ai.llm.schemas import validate_llm_extraction
from users.resume_parsing.service import parse_resume_file
from users.resume_semantic.normalization import clean_resume_semantic_text
from users.resume_semantic.structured_llm import (
    RESUME_OFFICIAL_EXTRACTION_SCHEMA,
    build_resume_extraction_prompt,
)


def official_prompt(text: str) -> str:
    return build_resume_extraction_prompt(text)


PROMPTS = {
    "official": (official_prompt, RESUME_OFFICIAL_EXTRACTION_SCHEMA),
}


class Command(BaseCommand):
    help = "Benchmark Qwen/Ollama structured CV extraction latency and JSON quality."

    def add_arguments(self, parser):
        parser.add_argument(
            "paths",
            nargs="*",
            help="Resume files or directories inside the backend container.",
        )
        parser.add_argument("--variant", choices=sorted(PROMPTS), default="official")
        parser.add_argument("--temperature", type=float, default=0.0)
        parser.add_argument("--max-tokens", type=int, default=300)
        parser.add_argument("--timeout-seconds", type=float, default=None)
        parser.add_argument("--keep-alive", default="30m")
        parser.add_argument("--page-limits", nargs="*", type=int, default=[1, 2, 4])
        parser.add_argument("--text-chars", type=int, default=5000)
        parser.add_argument("--limit-files", type=int, default=0)
        parser.add_argument("--json", action="store_true", dest="json_output")

    def handle(self, *args, **options):
        files = self._resolve_files(options["paths"])
        if options["limit_files"]:
            files = files[: max(1, options["limit_files"])]
        if not files:
            raise CommandError("No resume files found.")

        variant = options["variant"]
        prompt_builder, schema = PROMPTS[variant]
        rows = []
        for file_path in files:
            for page_limit in options["page_limits"]:
                rows.append(
                    self._benchmark_one(
                        file_path,
                        page_limit=page_limit,
                        prompt_builder=prompt_builder,
                        schema=schema,
                        variant=variant,
                        temperature=options["temperature"],
                        max_tokens=options["max_tokens"],
                        timeout_seconds=options["timeout_seconds"],
                        text_chars=options["text_chars"],
                        keep_alive=options["keep_alive"],
                    )
                )

        if options["json_output"]:
            self.stdout.write(json.dumps(rows, ensure_ascii=False, indent=2))
            return

        self._print_table(rows)

    def _resolve_files(self, paths: list[str]) -> list[Path]:
        if not paths:
            paths = ["/app/benchmark_inputs/cvs"]
        files: list[Path] = []
        for raw_path in paths:
            path = Path(raw_path)
            if path.is_dir():
                files.extend(sorted(item for item in path.iterdir() if item.suffix.lower() in {".pdf", ".docx"}))
            elif path.is_file():
                files.append(path)
        return files

    def _extract_text(self, file_path: Path, *, page_limit: int, text_chars: int) -> tuple[str, int | None]:
        if file_path.suffix.lower() == ".pdf":
            try:
                from pypdf import PdfReader
            except ImportError as exc:
                raise CommandError("pypdf is required for PDF page-limited benchmarking.") from exc
            with file_path.open("rb") as handle:
                reader = PdfReader(handle, strict=False)
                actual_pages = len(reader.pages)
                parts = []
                for page in reader.pages[: max(1, page_limit)]:
                    parts.append(page.extract_text() or "")
                text = "\n".join(parts)
        else:
            with file_path.open("rb") as handle:
                parsed = parse_resume_file(handle, filename=file_path.name)
            text = parsed.text
            actual_pages = None
        return clean_resume_semantic_text(text, max_chars=max(500, text_chars)), actual_pages

    def _benchmark_one(
        self,
        file_path: Path,
        *,
        page_limit: int,
        prompt_builder,
        schema: dict[str, Any],
        variant: str,
        temperature: float,
        max_tokens: int,
        timeout_seconds: float | None,
        text_chars: int,
        keep_alive: str,
    ) -> dict[str, Any]:
        text, actual_pages = self._extract_text(file_path, page_limit=page_limit, text_chars=text_chars)
        prompt = prompt_builder(text)
        model = str(getattr(settings, "OLLAMA_MODEL", "") or "").strip()
        base_url = str(getattr(settings, "OLLAMA_BASE_URL", "") or "http://host.docker.internal:11434").rstrip("/")
        timeout = timeout_seconds or float(getattr(settings, "OLLAMA_TIMEOUT_SECONDS", 120.0))
        payload = {
            "model": model,
            "prompt": f"{prompt}\n\nReturn only one valid JSON object.",
            "stream": False,
            "format": schema,
            "options": {
                "temperature": temperature,
                "num_predict": max(64, int(max_tokens)),
            },
        }
        if str(keep_alive or "").strip():
            payload["keep_alive"] = str(keep_alive).strip()
        started = time.monotonic()
        ok = False
        error = ""
        response_chars = 0
        output_keys = []
        ollama_data: dict[str, Any] = {}
        try:
            response = requests.post(f"{base_url}/api/generate", json=payload, timeout=timeout)
            response.raise_for_status()
            ollama_data = response.json()
            response_text = str(ollama_data.get("response") or "")
            response_chars = len(response_text)
            parsed = _extract_json_object(response_text)
            result = validate_llm_extraction(parsed, provider="ollama", model=model)
            output_keys = sorted(result.as_dict().keys())
            ok = True
        except Exception as exc:  # noqa: BLE001 - benchmark should record failures
            error = str(exc)[:220] or exc.__class__.__name__

        elapsed = time.monotonic() - started
        return {
            "file": file_path.name,
            "variant": variant,
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "page_limit": page_limit,
            "actual_pages": actual_pages,
            "text_chars": len(text),
            "prompt_chars": len(prompt),
            "response_chars": response_chars,
            "wall_seconds": round(elapsed, 2),
            "ollama_total_seconds": self._ns_to_seconds(ollama_data.get("total_duration")),
            "ollama_load_seconds": self._ns_to_seconds(ollama_data.get("load_duration")),
            "ollama_prompt_eval_count": ollama_data.get("prompt_eval_count"),
            "ollama_prompt_eval_seconds": self._ns_to_seconds(ollama_data.get("prompt_eval_duration")),
            "ollama_eval_count": ollama_data.get("eval_count"),
            "ollama_eval_seconds": self._ns_to_seconds(ollama_data.get("eval_duration")),
            "ok": ok,
            "error": error,
            "output_keys": output_keys,
        }

    def _ns_to_seconds(self, value: Any) -> float | None:
        try:
            return round(float(value) / 1_000_000_000, 2)
        except (TypeError, ValueError):
            return None

    def _print_table(self, rows: list[dict[str, Any]]) -> None:
        headers = [
            "file",
            "variant",
            "pages",
            "chars",
            "prompt",
            "tokens",
            "temp",
            "wall",
            "eval",
            "prompt_eval",
            "load",
            "ok",
            "error",
        ]
        self.stdout.write("\t".join(headers))
        for row in rows:
            values = [
                row["file"],
                row["variant"],
                f"{row['page_limit']}/{row['actual_pages'] or '?'}",
                str(row["text_chars"]),
                str(row["prompt_chars"]),
                str(row["max_tokens"]),
                str(row["temperature"]),
                str(row["wall_seconds"]),
                str(row["ollama_eval_seconds"]),
                str(row["ollama_prompt_eval_seconds"]),
                str(row["ollama_load_seconds"]),
                "yes" if row["ok"] else "no",
                row["error"],
            ]
            self.stdout.write("\t".join(values))
