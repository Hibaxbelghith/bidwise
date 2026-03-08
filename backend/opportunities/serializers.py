from rest_framework import serializers
from .models import Opportunite
from .models import SourceOpportunite


class SourceOpportuniteSerializer(serializers.ModelSerializer):
    class Meta:
        model = SourceOpportunite
        fields = ['id', 'nom', 'url', 'type_source']


class OpportuniteSerializer(serializers.ModelSerializer):
    source = SourceOpportuniteSerializer(read_only=True)
    source_id = serializers.PrimaryKeyRelatedField(
        queryset=SourceOpportunite.objects.all(), source='source', write_only=True
    )

    class Meta:
        model = Opportunite
        fields = '__all__'

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
