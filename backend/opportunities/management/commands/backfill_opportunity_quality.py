from django.core.management.base import BaseCommand

from opportunities.models import Opportunite, RawOpportunite, StatutOpportunite, TypeOpportunite
from opportunities.scoring.quality import (
    compute_quality_score,
    infer_date_confidence,
    normalize_date_confidence,
)
from opportunities.scraping.scraper_utils import (
    clean_location_for_ml,
    infer_city_from_text,
    infer_opportunity_type,
    infer_organization_from_text,
    infer_organization_from_title,
    looks_closed_opportunity,
    normalize_organization_name,
)


class Command(BaseCommand):
    help = (
        "Backfill organization/city/status/type/date_confidence/quality_score using "
        "current quality policy."
    )
    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply changes. Without this flag, the command runs in dry-run mode.",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=500,
            help="Batch size for queryset iteration and bulk updates.",
        )
        parser.add_argument(
            "--active-only",
            action="store_true",
            help="Restrict processing to active opportunities.",
        )

    def handle(self, *args, **options):
        apply_changes = bool(options["apply"])
        batch_size = max(50, int(options["batch_size"] or 500))
        active_only = bool(options["active_only"])

        def _pick_payload_value(payload, *keys):
            if not isinstance(payload, dict):
                return ""
            for key in keys:
                value = payload.get(key)
                if value is None:
                    continue
                text = str(value).strip()
                if text:
                    return text
            return ""

        def _drop_anonymous_placeholder(value):
            text = str(value or "").strip()
            return "" if text.lower() == "entreprise anonyme" else text

        queryset = Opportunite.objects.select_related("source").all()
        if active_only:
            queryset = queryset.filter(statut=StatutOpportunite.ACTIVE)

        latest_raw_by_canonical = {}
        raw_queryset = RawOpportunite.objects.filter(canonical__isnull=False).values(
            "canonical_id",
            "raw_payload",
            "raw_titre",
            "raw_description",
            "raw_organisation_nom",
            "raw_date_publication",
            "source_item_url",
        ).order_by("canonical_id", "-id")
        for item in raw_queryset.iterator(chunk_size=batch_size):
            canonical_id = item["canonical_id"]
            if canonical_id in latest_raw_by_canonical:
                continue
            latest_raw_by_canonical[canonical_id] = item

        total = queryset.count()
        updated_count = 0
        city_backfilled = 0
        org_normalized = 0
        archived_low_info = 0
        date_confidence_updated = 0
        quality_scored = 0
        status_closed_corrected = 0

        pending_updates = []
        fields = ["organisation_nom", "ville", "statut", "type_opportunite", "date_confidence", "quality_score", "skills"]
        type_corrected = 0

        for opportunity in queryset.iterator(chunk_size=batch_size):
            original_org = (opportunity.organisation_nom or "").strip()
            original_city = (opportunity.ville or "").strip()
            original_status = opportunity.statut
            source_name = getattr(opportunity.source, "nom", "")
            source_status_is_authoritative = source_name in {"Keejob", "EmploiTunisie", "MarchesPublics"}

            raw_snapshot = latest_raw_by_canonical.get(opportunity.id, {})
            payload = raw_snapshot.get("raw_payload") or {}
            raw_org = _drop_anonymous_placeholder(raw_snapshot.get("raw_organisation_nom"))
            raw_titre = str(raw_snapshot.get("raw_titre") or "").strip()
            raw_description = str(raw_snapshot.get("raw_description") or "").strip()
            payload_org = normalize_organization_name(
                _drop_anonymous_placeholder(
                    _pick_payload_value(
                        payload,
                        "organisation_nom",
                        "organisation",
                        "organization",
                        "organization_name",
                        "company",
                        "employer",
                        "buyer",
                        "acheteur",
                        "organisme",
                    )
                )
            )
            payload_city = _pick_payload_value(
                payload,
                "ville",
                "location",
                "city",
                "gouvernorat",
                "region",
                "lieu",
            )
            payload_url = str(raw_snapshot.get("source_item_url") or _pick_payload_value(payload, "url")).strip()
            raw_date_value = str(raw_snapshot.get("raw_date_publication") or "").strip()

            cleaned_org = normalize_organization_name(_drop_anonymous_placeholder(original_org))
            inferred_org_title = infer_organization_from_title(opportunity.titre or raw_titre)
            inferred_org_text = infer_organization_from_text(
                opportunity.titre,
                opportunity.description,
                raw_titre,
                raw_description,
                payload_org,
                raw_org,
            )

            normalized_org = (
                cleaned_org
                or payload_org
                or inferred_org_title
                or inferred_org_text
                or original_org
                or raw_org
            )

            normalized_city = clean_location_for_ml(original_city)
            if not normalized_city:
                normalized_city = clean_location_for_ml(payload_city)
            if not normalized_city:
                normalized_city = infer_city_from_text(
                    opportunity.titre,
                    opportunity.description,
                    raw_titre,
                    raw_description,
                    payload_city,
                    payload_url,
                    original_org,
                    raw_org,
                    source_name,
                )

            next_status = original_status
            next_type = opportunity.type_opportunite
            if source_name == "EmploiTunisie" and opportunity.type_opportunite == TypeOpportunite.STAGE:
                inferred_type = infer_opportunity_type(
                    opportunity.titre,
                    opportunity.description,
                    raw_titre,
                    raw_description,
                )
                if inferred_type == TypeOpportunite.EMPLOI:
                    next_type = TypeOpportunite.EMPLOI

            if not source_status_is_authoritative and looks_closed_opportunity(
                opportunity.titre,
                opportunity.description,
                raw_titre,
                raw_description,
            ):
                next_status = StatutOpportunite.EXPIREE

            has_org = bool(normalize_organization_name(normalized_org))
            has_city = bool(normalized_city)
            if next_status == StatutOpportunite.ACTIVE:
                if (
                    next_type in (TypeOpportunite.STAGE, TypeOpportunite.EMPLOI)
                    and not (has_org or has_city)
                ):
                    next_status = StatutOpportunite.ARCHIVEE
            changed = False
            if normalized_org != original_org:
                opportunity.organisation_nom = normalized_org
                org_normalized += 1
                changed = True

            if normalized_city != original_city:
                opportunity.ville = normalized_city
                city_backfilled += 1
                changed = True

            if next_status != original_status:
                opportunity.statut = next_status
                archived_low_info += 1
                if next_status == StatutOpportunite.EXPIREE:
                    status_closed_corrected += 1
                changed = True

            if next_type != opportunity.type_opportunite:
                opportunity.type_opportunite = next_type
                type_corrected += 1
                changed = True

            if next_type == TypeOpportunite.PROJET and opportunity.skills:
                opportunity.skills = []
                changed = True

            payload_confidence = _pick_payload_value(payload, "date_confidence", "publication_date_confidence")
            inferred_confidence = normalize_date_confidence(
                payload_confidence
                or infer_date_confidence(
                    raw_date_value
                    or _pick_payload_value(payload, "date_publication", "publication_date")
                    or opportunity.date_publication.isoformat()
                )
            )
            if inferred_confidence != (opportunity.date_confidence or ""):
                opportunity.date_confidence = inferred_confidence
                date_confidence_updated += 1
                changed = True

            computed_quality_score = compute_quality_score(
                titre=opportunity.titre,
                organisation_nom=normalized_org,
                ville=normalized_city,
                description=opportunity.description,
                source_item_url=payload_url,
                date_confidence=inferred_confidence,
                skills=opportunity.skills,
                source_name=getattr(opportunity.source, "nom", ""),
                description_html=getattr(opportunity, "description_html", ""),
                contract_type=getattr(opportunity, "contract_type", ""),
                availability=getattr(opportunity, "availability", ""),
                education_level=getattr(opportunity, "education_level", ""),
                type_opportunite=getattr(opportunity, "type_opportunite", ""),
                date_publication=getattr(opportunity, "date_publication", None),
                date_limite=getattr(opportunity, "date_limite", None),
                extra_data=getattr(opportunity, "extra_data", None),
            )

            if abs(float(opportunity.quality_score or 0.0) - float(computed_quality_score)) > 1e-9:
                opportunity.quality_score = computed_quality_score
                quality_scored += 1
                changed = True

            if changed:
                pending_updates.append(opportunity)

            if apply_changes and len(pending_updates) >= batch_size:
                Opportunite.objects.bulk_update(pending_updates, fields=fields, batch_size=batch_size)
                updated_count += len(pending_updates)
                pending_updates = []

        if apply_changes and pending_updates:
            Opportunite.objects.bulk_update(pending_updates, fields=fields, batch_size=batch_size)
            updated_count += len(pending_updates)

        if not apply_changes:
            updated_count = len(pending_updates)

        mode = "APPLY" if apply_changes else "DRY-RUN"
        self.stdout.write(f"=== BACKFILL QUALITY ({mode}) ===")
        self.stdout.write(f"scanned={total}")
        self.stdout.write(f"would_update={updated_count}" if not apply_changes else f"updated={updated_count}")
        self.stdout.write(f"organization_normalized={org_normalized}")
        self.stdout.write(f"city_backfilled={city_backfilled}")
        self.stdout.write(f"archived_low_info={archived_low_info}")
        self.stdout.write(f"status_closed_corrected={status_closed_corrected}")
        self.stdout.write(f"type_corrected={type_corrected}")
        self.stdout.write(f"date_confidence_updated={date_confidence_updated}")
        self.stdout.write(f"quality_scored={quality_scored}")
