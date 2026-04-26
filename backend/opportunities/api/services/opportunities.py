from django.db import connection
from django.db.models import Case, F, IntegerField, Value, When, Window
from django.db.models.functions import RowNumber

from opportunities.models import Opportunite, StatutOpportunite, TypeOpportunite


def build_opportunity_queryset(*, request, action, base_ordering):
    queryset = Opportunite.objects.select_related("source", "organisation").all()
    ordering = list(base_ordering) if isinstance(base_ordering, (list, tuple)) else [base_ordering]

    if action != "list":
        return queryset, ordering

    statut_param = request.query_params.get("statut")
    status_param = request.query_params.get("status")
    if not statut_param and not status_param:
        queryset = queryset.filter(statut=StatutOpportunite.ACTIVE)

    source_param = request.query_params.get("source")
    diversify_param = str(request.query_params.get("diversify_sources", "1")).strip().lower()
    source_cap_param = request.query_params.get("source_cap")
    diversify_enabled = diversify_param not in {"0", "false", "no", "off"}
    type_param = str(request.query_params.get("type_opportunite", "")).strip().upper()
    stage_requested = type_param == TypeOpportunite.STAGE

    if stage_requested and not source_param:
        queryset = queryset.annotate(
            _stage_source_priority=Case(
                When(source__nom="Keejob", then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            )
        )

    try:
        source_cap = int(source_cap_param) if source_cap_param else 0
    except (TypeError, ValueError):
        source_cap = 0

    if (
        diversify_enabled
        and not source_param
        and source_cap > 0
        and connection.features.supports_over_clause
    ):
        queryset = queryset.annotate(
            _source_rank=Window(
                expression=RowNumber(),
                partition_by=[F("source_id")],
                order_by=[F("date_publication").desc(), F("id").desc()],
            )
        ).filter(_source_rank__lte=source_cap)
        if not request.query_params.get("ordering"):
            if stage_requested and not source_param:
                ordering = ["_stage_source_priority", "_source_rank", "-date_publication", "-id"]
            else:
                ordering = ["_source_rank", "-date_publication", "-id"]
    elif stage_requested and not source_param and not request.query_params.get("ordering"):
        ordering = ["_stage_source_priority", "-date_publication", "-id"]

    return queryset, ordering
