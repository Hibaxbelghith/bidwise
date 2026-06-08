from rest_framework import serializers
from opportunities.models import StatutOpportunite
from .models import Candidature, Document


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = [
            "id",
            "type_document",
            "fichier",
            "date_upload",
        ]


class CandidatureSerializer(serializers.ModelSerializer):
    documents = DocumentSerializer(many=True, read_only=True)

    class Meta:
        model = Candidature
        fields = [
            "id",
            "candidat",
            "opportunite",
            "statut",
            "url_source",
            "date_creation",
            "derniere_mise_a_jour",
            "documents",
        ]
        read_only_fields = [
            "date_creation",
            "derniere_mise_a_jour",
        ]

    def validate_opportunite(self, value):
        if value.statut != StatutOpportunite.ACTIVE:
            raise serializers.ValidationError(
                "Applications are closed for this opportunity."
            )
        return value
