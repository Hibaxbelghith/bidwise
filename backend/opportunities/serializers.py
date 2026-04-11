from rest_framework import serializers
from .models import Opportunite, SourceOpportunite


class SourceOpportuniteSerializer(serializers.ModelSerializer):
    class Meta:
        model = SourceOpportunite
        fields = ['id', 'nom', 'url', 'type_source']


class OpportuniteSerializer(serializers.ModelSerializer):
    source_item_url = serializers.URLField(read_only=True, allow_null=True)
    contract_type = serializers.SerializerMethodField(read_only=True)
    education_level = serializers.SerializerMethodField(read_only=True)
    availability = serializers.SerializerMethodField(read_only=True)
    experience = serializers.SerializerMethodField(read_only=True)
    salary = serializers.SerializerMethodField(read_only=True)
    skills = serializers.SerializerMethodField(read_only=True)
    languages = serializers.SerializerMethodField(read_only=True)
    languages_fallback = serializers.SerializerMethodField(read_only=True)
    source = SourceOpportuniteSerializer(read_only=True)
    source_id = serializers.PrimaryKeyRelatedField(
        queryset=SourceOpportunite.objects.all(), source='source', write_only=True
    )

    class Meta:
        model = Opportunite
        fields = [
            "id",
            "titre",
            "description",
            "organisation_nom",
            "ville",
            "date_confidence",
            "quality_score",
            "type_opportunite",
            "statut",
            "date_publication",
            "date_limite",
            "source_item_url",
            "contract_type",
            "experience",
            "education_level",
            "availability",
            "salary",
            "skills",
            "languages",
            "languages_fallback",
            "source",
            "source_id",
            "date_creation",
            "date_modification",
        ]
        read_only_fields = [
            "id",
            "date_confidence",
            "quality_score",
            "date_creation",
            "date_modification",
        ]

    @staticmethod
    def _as_list_of_text(value):
        if not isinstance(value, list):
            return None

        cleaned = []
        for item in value:
            text = str(item).strip()
            if text and text not in cleaned:
                cleaned.append(text)
        return cleaned or None

    def get_salary(self, obj):
        value = getattr(obj, "salary", None)
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _get_optional_text(self, obj, field_name):
        value = getattr(obj, field_name, None)
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def get_contract_type(self, obj):
        return self._get_optional_text(obj, "contract_type")

    def get_education_level(self, obj):
        return self._get_optional_text(obj, "education_level")

    def get_availability(self, obj):
        return self._get_optional_text(obj, "availability")

    def get_experience(self, obj):
        legacy_years = getattr(obj, "experience_years", None)
        min_value = getattr(obj, "experience_min", None)
        max_value = getattr(obj, "experience_max", None)

        if min_value is None:
            min_value = legacy_years
        if max_value is None:
            max_value = legacy_years

        return {
            "min": min_value,
            "max": max_value,
        }

    def get_skills(self, obj):
        value = self._as_list_of_text(getattr(obj, "skills", None))
        return value or []

    def get_languages(self, obj):
        return self._as_list_of_text(getattr(obj, "languages", None))

    def get_languages_fallback(self, obj):
        return self._as_list_of_text(getattr(obj, "languages_fallback", None))

    def to_internal_value(self, data):
        # Keep API backward-compatible: ignore legacy owner payload key.
        if isinstance(data, dict):
            data = data.copy()
            data.pop("organisation", None)
        return super().to_internal_value(data)

    def validate(self, attrs):
        """Business rule: date_limite must be >= date_publication when set."""
        # Support both create and partial update by falling back to instance values.
        date_publication = attrs.get('date_publication') or getattr(self.instance, 'date_publication', None)
        date_limite = attrs.get('date_limite') if 'date_limite' in attrs else getattr(self.instance, 'date_limite', None)

        if date_limite and date_publication and date_limite < date_publication:
            raise serializers.ValidationError({
                'date_limite': "La date limite ne peut pas être antérieure à la date de publication."
            })

        return attrs


class SimilarOpportunitySerializer(serializers.ModelSerializer):
    similarity_score = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Opportunite
        fields = ["id", "titre", "similarity_score"]
        read_only_fields = ["id", "titre", "similarity_score"]

    def get_similarity_score(self, obj):
        score = getattr(obj, "similarity_score", None)
        if score is None:
            return None
        try:
            return round(float(score), 4)
        except (TypeError, ValueError):
            return None
