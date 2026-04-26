import re
from collections import defaultdict

from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count
from django.utils import timezone

from applications.models import Candidature, StatutSuiviCandidature
from opportunities.materialization.service import _merge_duplicate_fields
from opportunities.models import Opportunite, RawOpportunite, SourceOpportunite
from opportunities.scraping.sources.linkedin import (
    _build_job_fingerprint,
    _clean_description_container,
    _clean_text,
    _is_title_candidate,
)


STATUS_RANK = {
    StatutSuiviCandidature.VUE: 1,
    StatutSuiviCandidature.INTERESSEE: 2,
    StatutSuiviCandidature.POSTULEE_EXTERNEMENT: 3,
    StatutSuiviCandidature.ABANDONNEE: 0,
}


def _normalize_key_text(value):
    if value is None:
        return ""
    text = _clean_text(value).lower()
    text = "".join(ch if (ch.isalnum() or ch.isspace()) else " " for ch in text)
    return " ".join(text.split())


def _pick_first_non_empty(*values):
    for value in values:
        text = _clean_text(value)
        if text:
            return text
    return ""


def _title_candidate_from_url(url):
    value = _clean_text(url)
    if not value or "/jobs/view/" not in value:
        return ""

    slug = value.rstrip("/").rsplit("/jobs/view/", 1)[-1]
    slug = slug.split("?", 1)[0].strip().lower()
    if not slug:
        return ""

    slug = re.sub(r"-\d{6,}$", "", slug)
    slug = slug.split("-at-", 1)[0]
    slug = slug.replace("%E2%80%93", "-")
    text = slug.replace("-", " ").strip()
    if not text:
        return ""

    return " ".join(part.capitalize() for part in text.split())


def _title_candidates_from_html(html):
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    candidates = []
    for node in soup.select("h1, h2, h3, strong, b"):
        text = _clean_text(node.get_text(" ", strip=True))
        if text:
            candidates.append(text)
    return candidates


def _clean_description_fields(opportunity, raw_snapshot):
    payload = (raw_snapshot or {}).get("raw_payload") or {}
    html_candidates = [
        getattr(opportunity, "description_html", ""),
        payload.get("description_html"),
    ]

    for html in html_candidates:
        if not _clean_text(html):
            continue
        cleaned_text, cleaned_html = _clean_description_container(BeautifulSoup(str(html), "html.parser"))
        if cleaned_text:
            return cleaned_text, cleaned_html

    return _clean_text(opportunity.description), _clean_text(getattr(opportunity, "description_html", ""))


def _clean_title(opportunity, raw_snapshot):
    payload = (raw_snapshot or {}).get("raw_payload") or {}
    company_name = _pick_first_non_empty(
        opportunity.organisation_nom,
        (raw_snapshot or {}).get("raw_organisation_nom"),
        payload.get("organisation_nom"),
        payload.get("organization"),
        payload.get("company"),
    )
    location = _pick_first_non_empty(
        opportunity.ville,
        payload.get("ville"),
        payload.get("location"),
        payload.get("city"),
    )

    candidates = [
        opportunity.titre,
        (raw_snapshot or {}).get("raw_titre"),
        payload.get("title"),
        payload.get("titre"),
    ]
    candidates.append(
        _title_candidate_from_url(
            _pick_first_non_empty(
                opportunity.source_item_url,
                payload.get("source_item_url"),
                payload.get("url"),
            )
        )
    )
    candidates.extend(_title_candidates_from_html(getattr(opportunity, "description_html", "")))
    candidates.extend(_title_candidates_from_html(payload.get("description_html")))

    seen = set()
    fallback_candidates = []
    for candidate in candidates:
        text = _clean_text(candidate)
        if not text:
            continue
        key = _normalize_key_text(text)
        if key in seen:
            continue
        seen.add(key)
        fallback_candidates.append(text)
        if _is_title_candidate(text, company_name=company_name, location=location):
            return text

    if fallback_candidates:
        return max(fallback_candidates, key=len)

    return _clean_text(opportunity.titre)


