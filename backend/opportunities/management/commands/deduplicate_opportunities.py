import re
import unicodedata
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction

from applications.models import Candidature
from opportunities.models import Opportunite, RawOpportunite


def _normalize_key_text(value):
    if value is None:
        return ""
    cleaned = unicodedata.normalize("NFKC", str(value)).lower().strip()
    cleaned = "".join(ch if (ch.isalnum() or ch.isspace()) else " " for ch in cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def _extract_location(payload):
    if not isinstance(payload, dict):
        return ""
    for key in ("ville", "location", "city", "gouvernorat", "region", "lieu"):
        value = payload.get(key)
        if value:
            return str(value).strip()
    return ""


class Command(BaseCommand):
    help = (
        "Merge duplicates using title+company+city+type within a rolling publication-date window. "
        "By default runs in dry-run mode. Use --apply to execute."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply deduplication changes (default is dry-run).",
        )
        parser.add_argument(
            "--sample-size",
            type=int,
            default=5,
            help="Number of duplicate groups to print as examples.",
        )
        parser.add_argument(
            "--window-days",
            type=int,
            default=30,
            help="Rolling date window (in days) used for dedup inside each title+company+city+type group.",
        )

    def handle(self, *args, **options):
        apply_changes = bool(options["apply"])
        sample_size = max(1, int(options["sample_size"]))
        window_days = max(0, int(options["window_days"]))

        location_by_canonical = {}
        for _, canonical_id, payload in RawOpportunite.objects.filter(canonical__isnull=False).values_list(
            "id", "canonical_id", "raw_payload"
        ).order_by("-id"):
            if canonical_id in location_by_canonical:
                continue
            location_by_canonical[canonical_id] = _extract_location(payload)

        ville_max_length = Opportunite._meta.get_field("ville").max_length
        synced_cities = 0

        for opp in Opportunite.objects.only("id", "ville").iterator(chunk_size=500):
            if (opp.ville or "").strip():
                continue
            raw_city = (location_by_canonical.get(opp.id) or "").strip()
            if not raw_city:
                continue
            capped_city = raw_city[:ville_max_length]
            if apply_changes:
                Opportunite.objects.filter(pk=opp.id).update(ville=capped_city)
            synced_cities += 1

        groups = defaultdict(list)
        rows = Opportunite.objects.values(
            "id",
            "titre",
            "organisation_nom",
            "ville",
            "type_opportunite",
            "date_publication",
        )

        for row in rows:
            city = (row.get("ville") or "").strip() or (location_by_canonical.get(row["id"]) or "").strip()

            key = (
                _normalize_key_text(row.get("titre")),
                _normalize_key_text(row.get("organisation_nom")),
                _normalize_key_text(city),
                str(row.get("type_opportunite") or "").strip(),
            )

            if not (key[0] and key[1] and key[2] and key[3] and row.get("date_publication")):
                continue

            groups[key].append((int(row["id"]), row["date_publication"]))

        duplicate_map = {}
        group_samples = []
        groups_with_duplicates = 0

        for key, items in groups.items():
            unique_items = sorted(set(items), key=lambda item: item[1], reverse=True)
            if len(unique_items) < 2:
                continue

            keepers = []
            local_dups = []

            for opp_id, pub_date in unique_items:
                matched_keeper_id = None
                for keeper_id, keeper_date in keepers:
                    if abs((pub_date - keeper_date).days) <= window_days:
                        matched_keeper_id = keeper_id
                        break

                if matched_keeper_id is None:
                    keepers.append((opp_id, pub_date))
                else:
                    duplicate_map[opp_id] = matched_keeper_id
                    local_dups.append((opp_id, matched_keeper_id, pub_date))

            if local_dups:
                groups_with_duplicates += 1
                if len(group_samples) < sample_size:
                    group_samples.append((key, local_dups))

        self.stdout.write("=== DEDUP PLAN ===")
        self.stdout.write(f"apply_changes={apply_changes}")
        self.stdout.write(f"window_days={window_days}")
        self.stdout.write(f"city_backfill_candidates={synced_cities}")
        self.stdout.write(f"duplicate_groups={groups_with_duplicates}")
        self.stdout.write(f"duplicate_rows={len(duplicate_map)}")

        for key, local_dups in group_samples:
            self.stdout.write(f"sample_group key={key} duplicates={local_dups[:3]}")

        if not apply_changes:
            self.stdout.write(self.style.SUCCESS("Dry-run completed. Re-run with --apply to merge duplicates."))
            return

        merged_groups = 0
        merged_rows = 0
        skipped_groups_with_candidatures = 0

        duplicates_by_keeper = defaultdict(list)
        for duplicate_id, keeper_id in duplicate_map.items():
            duplicates_by_keeper[keeper_id].append(duplicate_id)

        for keeper_id, duplicate_ids in duplicates_by_keeper.items():
            impacted_ids = [keeper_id, *duplicate_ids]
            if Candidature.objects.filter(opportunite_id__in=impacted_ids).exists():
                skipped_groups_with_candidatures += 1
                continue

            with transaction.atomic():
                RawOpportunite.objects.filter(canonical_id__in=duplicate_ids).update(canonical_id=keeper_id)
                Opportunite.objects.filter(id__in=duplicate_ids).delete()

            merged_groups += 1
            merged_rows += len(duplicate_ids)

        self.stdout.write("=== DEDUP RESULT ===")
        self.stdout.write(f"merged_groups={merged_groups}")
        self.stdout.write(f"merged_rows={merged_rows}")
        self.stdout.write(f"skipped_groups_with_candidatures={skipped_groups_with_candidatures}")
        self.stdout.write(self.style.SUCCESS("Deduplication completed."))
