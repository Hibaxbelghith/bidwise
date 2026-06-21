import json
import secrets
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from applications.models import Candidature, INTERNAL_APPLICATION_STATUSES, StatutSuiviCandidature
from opportunities.models import Opportunite
from users.models import ProfileResume, Utilisateur
from users.storage import ProfileResumeStorage


User = get_user_model()


class Command(BaseCommand):
    help = (
        "Bulk create direct candidate applications for opportunities owned by an "
        "organization account from a JSON file."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "json_file",
            help="Path to a JSON file containing an array of applications or {'applications': [...]}",
        )
        parser.add_argument(
            "--email",
            required=True,
            help="Organization account email that owns the target opportunities.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate the file and show what would be created without writing to the database.",
        )

    def handle(self, *args, **options):
        file_path = Path(options["json_file"]).expanduser()
        if not file_path.exists():
            raise CommandError(f"JSON file not found: {file_path}")

        payload = self._load_payload(file_path)
        if not payload:
            raise CommandError("No applications found in the provided JSON file.")

        organization_user = self._get_organization_user(options["email"])
        dry_run = bool(options["dry_run"])

        created_count = 0
        errors = []

        for index, raw_item in enumerate(payload, start=1):
            try:
                normalized = self._normalize_item(
                    raw_item=raw_item,
                    base_dir=file_path.parent,
                    organization_user=organization_user,
                    dry_run=dry_run,
                )
            except CommandError as exc:
                errors.append(f"Row {index}: {exc}")
                continue

            if dry_run:
                created_count += 1
                self.stdout.write(
                    "[DRY RUN] "
                    f"#{index} {normalized['candidate'].email} -> "
                    f"{normalized['opportunity'].id} {normalized['opportunity'].titre} / "
                    f"{normalized['status']}"
                )
                continue

            with transaction.atomic():
                cover_letter_url = self._store_cover_letter(
                    candidate=normalized["candidate"],
                    source_path=normalized["cover_letter_path"],
                )
                Candidature.objects.create(
                    candidat=normalized["candidate"],
                    opportunite=normalized["opportunity"],
                    statut=normalized["status"],
                    cv=normalized["resume"],
                    cover_letter_url=cover_letter_url or normalized["cover_letter_url"],
                    contact_email=normalized["contact_email"],
                    contact_phone=normalized["contact_phone"],
                    submitted_at=normalized["submitted_at"],
                )

            created_count += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f"Created #{index}: {normalized['candidate'].email} -> "
                    f"{normalized['opportunity'].titre} ({normalized['status']})"
                )
            )

        if errors:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING("Import completed with validation issues:"))
            for error in errors:
                self.stdout.write(f" - {error}")

        self.stdout.write("")
        summary_label = "Validated" if dry_run else "Created"
        self.stdout.write(self.style.SUCCESS(f"{summary_label}: {created_count}"))
        self.stdout.write(f"Rejected: {len(errors)}")
        self.stdout.write(f"Owner: {organization_user.email}")
        self.stdout.write(f"Mode: {'dry-run' if dry_run else 'apply'}")

    def _load_payload(self, file_path: Path):
        try:
            payload = json.loads(file_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise CommandError(f"Invalid JSON file: {exc}") from exc

        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict) and isinstance(payload.get("applications"), list):
            return payload["applications"]
        raise CommandError(
            "JSON must be either an array of applications or an object with an 'applications' array."
        )

    def _get_organization_user(self, email: str):
        normalized_email = str(email or "").strip().lower()
        if not normalized_email:
            raise CommandError("Organization email is required.")

        user = User.objects.filter(email__iexact=normalized_email).first()
        if user is None:
            raise CommandError(f"No user found with email {normalized_email}.")
        if user.account_type != Utilisateur.AccountType.ORGANIZATION:
            raise CommandError(f"User {normalized_email} is not an organization account.")
        return user

    def _normalize_item(self, *, raw_item, base_dir: Path, organization_user, dry_run: bool):
        if not isinstance(raw_item, dict):
            raise CommandError("Each application entry must be an object.")

        candidate_email = str(raw_item.get("candidate_email") or "").strip().lower()
        if not candidate_email:
            raise CommandError("candidate_email is required.")

        candidate = User.objects.filter(email__iexact=candidate_email).first()
        if candidate is None:
            raise CommandError(f"Candidate not found: {candidate_email}")
        if candidate.account_type != Utilisateur.AccountType.CANDIDATE:
            raise CommandError(f"User {candidate_email} is not a candidate account.")

        opportunity_id = raw_item.get("opportunity_id")
        if not opportunity_id:
            raise CommandError("opportunity_id is required.")

        opportunity = Opportunite.objects.filter(
            pk=opportunity_id,
            organisation=organization_user,
        ).first()
        if opportunity is None:
            raise CommandError(
                f"Opportunity {opportunity_id} does not belong to {organization_user.email}."
            )
        if opportunity.type_opportunite == "PROJET":
            raise CommandError("Direct candidate applications are not allowed for tenders.")

        existing = Candidature.objects.filter(
            candidat=candidate,
            opportunite=opportunity,
        ).exists()
        if existing:
            raise CommandError(
                f"Candidate {candidate_email} already has an application for opportunity {opportunity_id}."
            )

        resume = self._resolve_resume(candidate=candidate, raw_item=raw_item)

        status = str(raw_item.get("status") or StatutSuiviCandidature.SUBMITTED).strip().upper()
        if status not in INTERNAL_APPLICATION_STATUSES:
            raise CommandError(f"Unsupported internal application status: {status}")

        submitted_at = self._resolve_submitted_at(raw_item.get("submitted_at"))
        contact_email = str(raw_item.get("contact_email") or candidate.email or "").strip()
        if not contact_email:
            raise CommandError("contact_email could not be resolved.")
        contact_phone = str(raw_item.get("contact_phone") or "").strip()

        cover_letter_url = str(raw_item.get("cover_letter_url") or "").strip()
        cover_letter_path = None
        if not cover_letter_url:
            cover_letter_file = str(raw_item.get("cover_letter_file") or "").strip()
            if cover_letter_file:
                candidate_path = Path(cover_letter_file)
                if not candidate_path.is_absolute():
                    candidate_path = (base_dir / candidate_path).resolve()
                if not candidate_path.exists():
                    raise CommandError(f"cover_letter_file not found: {candidate_path}")
                cover_letter_path = candidate_path
            elif not dry_run:
                raise CommandError(
                    "Either cover_letter_url or cover_letter_file is required for non-dry-run import."
                )

        return {
            "candidate": candidate,
            "opportunity": opportunity,
            "resume": resume,
            "status": status,
            "submitted_at": submitted_at,
            "contact_email": contact_email,
            "contact_phone": contact_phone,
            "cover_letter_url": cover_letter_url,
            "cover_letter_path": cover_letter_path,
        }

    def _resolve_resume(self, *, candidate, raw_item):
        resume_id = raw_item.get("resume_id")
        if resume_id:
            resume = ProfileResume.objects.filter(
                pk=resume_id,
                profile=candidate.profil,
                is_active=True,
            ).first()
            if resume is None or not resume.file:
                raise CommandError(
                    f"Active resume {resume_id} not found for candidate {candidate.email}."
                )
            return resume

        resume = candidate.profil.resumes.filter(is_active=True).first()
        if resume is None or not resume.file:
            raise CommandError(f"No active resume found for candidate {candidate.email}.")
        return resume

    def _resolve_submitted_at(self, raw_value):
        if not raw_value:
            return timezone.now()
        parsed = parse_datetime(str(raw_value).strip())
        if parsed is None:
            raise CommandError(f"Invalid submitted_at datetime: {raw_value}")
        if timezone.is_naive(parsed):
            parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
        return parsed

    def _store_cover_letter(self, *, candidate, source_path: Path | None):
        if source_path is None:
            return ""

        extension = source_path.suffix.lower() or ".bin"
        storage = ProfileResumeStorage()
        target_name = (
            f"application_cover_letters/{candidate.pk}/"
            f"{secrets.token_hex(16)}{extension}"
        )
        with source_path.open("rb") as file_handle:
            stored_name = storage.save(target_name, File(file_handle, name=source_path.name))
        return storage.url(stored_name)