def _build_cleanup_payload(opportunity, raw_snapshot):
    cleaned_title = _clean_title(opportunity, raw_snapshot)
    cleaned_description, cleaned_description_html = _clean_description_fields(opportunity, raw_snapshot)
    cleaned_location = _clean_text(opportunity.ville)
    cleaned_company = _clean_text(opportunity.organisation_nom)
    cleaned_external_id = _build_job_fingerprint(
        cleaned_title,
        cleaned_company,
        cleaned_location,
        cleaned_description,
    )
    return {
        "titre": cleaned_title,
        "description": cleaned_description,
        "description_html": cleaned_description_html,
        "external_id": cleaned_external_id,
    }


def _is_safe_duplicate(keeper, duplicate):
    keeper_company = _normalize_key_text(getattr(keeper, "organisation_nom", ""))
    duplicate_company = _normalize_key_text(getattr(duplicate, "organisation_nom", ""))
    keeper_city = _normalize_key_text(getattr(keeper, "ville", ""))
    duplicate_city = _normalize_key_text(getattr(duplicate, "ville", ""))

    if not keeper_company or keeper_company != duplicate_company:
        return False
    if not keeper_city or keeper_city != duplicate_city:
        return False

    keeper_date = getattr(keeper, "date_publication", None) or timezone.now().date()
    duplicate_date = getattr(duplicate, "date_publication", None) or timezone.now().date()
    return abs((keeper_date - duplicate_date).days) < 30


def _is_better_text(new_value, current_value):
    new_text = _clean_text(new_value)
    current_text = _clean_text(current_value)
    if not new_text:
        return False
    if not current_text:
        return True
    return len(new_text) > len(current_text) * 1.2


def _build_merge_defaults(keeper, duplicate):
    return {
        "source": keeper.source,
        "description": duplicate.description if _is_better_text(duplicate.description, keeper.description) else "",
        "description_html": (
            duplicate.description_html
            if _is_better_text(duplicate.description_html, keeper.description_html)
            else ""
        ),
        "organisation_nom": duplicate.organisation_nom,
        "company_logo": duplicate.company_logo,
        "ville": duplicate.ville,
        "source_item_url": duplicate.source_item_url,
        "external_id": keeper.external_id,
        "contract_type": duplicate.contract_type,
        "experience_min": duplicate.experience_min,
        "experience_max": duplicate.experience_max,
        "education_level": duplicate.education_level,
        "availability": duplicate.availability,
        "salary": duplicate.salary,
        "experience_years": duplicate.experience_years,
        "skills": duplicate.skills,
        "languages": duplicate.languages,
        "languages_fallback": duplicate.languages_fallback,
        "date_confidence": duplicate.date_confidence,
        "quality_score": duplicate.quality_score,
        "statut": duplicate.statut,
        "date_limite": duplicate.date_limite,
        "organisation": duplicate.organisation,
    }


def _keeper_sort_key(opportunity):
    return (
        1 if _is_title_candidate(getattr(opportunity, "cleanup_titre", ""), company_name=opportunity.organisation_nom, location=opportunity.ville) else 0,
        float(getattr(opportunity, "quality_score", 0.0) or 0.0),
        1 if _clean_text(getattr(opportunity, "cleanup_description_html", "")) else 0,
        len(_clean_text(getattr(opportunity, "cleanup_description", ""))),
        getattr(opportunity, "candidatures_count", 0),
        1 if _clean_text(getattr(opportunity, "source_item_url", "")) else 0,
        1 if _clean_text(getattr(opportunity, "company_logo", "")) else 0,
        getattr(opportunity, "date_publication", None) or timezone.now().date(),
        -int(opportunity.pk),
    )


def _sync_candidatures(duplicate, keeper, stats):
    for candidature in Candidature.objects.filter(opportunite=duplicate).prefetch_related("documents").select_related("candidat"):
        existing = Candidature.objects.filter(
            candidat=candidature.candidat,
            opportunite=keeper,
        ).first()

        if existing is not None:
            if STATUS_RANK.get(candidature.statut, 0) > STATUS_RANK.get(existing.statut, 0):
                existing.statut = candidature.statut
                existing.save(update_fields=["statut", "derniere_mise_a_jour"])

            if candidature.url_source and not existing.url_source:
                existing.url_source = candidature.url_source
                existing.save(update_fields=["url_source", "derniere_mise_a_jour"])

            moved_docs = candidature.documents.count()
            if moved_docs:
                candidature.documents.update(candidature=existing)
                stats["documents_relinked"] += moved_docs

            candidature.delete()
            stats["duplicate_candidatures_removed"] += 1
            continue

        candidature.opportunite = keeper
        candidature.save(update_fields=["opportunite", "derniere_mise_a_jour"])
        stats["candidatures_relinked"] += 1


