import re

from django.contrib.postgres.search import (
    SearchQuery,
    SearchRank,
    SearchVector,
    TrigramSimilarity,
    TrigramWordSimilarity,
)
from django.db import connection
from django.db.models import Case, FloatField, Q, Value, When
from django.db.models.functions import Greatest


SEARCH_FIELDS = ("titre", "organisation_nom", "ville", "description")
SEARCH_MIN_LENGTH = 2
TRIGRAM_SIMILARITY_THRESHOLD = 0.12
SEARCH_TERM_PATTERN = re.compile(r"[\w]+", re.UNICODE)

SORT_ORDERINGS = {
    "quality": ["-quality_score", "-date_publication", "-id"],
    "newest": ["-date_publication", "-date_creation", "-id"],
    "created": ["-date_creation", "-id"],
    "deadline": ["date_limite", "-quality_score", "-id"],
    "relevance": ["-title_match_rank", "-search_rank", "-quality_score", "-date_publication", "-id"],
}


def normalize_search_query(value):
    return " ".join(str(value or "").strip().split())


def build_prefix_search_query(value):
    terms = [term for term in SEARCH_TERM_PATTERN.findall(value) if len(term) >= SEARCH_MIN_LENGTH]
    if not terms:
        return value
    return " & ".join(f"{term}:*" for term in terms)


def get_sort_ordering(sort_value, *, has_search=False):
    normalized = str(sort_value or "").strip().lower()
    if not normalized:
        normalized = "relevance" if has_search else "quality"
    if normalized == "recent":
        normalized = "newest"
    if normalized == "date":
        normalized = "newest"

    ordering = SORT_ORDERINGS.get(normalized, SORT_ORDERINGS["quality"])
    if normalized == "relevance" and not has_search:
        return SORT_ORDERINGS["quality"]
    return ordering


def apply_opportunity_search(queryset, raw_query):
    query = normalize_search_query(raw_query)
    if len(query) < SEARCH_MIN_LENGTH:
        return queryset, False

    if connection.vendor == "postgresql":
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT set_config('pg_trgm.similarity_threshold', %s, false)",
                [str(TRIGRAM_SIMILARITY_THRESHOLD)],
            )
            cursor.execute(
                "SELECT set_config('pg_trgm.word_similarity_threshold', %s, false)",
                [str(TRIGRAM_SIMILARITY_THRESHOLD)],
            )

    search_filter = Q()
    for field in SEARCH_FIELDS:
        if connection.vendor != "postgresql":
            search_filter |= Q(**{f"{field}__icontains": query})
        elif field != "description":
            search_filter |= Q(**{f"{field}__trigram_similar": query})
            search_filter |= Q(**{f"{field}__trigram_word_similar": query})

    if connection.vendor == "postgresql":
        search_filter |= Q(titre__icontains=query)

    title_match_rank = Case(
        When(titre__iexact=query, then=Value(3.0)),
        When(titre__istartswith=query, then=Value(2.0)),
        When(titre__icontains=query, then=Value(1.0)),
        default=Value(0.0),
        output_field=FloatField(),
    )

    if connection.vendor != "postgresql":
        return queryset.annotate(
            title_match_rank=title_match_rank,
            search_rank=Value(0.0, output_field=FloatField()),
        ).filter(search_filter), True

    search_vector = (
        SearchVector("titre", weight="A", config="simple")
        + SearchVector("organisation_nom", weight="B", config="simple")
        + SearchVector("ville", weight="C", config="simple")
        + SearchVector("description", weight="D", config="simple")
    )
    search_query = SearchQuery(build_prefix_search_query(query), search_type="raw", config="simple")

    queryset = queryset.annotate(
        search_document=search_vector,
        title_match_rank=title_match_rank,
        search_rank=Greatest(
            SearchRank(search_vector, search_query),
            TrigramWordSimilarity(query, "titre"),
            TrigramSimilarity("titre", query),
            TrigramWordSimilarity(query, "organisation_nom"),
            TrigramSimilarity("organisation_nom", query),
            TrigramWordSimilarity(query, "ville"),
            TrigramSimilarity("ville", query),
            Value(0.0),
            output_field=FloatField(),
        ),
    )
    return queryset.filter(Q(search_document=search_query) | search_filter), True
