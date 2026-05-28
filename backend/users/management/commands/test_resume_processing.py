from __future__ import annotations

import time
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.test import override_settings
from django.utils import timezone

from users.models import Profil, ProfileResume
from users.tasks import enqueue_profile_resume_parse, parse_profile_resume


class Command(BaseCommand):
    help = "Test one resume parsing/enrichment run and print timings without running the benchmark."

    def add_arguments(self, parser):
        parser.add_argument("file_path", help="Path to a PDF/DOCX/TXT resume file inside the backend container.")
        parser.add_argument(
            "--profile-id",
            type=int,
            default=None,
            help="Profile id to attach the temporary resume to. Defaults to the first profile.",
        )
        parser.add_argument(
            "--async",
            action="store_true",
            dest="run_async",
            help="Enqueue through Celery and poll DB status. Default runs synchronously in this process.",
        )
        parser.add_argument(
            "--timeout-seconds",
            type=int,
            default=180,
            help="Maximum wait when using --async.",
        )
        parser.add_argument(
            "--keep",
            action="store_true",
            help="Keep the temporary ProfileResume row for inspection.",
        )
        parser.add_argument(
            "--structured-llm",
            action="store_true",
            help=(
                "Force Qwen/Ollama structured extraction for the synchronous run. "
                "No lightweight semantic fallback is written if Qwen fails."
            ),
        )

    def handle(self, *args, **options):
        file_path = Path(options["file_path"])
        if not file_path.exists() or not file_path.is_file():
            raise CommandError(f"Resume file not found: {file_path}")

        profile = self._get_profile(options["profile_id"])
        started = time.monotonic()
        resume = self._create_resume(profile, file_path)
        self.stdout.write(f"Created temporary resume id={resume.pk} file={file_path.name}")

        try:
            if options["run_async"]:
                if options["structured_llm"]:
                    self.stdout.write(
                        "Note: --structured-llm cannot override an already running Celery worker. "
                        "Use PROFILE_RESUME_STRUCTURED_LLM_ENABLED=true and "
                        "PROFILE_RESUME_STRUCTURED_LLM_FALLBACK_ENABLED=false for async testing."
                    )
                self._run_async(resume.pk, timeout_seconds=options["timeout_seconds"])
            else:
                if options["structured_llm"]:
                    with override_settings(
                        PROFILE_RESUME_STRUCTURED_LLM_ENABLED=True,
                        PROFILE_RESUME_STRUCTURED_LLM_FALLBACK_ENABLED=False,
                    ):
                        result = parse_profile_resume(resume.pk)
                else:
                    result = parse_profile_resume(resume.pk)
                self.stdout.write(f"Task result: {result}")

            resume.refresh_from_db()
            elapsed = time.monotonic() - started
            self._print_resume_summary(resume, elapsed)
        finally:
            if not options["keep"]:
                resume.delete()
                self.stdout.write("Temporary resume deleted. Use --keep to inspect it later.")

    def _get_profile(self, profile_id: int | None) -> Profil:
        queryset = Profil.objects.order_by("pk")
        profile = queryset.filter(pk=profile_id).first() if profile_id else queryset.first()
        if not profile:
            raise CommandError("No profile found. Create a profile first or pass --profile-id.")
        return profile

    def _create_resume(self, profile: Profil, file_path: Path) -> ProfileResume:
        with file_path.open("rb") as handle:
            return ProfileResume.objects.create(
                profile=profile,
                file=File(handle, name=f"test_resume_{file_path.name}"),
                is_active=False,
                source_type=ProfileResume.SourceType.UPLOAD,
            )

    def _run_async(self, resume_id: int, *, timeout_seconds: int) -> None:
        if not enqueue_profile_resume_parse(resume_id):
            raise CommandError(f"Could not enqueue resume id={resume_id}")

        deadline = time.monotonic() + max(1, timeout_seconds)
        while time.monotonic() < deadline:
            resume = ProfileResume.objects.only(
                "parsing_status",
                "semantic_resume_status",
                "semantic_resume_error",
            ).get(pk=resume_id)
            semantic_status = str(resume.semantic_resume_status or "").upper()
            parsing_status = str(resume.parsing_status or "").upper()
            if semantic_status in {"SUCCEEDED", "EMPTY", "FAILED", "SKIPPED"}:
                return
            if parsing_status in {"FAILED", "EMPTY", "UNSUPPORTED"}:
                return
            time.sleep(1)

        raise CommandError(f"Timed out waiting for resume id={resume_id}")

    def _print_resume_summary(self, resume: ProfileResume, elapsed_seconds: float) -> None:
        parse_seconds = (
            (resume.parsed_at - resume.uploaded_at).total_seconds()
            if resume.parsed_at and resume.uploaded_at
            else None
        )
        semantic_seconds = (
            (resume.semantic_resume_updated_at - resume.parsed_at).total_seconds()
            if resume.semantic_resume_updated_at and resume.parsed_at
            else None
        )
        total_db_seconds = (
            (resume.semantic_resume_updated_at - resume.uploaded_at).total_seconds()
            if resume.semantic_resume_updated_at and resume.uploaded_at
            else None
        )

        self.stdout.write("")
        self.stdout.write("Resume processing summary")
        self.stdout.write("-------------------------")
        self.stdout.write(f"resume_id: {resume.pk}")
        self.stdout.write(f"wall_time_seconds: {elapsed_seconds:.2f}")
        self.stdout.write(f"parse_seconds: {self._fmt(parse_seconds)}")
        self.stdout.write(f"semantic_seconds: {self._fmt(semantic_seconds)}")
        self.stdout.write(f"db_total_seconds: {self._fmt(total_db_seconds)}")
        self.stdout.write(f"parsing_status: {resume.parsing_status}")
        self.stdout.write(f"semantic_resume_status: {resume.semantic_resume_status}")
        self.stdout.write(f"semantic_resume_confidence: {resume.semantic_resume_confidence}")
        self.stdout.write(f"parsed_text_available: {bool(resume.parsed_text)}")
        self.stdout.write(f"skills: {resume.extracted_skills}")
        self.stdout.write(f"domains: {resume.extracted_domains}")
        self.stdout.write(f"tools: {resume.extracted_tools}")
        self.stdout.write(f"languages: {resume.extracted_languages}")
        self.stdout.write(f"normalized_skills_count: {len(resume.extracted_normalized_skills or [])}")
        metadata = resume.semantic_resume_metadata if isinstance(resume.semantic_resume_metadata, dict) else {}
        llm_enrichment = metadata.get("llm_enrichment") if isinstance(metadata, dict) else {}
        if isinstance(llm_enrichment, dict) and llm_enrichment:
            self.stdout.write(f"llm_version: {llm_enrichment.get('version') or 'n/a'}")
            self.stdout.write(f"llm_provider: {llm_enrichment.get('provider') or 'n/a'}")
            self.stdout.write(f"llm_model: {llm_enrichment.get('model') or 'n/a'}")
            self.stdout.write(f"profile_suggestions: {llm_enrichment.get('profile_suggestions') or {}}")
        if resume.parsing_error:
            self.stdout.write(f"parsing_error: {resume.parsing_error[:300]}")
        if resume.semantic_resume_error:
            self.stdout.write(f"semantic_resume_error: {resume.semantic_resume_error[:300]}")
        self.stdout.write(f"tested_at: {timezone.now().isoformat()}")

    def _fmt(self, value: float | None) -> str:
        return "n/a" if value is None else f"{value:.2f}"
