import re
import unicodedata
from collections import Counter, defaultdict
from datetime import date
from urllib.parse import urlparse

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count

from opportunities.models import Opportunite, RawOpportunite, StatutOpportunite


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


def _is_valid_http_url(value):
    if not value:
        return False
    try:
        parsed = urlparse(value)
    except Exception:
        return False
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


class Command(BaseCommand):
    help = "Audit dataset readiness: dedup, quality, source distribution, and AI readiness indicators."

    def add_arguments(self, parser):
        parser.add_argument(
            "--sample-size",
            type=int,
            default=5,
            help="Number of duplicate groups to print as examples.",
        )
        parser.add_argument(
            "--strict",
            action="store_true",
            help="Return a non-zero exit code if hard duplicates, invalid URLs, or source dominance >= 90% are detected.",
        )
        parser.add_argument(
            "--window-days",
            type=int,
            default=30,
            help="Rolling window (days) used to report practical triad duplicates.",
        )
        parser.add_argument(
            "--active-dominance-threshold",
            type=float,
            default=0.80,
            help="Strict threshold for top-source ratio in ACTIVE dataset (default: 0.80).",
        )

    def handle(self, *args, **options):
        sample_size = max(1, int(options["sample_size"]))
        window_days = max(0, int(options["window_days"]))
        active_dominance_threshold = min(1.0, max(0.0, float(options["active_dominance_threshold"])))

        location_by_canonical = {}
        for _, canonical_id, payload in RawOpportunite.objects.filter(canonical__isnull=False).values_list(
            "id", "canonical_id", "raw_payload"
        ).order_by("-id"):
            if canonical_id in location_by_canonical:
                continue
            location_by_canonical[canonical_id] = _extract_location(payload)

        rows = list(
            Opportunite.objects.values(
                "id",
                "source__nom",
                "titre",
                "organisation_nom",
                "ville",
                "description",
                "type_opportunite",
                "date_publication",
            )
        )

        triad_counter = Counter()
        triad_with_date_counter = Counter()
        triad_examples = defaultdict(list)
        triad_with_date_examples = defaultdict(list)

        empty_city = 0
        empty_company = 0
        empty_title = 0
        short_title = 0
        title_urlish = 0
        empty_description = 0
        short_description = 0

        for row in rows:
            city = (row.get("ville") or "").strip()
            if not city:
                city = (location_by_canonical.get(row["id"]) or "").strip()

            norm_title = _normalize_key_text(row.get("titre"))
            norm_company = _normalize_key_text(row.get("organisation_nom"))
            norm_city = _normalize_key_text(city)
            opp_type = str(row.get("type_opportunite") or "").strip()
            pub_date = str(row.get("date_publication") or "")

            raw_title_clean = (row.get("titre") or "").strip()
            if not raw_title_clean:
                empty_title += 1
            if raw_title_clean and len(raw_title_clean) < 5:
                short_title += 1
            raw_title = raw_title_clean.lower()
            if "http" in raw_title or "www." in raw_title:
                title_urlish += 1

            if not norm_company:
                empty_company += 1
            if not norm_city:
                empty_city += 1

            description = (row.get("description") or "").strip()
            if not description:
                empty_description += 1
            elif len(description) < 40:
                short_description += 1

            if norm_title and norm_company and norm_city and opp_type:
                triad_key = (norm_title, norm_company, norm_city, opp_type)
                triad_counter[triad_key] += 1
                triad_examples[triad_key].append(
                    {
                        "id": row["id"],
                        "source": row.get("source__nom") or "",
                        "titre": row.get("titre") or "",
                        "organisation_nom": row.get("organisation_nom") or "",
                        "ville": city,
                        "date_publication": pub_date,
                    }
                )

                if pub_date:
                    hard_key = (*triad_key, pub_date)
                    triad_with_date_counter[hard_key] += 1
                    triad_with_date_examples[hard_key].append(triad_examples[triad_key][-1])

        soft_duplicate_keys = [k for k, c in triad_counter.items() if c > 1]
        hard_duplicate_keys = [k for k, c in triad_with_date_counter.items() if c > 1]

        soft_duplicate_rows = sum(triad_counter[k] - 1 for k in soft_duplicate_keys)
        hard_duplicate_rows = sum(triad_with_date_counter[k] - 1 for k in hard_duplicate_keys)

        window_duplicate_rows = 0
        window_duplicate_groups = 0
        for rows_in_group in triad_examples.values():
            if len(rows_in_group) < 2:
                continue

            parsed = sorted(
                [
                    (item["id"], item["date_publication"])
                    for item in rows_in_group
                    if item.get("date_publication")
                ],
                key=lambda item: item[1],
                reverse=True,
            )
            if len(parsed) < 2:
                continue

            keepers = []
            local_duplicates = 0
            for _, pub_date_raw in parsed:
                try:
                    year, month, day = [int(part) for part in str(pub_date_raw).split("-")]
                except Exception:
                    continue

                pub_date = date(year, month, day)
                matched = False
                for keeper_date in keepers:
                    if abs((pub_date - keeper_date).days) <= window_days:
                        local_duplicates += 1
                        matched = True
                        break
                if not matched:
                    keepers.append(pub_date)

            if local_duplicates > 0:
                window_duplicate_groups += 1
                window_duplicate_rows += local_duplicates

        raw_urls = list(
            RawOpportunite.objects.exclude(source_item_url__isnull=True)
            .exclude(source_item_url="")
            .values_list("source_item_url", flat=True)
        )
        invalid_url_count = sum(1 for value in raw_urls if not _is_valid_http_url(value))

        source_distribution = list(
            Opportunite.objects.values("source__nom")
            .annotate(c=Count("id"))
            .order_by("-c")
        )
        total_opportunities = sum(item["c"] for item in source_distribution)
        top_source_name = source_distribution[0]["source__nom"] if source_distribution else "N/A"
        top_source_count = source_distribution[0]["c"] if source_distribution else 0
        top_source_ratio = (top_source_count / total_opportunities) if total_opportunities else 0.0

        active_distribution = list(
            Opportunite.objects.filter(statut=StatutOpportunite.ACTIVE)
            .values("source__nom")
            .annotate(c=Count("id"))
            .order_by("-c")
        )
        active_total_opportunities = sum(item["c"] for item in active_distribution)
        active_top_source_name = active_distribution[0]["source__nom"] if active_distribution else "N/A"
        active_top_source_count = active_distribution[0]["c"] if active_distribution else 0
        active_top_source_ratio = (
            (active_top_source_count / active_total_opportunities)
            if active_total_opportunities
            else 0.0
        )

        self.stdout.write("=== DATASET AUDIT ===")
        self.stdout.write(f"total_opportunities={total_opportunities}")
        self.stdout.write(f"soft_duplicates_title_company_city={soft_duplicate_rows} (groups={len(soft_duplicate_keys)})")
        self.stdout.write(
            f"window_duplicates_title_company_city_type_{window_days}d={window_duplicate_rows} (groups={window_duplicate_groups})"
        )
        self.stdout.write(
            f"hard_duplicates_title_company_city_type_date={hard_duplicate_rows} (groups={len(hard_duplicate_keys)})"
        )

        self.stdout.write("=== QUALITY CHECK ===")
        self.stdout.write(f"empty_title={empty_title}")
        self.stdout.write(f"short_title_lt5={short_title}")
        self.stdout.write(f"title_urlish={title_urlish}")
        self.stdout.write(f"empty_description={empty_description}")
        self.stdout.write(f"short_description_lt40={short_description}")
        self.stdout.write(f"empty_company={empty_company}")
        self.stdout.write(f"empty_city={empty_city}")
        self.stdout.write(f"raw_urls_total={len(raw_urls)}")
        self.stdout.write(f"raw_urls_invalid={invalid_url_count}")

        self.stdout.write("=== SOURCE DISTRIBUTION ===")
        self.stdout.write(f"top_source={top_source_name}")
        self.stdout.write(f"top_source_count={top_source_count}")
        self.stdout.write(f"top_source_ratio={top_source_ratio:.4f}")
        self.stdout.write(f"distribution={source_distribution}")

        self.stdout.write("=== ACTIVE SOURCE DISTRIBUTION ===")
        self.stdout.write(f"active_total_opportunities={active_total_opportunities}")
        self.stdout.write(f"active_top_source={active_top_source_name}")
        self.stdout.write(f"active_top_source_count={active_top_source_count}")
        self.stdout.write(f"active_top_source_ratio={active_top_source_ratio:.4f}")
        self.stdout.write(f"active_distribution={active_distribution}")

        if hard_duplicate_keys:
            self.stdout.write("=== SAMPLE HARD DUPLICATES ===")
            for key in hard_duplicate_keys[:sample_size]:
                self.stdout.write(f"key={key} count={triad_with_date_counter[key]}")
                for row in triad_with_date_examples[key][:3]:
                    self.stdout.write(f"- {row}")

        if options["strict"]:
            if window_duplicate_rows > 0:
                raise CommandError("Strict mode failed: rolling-window duplicates detected.")
            if invalid_url_count > 0:
                raise CommandError("Strict mode failed: invalid source URLs detected.")
            if top_source_ratio >= 0.90:
                raise CommandError("Strict mode failed: one source dominates >= 90% of the dataset.")
            if active_top_source_ratio >= active_dominance_threshold:
                raise CommandError(
                    "Strict mode failed: one source dominates the ACTIVE dataset "
                    f">= {active_dominance_threshold:.2f}."
                )

        self.stdout.write(self.style.SUCCESS("Dataset audit completed."))
