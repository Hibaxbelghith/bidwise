from datetime import timedelta

import django_filters
from django.utils import timezone
from django.db.models import F, Func, IntegerField, Q, Value
from django.db.models.functions import Cast, NullIf

from .models import Opportunite, StatutOpportunite, TypeOpportunite
from .normalization import normalize_city_name
from .normalization.industries import industry_alias_keys_for, normalize_industries
from .normalization.text import normalize_lookup_key


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
    location = django_filters.CharFilter(method="filter_location")
    city = django_filters.CharFilter(method="filter_city")
    ville = django_filters.CharFilter(method="filter_ville")
    min_salary = django_filters.NumberFilter(method="filter_min_salary")
    source = django_filters.CharFilter(method="filter_source")
    work_mode = django_filters.CharFilter(method="filter_work_mode")
    experience_level = django_filters.CharFilter(method="filter_experience_level")
    date_posted = django_filters.CharFilter(method="filter_date_posted")
    deadline_window = django_filters.CharFilter(method="filter_deadline_window")
    sector = django_filters.CharFilter(method="filter_sector")
    industry = django_filters.CharFilter(method="filter_sector")

    def filter_location(self, queryset, _name, value):
        return self.filter_ville(queryset, "ville", value)

    def filter_city(self, queryset, _name, value):
        return self.filter_ville(queryset, "ville", value)

    def filter_ville(self, queryset, _name, value):
        canonical_city = normalize_city_name(value)
        if not canonical_city:
            return queryset
        return queryset.filter(ville__iexact=canonical_city)

    def filter_source(self, queryset, _name, value):
        normalized = str(value or "").strip()
        if not normalized:
            return queryset
        if normalized.isdigit():
            return queryset.filter(source_id=int(normalized))
        return queryset.filter(source__nom__iexact=normalized)

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

    def filter_work_mode(self, queryset, _name, value):
        normalized = str(value or "").strip().upper()
        if normalized not in {"REMOTE", "HYBRID", "ON_SITE"}:
            return queryset
        return queryset.filter(normalized_work_mode=normalized)

    def filter_experience_level(self, queryset, _name, value):
        normalized = str(value or "").strip().lower()
        if normalized == "entry":
            return queryset.filter(experience_min__lte=1)
        if normalized == "junior":
            return queryset.filter(experience_min__lte=2, experience_max__lte=3)
        if normalized == "mid":
            return queryset.filter(experience_min__gte=2, experience_min__lte=5)
        if normalized == "senior":
            return queryset.filter(experience_min__gte=5)
        return queryset

    def filter_date_posted(self, queryset, _name, value):
        normalized = str(value or "").strip().lower()
        days_by_value = {
            "day": 1,
            "24h": 1,
            "3days": 3,
            "week": 7,
            "2weeks": 14,
            "month": 30,
        }
        days = days_by_value.get(normalized)
        if not days:
            return queryset

        cutoff = timezone.localdate() - timedelta(days=days)
        return queryset.filter(date_publication__gte=cutoff)

    def filter_deadline_window(self, queryset, _name, value):
        normalized = str(value or "").strip().lower()
        days_by_value = {
            "week": 7,
            "month": 30,
        }
        days = days_by_value.get(normalized)
        if not days:
            return queryset

        today = timezone.localdate()
        deadline = today + timedelta(days=days)
        return queryset.filter(date_limite__gte=today, date_limite__lte=deadline)

    def filter_sector(self, queryset, _name, value):
        raw_value = str(value or "").strip()
        lookup_key = normalize_lookup_key(raw_value)
        if not lookup_key:
            return queryset

        canonical_values = normalize_industries(raw_value)
        query = Q(extra_data__company_sector__icontains=raw_value)
        compact_lookup = lookup_key.replace(" ", "")
        for part in lookup_key.split():
            if len(part) >= 3:
                query |= Q(extra_data__company_sector__icontains=part)
        for canonical in canonical_values:
            query |= Q(normalized_industries__contains=[canonical])
            for alias in industry_alias_keys_for(canonical):
                compact_alias = alias.replace(" ", "")
                if compact_alias != compact_lookup:
                    continue
                query |= Q(extra_data__company_sector__icontains=alias)
                query |= Q(extra_data__company_sector__icontains=alias.replace(" ", "-"))

        return queryset.filter(query).distinct()

    class Meta:
        model = Opportunite
        fields = [
            "type",
            "type_opportunite",
            "statut",
            "status",
            "location",
            "city",
            "ville",
            "min_salary",
            "source",
            "work_mode",
            "experience_level",
            "date_posted",
            "deadline_window",
            "sector",
            "industry",
        ]
