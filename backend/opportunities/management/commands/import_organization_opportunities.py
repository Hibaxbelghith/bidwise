import json
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from opportunities.moderation_llm import (
    DECISION_APPROVED,
    classify_opportunity_with_gemini,
    failed_llm_result,
)
from opportunities.models import DateConfidence, Opportunite, SourceOpportunite, StatutOpportunite
from opportunities.normalization.employment import (
    normalize_contract_types,
    normalize_schedule,
    normalize_work_mode,
)
from opportunities.serializers import OrganizationOpportunityWriteSerializer
from opportunities.views import (
    ORGANIZATION_SOURCE_NAME,
    ORGANIZATION_SOURCE_URL,
    _moderation_payload,
)
from users.models import Utilisateur


User = get_user_model()


class Command(BaseCommand):
    help = (
        "Bulk create organization-owned opportunities from a JSON file, using the same "
        "validation rules as the organization posting flow."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "json_file",
            help="Path to a JSON file containing an array of opportunities or {'opportunities': [...]}",
        )
        parser.add_argument(
            "--email",
            required=True,
            help="Organization account email that will own the imported opportunities.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate the file and show what would be created without writing to the database.",
        )
        parser.add_argument(
            "--run-moderation",
            action="store_true",
            help="Run the same Gemini moderation step used by the organization posting API.",
        )
        parser.add_argument(
            "--status",
            choices=[choice for choice, _label in StatutOpportunite.choices],
            default=StatutOpportunite.ACTIVE,
            help="Fallback status when moderation is disabled. Default: ACTIVE.",
        )

    def handle(self, *args, **options):
        file_path = Path(options["json_file"]).expanduser()
        if not file_path.exists():
            raise CommandError(f"JSON file not found: {file_path}")

        opportunities_payload = self._load_payload(file_path)
        if not opportunities_payload:
            raise CommandError("No opportunities found in the provided JSON file.")

        organization_user = self._get_organization_user(options["email"])
        organization_profile = getattr(organization_user, "organization_profile", None)
        if organization_profile is None:
            raise CommandError(
                f"User {organization_user.email} has no organization profile."
            )

        source, _created = SourceOpportunite.objects.get_or_create(
            nom=ORGANIZATION_SOURCE_NAME,
            defaults={
                "url": ORGANIZATION_SOURCE_URL,
                "type_source": "AUTRE",
            },
        )

        dry_run = options["dry_run"]
        run_moderation = options["run_moderation"]
        fallback_status = options["status"]

        created_count = 0
        errors = []

        for index, raw_item in enumerate(opportunities_payload, start=1):
            if not isinstance(raw_item, dict):
                errors.append(f"Row {index}: each opportunity must be an object.")
                continue

            serializer = OrganizationOpportunityWriteSerializer(data=raw_item)
            if not serializer.is_valid():
                errors.append(f"Row {index}: {serializer.errors}")
                continue

            validated = serializer.validated_data
            extra_data = {"published_by": "organization_import"}

            if validated.get("internship_details"):
                extra_data["internship_details"] = validated["internship_details"]
            if validated.get("seasonal_details"):
                extra_data["seasonal_details"] = validated["seasonal_details"]
            if validated.get("project_details"):
                extra_data.update(validated["project_details"])
                extra_data["project_details"] = validated["project_details"]

            opportunity_status = fallback_status
            if run_moderation:
                moderation_payload = _moderation_payload(validated, raw_item)
                try:
                    llm_result = classify_opportunity_with_gemini(moderation_payload)
                except Exception:
                    llm_result = failed_llm_result(
                        "LLM moderation failed unexpectedly; kept for admin review.",
                    )

                opportunity_status = (
                    StatutOpportunite.ACTIVE
                    if llm_result.decision == DECISION_APPROVED
                    else StatutOpportunite.PENDING_REVIEW
                )
                extra_data["moderation"] = {
                    "llm": llm_result.to_dict(),
                    "final_decision": llm_result.decision,
                    "final_status": opportunity_status,
                    "automatic_decision_id": timezone.now().isoformat(),
                }

            if dry_run:
                created_count += 1
                self.stdout.write(
                    f"[DRY RUN] #{index} {validated['title']} -> {validated['type']} / {opportunity_status}"
                )
                continue

            with transaction.atomic():
                Opportunite.objects.create(
                    titre=validated["title"],
                    description=validated["description"],
                    description_html="",
                    organisation_nom=(
                        validated.get("project_details", {}).get("public_buyer")
                        or organization_profile.organization_name
                    ),
                    company_logo=organization_profile.logo or "",
                    ville=validated["location"],
                    contract_type=validated.get("contract", ""),
                    normalized_contract_types=normalize_contract_types(validated.get("contract", "")),
                    availability=validated.get("availability", ""),
                    normalized_work_mode=normalize_work_mode(validated.get("availability", "")),
                    normalized_schedule=normalize_schedule(
                        [validated.get("availability", ""), validated.get("contract", "")]
                    ),
                    experience_min=validated.get("experience_min"),
                    experience_max=validated.get("experience_max"),
                    education_level=validated.get("education_level", ""),
                    salary=validated.get("salary", ""),
                    skills=validated.get("skills", []),
                    raw_skills=validated.get("skills", []),
                    type_opportunite=validated["type"],
                    statut=opportunity_status,
                    date_publication=timezone.localdate(),
                    date_limite=validated.get("deadline"),
                    date_confidence=DateConfidence.EXACT,
                    source=source,
                    organisation=organization_user,
                    extra_data=extra_data,
                )

            created_count += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f"Created #{index}: {validated['title']} ({validated['type']}, {opportunity_status})"
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
        self.stdout.write(f"Moderation: {'enabled' if run_moderation else 'disabled'}")

    def _load_payload(self, file_path: Path):
        try:
            payload = json.loads(file_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise CommandError(f"Invalid JSON file: {exc}") from exc

        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict) and isinstance(payload.get("opportunities"), list):
            return payload["opportunities"]
        raise CommandError(
            "JSON must be either an array of opportunities or an object with an 'opportunities' array."
        )

    def _get_organization_user(self, email: str):
        normalized_email = str(email or "").strip().lower()
        if not normalized_email:
            raise CommandError("Organization email is required.")

        user = (
            User.objects.select_related("organization_profile")
            .filter(email__iexact=normalized_email)
            .first()
        )
        if user is None:
            raise CommandError(f"No user found with email {normalized_email}.")
        if user.account_type != Utilisateur.AccountType.ORGANIZATION:
            raise CommandError(
                f"User {normalized_email} is not an organization account."
            )
        return user
