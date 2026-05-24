import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from ai.esco_mapper import normalize_text
from ai.esco_skill_index import clear_esco_skill_index_cache
from ai.models import BidWiseSkillAlias, ESCOSkill


class Command(BaseCommand):
    help = "Load review-approved BidWise skill aliases from a CSV file."

    def add_arguments(self, parser):
        parser.add_argument("csv_path", help="CSV file path containing alias rows.")
        parser.add_argument(
            "--default-status",
            choices=[choice for choice, _label in BidWiseSkillAlias.Status.choices],
            default=BidWiseSkillAlias.Status.ACTIVE,
            help="Fallback status used when the CSV row omits a status.",
        )
        parser.add_argument(
            "--default-source",
            default="manual_review",
            help="Fallback source used when the CSV row omits a source.",
        )

    def handle(self, *args, **options):
        csv_path = Path(str(options["csv_path"]))
        if not csv_path.exists():
            raise CommandError(f"CSV file does not exist: {csv_path}")

        default_status = str(options["default_status"] or BidWiseSkillAlias.Status.ACTIVE)
        default_source = str(options["default_source"] or "manual_review").strip()

        with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)

        if not rows:
            raise CommandError("CSV file is empty.")

        uri_values = sorted(
            {
                str(row.get("target_esco_uri") or "").strip()
                for row in rows
                if str(row.get("target_esco_uri") or "").strip()
            }
        )
        skills_by_uri = {
            skill.uri: skill
            for skill in ESCOSkill.objects.filter(uri__in=uri_values)
        }

        creates = []
        updates = []
        skipped = 0
        existing = {
            alias.alias.casefold(): alias
            for alias in BidWiseSkillAlias.objects.filter(
                alias__in=[
                    str(row.get("alias") or "").strip()
                    for row in rows
                    if str(row.get("alias") or "").strip()
                ]
            ).select_related("target_skill")
        }

        for row in rows:
            alias = str(row.get("alias") or "").strip()
            target_uri = str(row.get("target_esco_uri") or "").strip()
            if not alias or not target_uri:
                skipped += 1
                continue

            skill = skills_by_uri.get(target_uri)
            if skill is None:
                skipped += 1
                continue

            normalized_key = normalize_text(alias)
            if not normalized_key:
                skipped += 1
                continue

            status = str(row.get("status") or default_status).strip() or default_status
            source = str(row.get("source") or default_source).strip() or default_source
            language = str(row.get("language") or "").strip()
            notes = str(row.get("notes") or "").strip()

            existing_row = existing.get(alias.casefold())
            if existing_row is None:
                creates.append(
                    BidWiseSkillAlias(
                        alias=alias,
                        normalized_key=normalized_key,
                        language=language,
                        target_skill=skill,
                        source=source,
                        status=status,
                        notes=notes,
                    )
                )
                continue

            changed = False
            if existing_row.normalized_key != normalized_key:
                existing_row.normalized_key = normalized_key
                changed = True
            if existing_row.language != language:
                existing_row.language = language
                changed = True
            if existing_row.target_skill_id != skill.id:
                existing_row.target_skill = skill
                changed = True
            if existing_row.source != source:
                existing_row.source = source
                changed = True
            if existing_row.status != status:
                existing_row.status = status
                changed = True
            if existing_row.notes != notes:
                existing_row.notes = notes
                changed = True
            if changed:
                updates.append(existing_row)

        if creates:
            BidWiseSkillAlias.objects.bulk_create(creates, batch_size=500)
        if updates:
            BidWiseSkillAlias.objects.bulk_update(
                updates,
                ["normalized_key", "language", "target_skill", "source", "status", "notes"],
                batch_size=500,
            )

        clear_esco_skill_index_cache()
        self.stdout.write(
            self.style.SUCCESS(
                "BidWise skill alias load complete creates=%s updates=%s skipped=%s"
                % (len(creates), len(updates), skipped)
            )
        )