class Command(BaseCommand):
    help = (
        "Clean and deduplicate canonical LinkedIn opportunities. "
        "Dry-run by default; use --apply to persist changes."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply cleanup changes. Without this flag, the command runs in dry-run mode.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=500,
            help="Maximum number of LinkedIn opportunities to inspect.",
        )
        parser.add_argument(
            "--ids",
            nargs="+",
            type=int,
            help="Optional explicit LinkedIn opportunity IDs to target.",
        )
        parser.add_argument(
            "--sample-size",
            type=int,
            default=5,
            help="Number of duplicate groups to print as examples.",
        )

    def handle(self, *args, **options):
        apply_changes = bool(options["apply"])
        limit = max(1, int(options["limit"] or 500))
        explicit_ids = options.get("ids") or []
        sample_size = max(1, int(options["sample_size"] or 5))

        source = SourceOpportunite.objects.filter(nom="LinkedIn").first()
        if source is None:
            self.stdout.write(self.style.WARNING("LinkedIn source not found. Nothing to clean."))
            return

        queryset = Opportunite.objects.filter(source=source)
        if explicit_ids:
            queryset = queryset.filter(id__in=explicit_ids)

        target_ids = list(queryset.order_by("id").values_list("id", flat=True)[:limit])
        if not target_ids:
            self.stdout.write(self.style.WARNING("No LinkedIn opportunities matched the cleanup scope."))
            return

        latest_raw_by_canonical = {}
        raw_queryset = (
            RawOpportunite.objects.filter(canonical_id__in=target_ids)
            .values("canonical_id", "raw_payload", "raw_titre", "raw_organisation_nom")
            .order_by("canonical_id", "-id")
        )
        for item in raw_queryset.iterator(chunk_size=500):
            canonical_id = item["canonical_id"]
            if canonical_id in latest_raw_by_canonical:
                continue
            latest_raw_by_canonical[canonical_id] = item

        opportunities = list(
            Opportunite.objects.filter(id__in=target_ids)
            .select_related("source")
            .order_by("id")
        )
        candidature_counts = {
            row["opportunite_id"]: row["count"]
            for row in Candidature.objects.filter(opportunite_id__in=target_ids)
            .values("opportunite_id")
            .annotate(count=Count("id"))
        }
        for opportunity in opportunities:
            opportunity.candidatures_count = int(candidature_counts.get(opportunity.id, 0) or 0)

        stats = {
            "inspected": len(opportunities),
            "title_updated": 0,
            "description_updated": 0,
            "description_html_updated": 0,
            "external_id_updated": 0,
            "invalid_titles_remaining": 0,
            "duplicate_groups": 0,
            "duplicate_rows": 0,
            "merged_rows": 0,
            "raw_relinked": 0,
            "candidatures_relinked": 0,
            "documents_relinked": 0,
            "duplicate_candidatures_removed": 0,
        }

        cleanup_plan = {}
        groups = defaultdict(list)

        for opportunity in opportunities:
            raw_snapshot = latest_raw_by_canonical.get(opportunity.id)
            cleaned = _build_cleanup_payload(opportunity, raw_snapshot)
            cleanup_plan[opportunity.id] = cleaned
            opportunity.cleanup_titre = cleaned["titre"]
            opportunity.cleanup_description = cleaned["description"]
            opportunity.cleanup_description_html = cleaned["description_html"]
            opportunity.cleanup_external_id = cleaned["external_id"]

            if cleaned["titre"] != _clean_text(opportunity.titre):
                stats["title_updated"] += 1
            if cleaned["description"] != _clean_text(opportunity.description):
                stats["description_updated"] += 1
            if cleaned["description_html"] != _clean_text(opportunity.description_html):
                stats["description_html_updated"] += 1
            if cleaned["external_id"] != _clean_text(opportunity.external_id):
                stats["external_id_updated"] += 1
            if not _is_title_candidate(cleaned["titre"], company_name=opportunity.organisation_nom, location=opportunity.ville):
                stats["invalid_titles_remaining"] += 1
                self.stdout.write(
                    f"[INVALID TITLE] id={opportunity.id} "
                    f"title='{cleaned['titre']}' "
                    f"company='{opportunity.organisation_nom}' "
                    f"location='{opportunity.ville}'"
                )

            if cleaned["external_id"]:
                groups[cleaned["external_id"]].append(opportunity)

        duplicate_groups = []
        for fingerprint, items in groups.items():
            if len(items) < 2:
                continue
            keeper = max(items, key=_keeper_sort_key)
            duplicates = [item for item in items if item.id != keeper.id and _is_safe_duplicate(keeper, item)]
            if not duplicates:
                continue
            duplicate_groups.append((fingerprint, keeper, duplicates))

        stats["duplicate_groups"] = len(duplicate_groups)
        stats["duplicate_rows"] = sum(len(duplicates) for _, _, duplicates in duplicate_groups)

        self.stdout.write("=== LINKEDIN CLEANUP PLAN ===")
        self.stdout.write(f"apply_changes={apply_changes}")
        self.stdout.write(f"target_rows={stats['inspected']}")
        self.stdout.write(f"title_updated={stats['title_updated']}")
        self.stdout.write(f"description_updated={stats['description_updated']}")
        self.stdout.write(f"description_html_updated={stats['description_html_updated']}")
        self.stdout.write(f"external_id_updated={stats['external_id_updated']}")
        self.stdout.write(f"invalid_titles_remaining={stats['invalid_titles_remaining']}")
        self.stdout.write(f"duplicate_groups={stats['duplicate_groups']}")
        self.stdout.write(f"duplicate_rows={stats['duplicate_rows']}")

        for fingerprint, keeper, duplicates in duplicate_groups[:sample_size]:
            self.stdout.write(
                f"sample_duplicate_group fingerprint={fingerprint} keeper={keeper.id} "
                f"duplicates={[item.id for item in duplicates]}"
            )

        if not apply_changes:
            self.stdout.write(self.style.SUCCESS("Dry-run completed. Re-run with --apply to execute cleanup."))
            return

        for opportunity in opportunities:
            cleaned = cleanup_plan[opportunity.id]
            update_fields = []

            if cleaned["titre"] and cleaned["titre"] != _clean_text(opportunity.titre):
                opportunity.titre = cleaned["titre"][: Opportunite._meta.get_field("titre").max_length]
                update_fields.append("titre")
            if cleaned["description"] and cleaned["description"] != _clean_text(opportunity.description):
                opportunity.description = cleaned["description"]
                update_fields.append("description")
            if cleaned["description_html"] != _clean_text(opportunity.description_html):
                opportunity.description_html = cleaned["description_html"]
                update_fields.append("description_html")
            if cleaned["external_id"] != _clean_text(opportunity.external_id):
                opportunity.external_id = cleaned["external_id"][: Opportunite._meta.get_field("external_id").max_length]
                update_fields.append("external_id")

            if update_fields:
                opportunity.date_modification = timezone.now()
                update_fields.append("date_modification")
                opportunity.save(update_fields=update_fields)

        for _, keeper, duplicates in duplicate_groups:
            with transaction.atomic():
                for duplicate in duplicates:
                    update_fields = _merge_duplicate_fields(keeper, _build_merge_defaults(keeper, duplicate))
                    if update_fields:
                        keeper.date_modification = timezone.now()
                        update_fields.append("date_modification")
                        keeper.save(update_fields=update_fields)

                    raw_count = RawOpportunite.objects.filter(canonical_id=duplicate.id).update(canonical_id=keeper.id)
                    stats["raw_relinked"] += raw_count

                    _sync_candidatures(duplicate, keeper, stats)
                    duplicate.delete()
                    stats["merged_rows"] += 1

        self.stdout.write("=== LINKEDIN CLEANUP RESULT ===")
        self.stdout.write(f"merged_rows={stats['merged_rows']}")
        self.stdout.write(f"raw_relinked={stats['raw_relinked']}")
        self.stdout.write(f"candidatures_relinked={stats['candidatures_relinked']}")
        self.stdout.write(f"documents_relinked={stats['documents_relinked']}")
        self.stdout.write(f"duplicate_candidatures_removed={stats['duplicate_candidatures_removed']}")
        self.stdout.write(self.style.SUCCESS("LinkedIn cleanup completed."))
