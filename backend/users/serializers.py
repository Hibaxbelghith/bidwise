from rest_framework import serializers
from .models import Utilisateur, Profil


class ProfilSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profil
        fields = [
            'id', 'nom', 'prenom', 'competences', 'domaines_interet',
            'niveau_experience', 'annees_experience',
            'opportunity_types', 'preferred_location', 'remote_preference',
            'compensation_expectation', 'compensation_period',
            'employment_types', 'target_roles', 'profile_visibility',
            'onboarding_completed', 'last_onboarding_step',
        ]
        read_only_fields = ['id']


class UtilisateurSerializer(serializers.ModelSerializer):
    profil = ProfilSerializer(read_only=True)

    class Meta:
        model = Utilisateur
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'is_active', 'date_joined', 'profil']
        read_only_fields = ['id', 'date_joined']


class ProfilUpdateSerializer(serializers.ModelSerializer):
    """Serializer pour permettre à l'utilisateur de modifier son profil."""
    class Meta:
        model = Profil
        fields = [
            'nom', 'prenom', 'competences', 'domaines_interet',
            'niveau_experience', 'annees_experience',
            'opportunity_types', 'preferred_location', 'remote_preference',
            'compensation_expectation', 'compensation_period',
            'employment_types', 'target_roles', 'profile_visibility',
            'onboarding_completed', 'last_onboarding_step',
        ]


# ── Passwordless OTP serializers ───────────────────────────

class OTPRequestSerializer(serializers.Serializer):
    """Validates the email submitted when requesting an OTP."""
    email = serializers.EmailField(required=True)


class OTPVerifySerializer(serializers.Serializer):
    """Validates email + 6-digit OTP code for passwordless login."""
    email = serializers.EmailField(required=True)
    otp = serializers.CharField(required=True, min_length=6, max_length=6)
