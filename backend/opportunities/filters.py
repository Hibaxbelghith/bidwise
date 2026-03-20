import django_filters

from .models import Opportunite, StatutOpportunite, TypeOpportunite


class OpportuniteFilterSet(django_filters.FilterSet):
    # English alias kept for API ergonomics while preserving model field names.
    status = django_filters.ChoiceFilter(
        field_name="statut",
        choices=StatutOpportunite.choices,
    )
    statut = django_filters.ChoiceFilter(choices=StatutOpportunite.choices)
    type_opportunite = django_filters.ChoiceFilter(choices=TypeOpportunite.choices)
    source = django_filters.NumberFilter(field_name="source_id")

    class Meta:
        model = Opportunite
        fields = ["type_opportunite", "statut", "status", "source"]
