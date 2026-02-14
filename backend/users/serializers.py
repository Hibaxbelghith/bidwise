from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.models import Group
from .models import Utilisateur, Profil


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Serializer personnalisé pour accepter email ou username au login."""
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        return token

    def validate(self, attrs):
        """Valide email ou username + password."""
        login = attrs.get('username')  # Récupère le champ 'username' depuis le body
        password = attrs.get('password')

        if not login or not password:
            raise serializers.ValidationError("Email/Username et mot de passe sont obligatoires.")

        # Chercher par email ou username
        try:
            user = Utilisateur.objects.get(email=login)
        except Utilisateur.DoesNotExist:
            try:
                user = Utilisateur.objects.get(username=login)
            except Utilisateur.DoesNotExist:
                raise serializers.ValidationError("Email ou mot de passe invalide.")

        # Vérifier le mot de passe
        if not user.check_password(password):
            raise serializers.ValidationError("Email ou mot de passe invalide.")

        # Si tout est bon, générer les tokens
        token = self.get_token(user)
        attrs['access'] = str(token.access_token)
        attrs['refresh'] = str(token)
        
        return attrs


class UtilisateurRegisterSerializer(serializers.ModelSerializer):
    """Serializer pour l'inscription d'un nouvel utilisateur."""
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    password2 = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    account_type = serializers.ChoiceField(choices=['CANDIDAT', 'ORGANISATION'], write_only=True, required=True)
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)

    class Meta:
        model = Utilisateur
        fields = ['email', 'password', 'password2', 'first_name', 'last_name', 'account_type']

    def validate(self, attrs):
        """Valide que les deux mots de passe correspondent et que l'email n'existe pas."""
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Les mots de passe ne correspondent pas."})
        
        # Vérifier que l'email n'existe pas
        if Utilisateur.objects.filter(email=attrs['email']).exists():
            raise serializers.ValidationError({"email": "Un utilisateur avec cet email existe déjà."})
        
        return attrs

    def create(self, validated_data):
        """Crée l'utilisateur et l'assigne au groupe approprié."""
        account_type = validated_data.pop('account_type')
        validated_data.pop('password2')
        first_name = validated_data.pop('first_name')
        last_name = validated_data.pop('last_name')
        
        # Créer l'utilisateur avec email comme username
        user = Utilisateur.objects.create_user(
            username=validated_data['email'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=first_name,
            last_name=last_name
        )
        
        # Assigner le groupe
        group = Group.objects.get(name=account_type)
        user.groups.add(group)
        
        # Mettre à jour le profil auto-créé
        user.profil.nom = last_name
        user.profil.prenom = first_name
        user.profil.save()
        
        return user


class ProfilSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profil
        fields = ['id', 'nom', 'prenom', 'competences', 'domaines_interet', 'niveau_experience']
        read_only_fields = ['id']


class UtilisateurSerializer(serializers.ModelSerializer):
    profil = ProfilSerializer(read_only=True)
    account_type = serializers.SerializerMethodField()

    class Meta:
        model = Utilisateur
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'is_active', 'date_joined', 'profil', 'account_type']
        read_only_fields = ['id', 'date_joined']

    def get_account_type(self, obj):
        group = obj.groups.first()
        return group.name if group else None


class ProfilUpdateSerializer(serializers.ModelSerializer):
    """Serializer pour permettre à l'utilisateur de modifier son profil."""
    class Meta:
        model = Profil
        fields = ['nom', 'prenom', 'competences', 'domaines_interet', 'niveau_experience', 'annees_experience']


class PasswordResetSerializer(serializers.Serializer):
    """Serializer pour demander une réinitialisation de mot de passe."""
    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        """Vérifie que l'email existe dans la base."""
        try:
            Utilisateur.objects.get(email=value)
        except Utilisateur.DoesNotExist:
            raise serializers.ValidationError("Aucun utilisateur avec cet email.")
        return value


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer pour confirmer la réinitialisation de mot de passe."""
    uid = serializers.CharField(required=True, max_length=100)  # Base64 encoded
    token = serializers.CharField(required=True, max_length=200)
    new_password = serializers.CharField(write_only=True, required=True, min_length=8)
    new_password2 = serializers.CharField(write_only=True, required=True, min_length=8)

    def validate(self, attrs):
        """Valide que les deux mots de passe correspondent."""
        if attrs['new_password'] != attrs['new_password2']:
            raise serializers.ValidationError({"new_password": "Les mots de passe ne correspondent pas."})
        return attrs
