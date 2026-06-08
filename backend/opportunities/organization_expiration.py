from __future__ import annotations

from datetime import date

from django.db import transaction
from django.utils import timezone

from .models import Opportunite, StatutOpportunite, TypeOpportunite


def _parse_iso_date(value) -> date | None:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value or "").strip())
    except (TypeError, ValueError):
        return None


def _seasonal_end_date(opportunity: Opportunite) -> date | None:
    if opportunity.type_opportunite != TypeOpportunite.SAISONNIER:
        return None
    extra_data = opportunity.extra_data if isinstance(opportunity.extra_data, dict) else {}
    details = extra_data.get("seasonal_details")
    if not isinstance(details, dict):
        return None
    return _parse_iso_date(details.get("end_date"))


def expire_due_organization_opportunities(*, today: date | None = None) -> dict:
    current_date = today or timezone.localdate()
    candidates = list(
        Opportunite.objects.filter(
            organisation__isnull=False,
            statut=StatutOpportunite.ACTIVE,
        ).only(
            "id",
            "type_opportunite",
            "statut",
            "date_limite",
            "extra_data",
            "date_modification",
        )
    )

    expired = []
    by_reason = {"deadline": 0, "seasonal_end_date": 0}
    now = timezone.now()

    for opportunity in candidates:
        reason = None
        if opportunity.date_limite and opportunity.date_limite < current_date:
            reason = "deadline"
        else:
            seasonal_end = _seasonal_end_date(opportunity)
            if seasonal_end and seasonal_end < current_date:
                reason = "seasonal_end_date"

        if reason is None:
            continue

        extra_data = dict(opportunity.extra_data or {})
        extra_data["expiration"] = {
            "reason": reason,
            "expired_on": current_date.isoformat(),
            "automatic": True,
        }
        opportunity.extra_data = extra_data
        opportunity.statut = StatutOpportunite.EXPIREE
        opportunity.date_modification = now
        expired.append(opportunity)
        by_reason[reason] += 1

    if expired:
        with transaction.atomic():
            Opportunite.objects.bulk_update(
                expired,
                ["statut", "extra_data", "date_modification"],
                batch_size=200,
            )

    return {
        "date": current_date.isoformat(),
        "inspected": len(candidates),
        "expired": len(expired),
        "expired_ids": [opportunity.id for opportunity in expired],
        "by_reason": by_reason,
    }
