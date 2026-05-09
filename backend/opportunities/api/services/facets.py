import hashlib
import json

from django.conf import settings
from django.core.cache import cache
from django.db.models import Case, Count, Q, Value, When


FACET_CACHE_TTL_SECONDS = int(getattr(settings, "OPPORTUNITY_FACET_CACHE_TTL_SECONDS", 60))
FACET_CACHE_VERSION = str(getattr(settings, "OPPORTUNITY_FACET_CACHE_VERSION", "v1"))
FACET_QUERY_PARAMS = (
    "search",
    "type",
    "type_opportunite",
    "location",
    "city",
    "ville",
    "source",
    "work_mode",
    "experience_level",
    "status",
    "statut",
    "min_salary",
    "source_cap",
    "diversify_sources",
)

FACET_LIMITS = {
    "types": 20,
    "locations": 30,
    "sources": 30,
    "work_modes": 10,
    "experience_levels": 10,
    "statuses": 10,
}


def _facet_cache_key(query_params):
    payload = {
        key: query_params.getlist(key) if hasattr(query_params, "getlist") else query_params.get(key)
        for key in FACET_QUERY_PARAMS
        if query_params.get(key) not in (None, "")
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return f"opportunities:facets:{FACET_CACHE_VERSION}:{digest}"


def _count_values(queryset, field, *, exclude_blank=True, limit=20, key_alias="key"):
    facet_queryset = queryset.order_by()
    if exclude_blank:
        facet_queryset = facet_queryset.exclude(Q(**{f"{field}__isnull": True}) | Q(**{field: ""}))

    return [
        {"key": item[field], "count": item["count"]}
        for item in (
            facet_queryset
            .values(field)
            .annotate(count=Count("id"))
            .order_by("-count", field)[:limit]
        )
        if item[field] not in (None, "")
    ]


def _source_facets(queryset):
    return [
        {
            "key": item["source__nom"],
            "id": item["source_id"],
            "count": item["count"],
        }
        for item in (
            queryset.order_by()
            .exclude(source__nom="")
            .values("source_id", "source__nom")
            .annotate(count=Count("id"))
            .order_by("-count", "source__nom")[:FACET_LIMITS["sources"]]
        )
        if item["source__nom"]
    ]


def _experience_facets(queryset):
    level_case = Case(
        When(experience_min__lte=1, then=Value("entry")),
        When(experience_min__lte=2, then=Value("junior")),
        When(experience_min__lte=5, then=Value("mid")),
        When(experience_min__gt=5, then=Value("senior")),
        default=Value(""),
    )
    return [
        {"key": item["experience_level"], "count": item["count"]}
        for item in (
            queryset.order_by()
            .exclude(experience_min__isnull=True)
            .annotate(experience_level=level_case)
            .exclude(experience_level="")
            .values("experience_level")
            .annotate(count=Count("id"))
            .order_by("-count", "experience_level")[:FACET_LIMITS["experience_levels"]]
        )
    ]


def build_opportunity_facets(queryset):
    return {
        "types": _count_values(
            queryset,
            "type_opportunite",
            limit=FACET_LIMITS["types"],
        ),
        "locations": _count_values(
            queryset,
            "ville",
            limit=FACET_LIMITS["locations"],
        ),
        "sources": _source_facets(queryset),
        "work_modes": _count_values(
            queryset.exclude(normalized_work_mode="UNSPECIFIED"),
            "normalized_work_mode",
            limit=FACET_LIMITS["work_modes"],
        ),
        "experience_levels": _experience_facets(queryset),
        "statuses": _count_values(
            queryset,
            "statut",
            limit=FACET_LIMITS["statuses"],
        ),
    }


def get_cached_opportunity_facets(queryset, query_params):
    cache_key = _facet_cache_key(query_params)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    facets = build_opportunity_facets(queryset)
    cache.set(cache_key, facets, timeout=FACET_CACHE_TTL_SECONDS)
    return facets
