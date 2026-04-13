import django_filters
from django.db.models import F, Func, IntegerField, Value
from django.db.models.functions import Cast, NullIf

from .models import Opportunite, StatutOpportunite, TypeOpportunite
from .scraping.normalization import normalize_city_name


class OpportuniteFilterSet(django_filters.FilterSet):
    # English alias kept for API ergonomics while preserving model field names.
    status = django_filters.ChoiceFilter(
        field_name="statut",
        choices=StatutOpportunite.choices,
    )
    statut = django_filters.ChoiceFilter(choices=StatutOpportunite.choices)
    type = django_filters.ChoiceFilter(
        field_name="type_opportunite",
        choices=TypeOpportunite.choices,
    )
    type_opportunite = django_filters.ChoiceFilter(choices=TypeOpportunite.choices)
    city = django_filters.CharFilter(method="filter_city")
    ville = django_filters.CharFilter(method="filter_ville")
    min_salary = django_filters.NumberFilter(method="filter_min_salary")
    source = django_filters.NumberFilter(field_name="source_id")

    def filter_city(self, queryset, _name, value):
        return self.filter_ville(queryset, "ville", value)

    def filter_ville(self, queryset, _name, value):
        canonical_city = normalize_city_name(value)
        if not canonical_city:
            return queryset
        return queryset.filter(ville__iexact=canonical_city)

    def filter_min_salary(self, queryset, _name, value):
        if value in (None, ""):
            return queryset

        try:
            min_salary = int(float(value))
        except (TypeError, ValueError):
            return queryset

        if min_salary <= 0:
            return queryset

        # Normalize free-text salary values (e.g., "1 500 TND") to digits.
        salary_digits = Func(
            F("salary"),
            Value(r"[^0-9]"),
            Value(""),
            Value("g"),
            function="REGEXP_REPLACE",
        )

        return queryset.annotate(
            _salary_numeric=Cast(
                NullIf(salary_digits, Value("")),
                IntegerField(),
            )
        ).filter(_salary_numeric__gte=min_salary)

    class Meta:
        model = Opportunite
        fields = [
            "type",
            "type_opportunite",
            "statut",
            "status",
            "city",
            "ville",
            "min_salary",
            "source",
        ]
