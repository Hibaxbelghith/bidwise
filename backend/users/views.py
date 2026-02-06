from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from .models import Utilisateur, Profil
from .serializers import (
    UtilisateurSerializer,
    ProfilUpdateSerializer,
    UtilisateurRegisterSerializer,
    CustomTokenObtainPairSerializer,
    PasswordResetSerializer,
    PasswordResetConfirmSerializer
)
from .permissions import IsAdmin


class UtilisateurViewSet(viewsets.ModelViewSet):
    queryset = Utilisateur.objects.all()
    serializer_class = UtilisateurSerializer
    permission_classes = [IsAdmin]


class CustomTokenObtainPairView(TokenObtainPairView):
    """Vue personnalisée pour accepter email ou username au login (champ 'username')."""
    serializer_class = CustomTokenObtainPairSerializer


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """
    Endpoint d'inscription (POST /api/auth/register/)
    Crée un nouvel utilisateur (CANDIDAT ou ORGANISATION) et son profil automatiquement.
    Envoie un email de bienvenue après l'inscription.
    """
    serializer = UtilisateurRegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        
        # Envoyer un email de bienvenue
        groupe = user.groups.first().name if user.groups.exists() else "utilisateur"
        sujet = "Bienvenue sur BidWise"
        message = f"""Bonjour {user.first_name} {user.last_name},

Bienvenue sur BidWise ! Votre compte {groupe} a été créé avec succès.

Email: {user.email}
Vous pouvez maintenant vous connecter et explorer notre plateforme.

À bientôt !
L'équipe BidWise"""
        
        try:
            send_mail(
                sujet,
                message,
                settings.DEFAULT_FROM_EMAIL or 'noreply@bidwise.com',
                [user.email],
                fail_silently=False,
            )
        except Exception as e:
            # Log l'erreur mais n'empêche pas l'inscription
            print(f"Erreur lors de l'envoi de l'email: {e}")
        
        return Response(
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "message": "Inscription réussie ! Vous pouvez maintenant vous connecter."
            },
            status=status.HTTP_201_CREATED
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def profile_detail(request):
    """
    GET : récupérer son profil
    PUT : modifier son profil
    """
    try:
        profil = request.user.profil
    except Profil.DoesNotExist:
        return Response(
            {"error": "Profil non trouvé"},
            status=status.HTTP_404_NOT_FOUND
        )

    if request.method == 'GET':
        serializer = ProfilUpdateSerializer(profil)
        return Response(serializer.data)

    elif request.method == 'PUT':
        serializer = ProfilUpdateSerializer(profil, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def password_reset(request):
    """
    Endpoint de réinitialisation de mot de passe (POST /api/auth/password-reset/)
    Envoie un email avec un lien de confirmation à l'adresse fournie.
    """
    serializer = PasswordResetSerializer(data=request.data)
    if serializer.is_valid():
        email = serializer.validated_data['email']
        user = Utilisateur.objects.get(email=email)
        
        # Générer un token sécurisé
        token_generator = PasswordResetTokenGenerator()
        token = token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        
        # Construire le lien de réinitialisation
        reset_url = f"http://localhost:3000/password-reset-confirm/?uid={uid}&token={token}"
        
        # Envoyer l'email
        sujet = "Réinitialisation de votre mot de passe BidWise"
        message = f"""Bonjour {user.first_name} {user.last_name},

Vous avez demandé une réinitialisation de votre mot de passe BidWise.

Cliquez sur le lien ci-dessous pour réinitialiser votre mot de passe :
{reset_url}

Ce lien expire dans 24 heures.

Si vous n'avez pas demandé cette réinitialisation, ignorez cet email.

L'équipe BidWise"""
        
        try:
            send_mail(
                sujet,
                message,
                settings.DEFAULT_FROM_EMAIL or 'noreply@bidwise.com',
                [email],
                fail_silently=False,
            )
            return Response(
                {"message": "Un email de réinitialisation a été envoyé à votre adresse."},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            print(f"Erreur lors de l'envoi de l'email: {e}")
            return Response(
                {"error": "Erreur lors de l'envoi de l'email."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def password_reset_confirm(request):
    """
    Endpoint de confirmation de réinitialisation (POST /api/auth/password-reset-confirm/)
    Valide le token et change le mot de passe.
    """
    serializer = PasswordResetConfirmSerializer(data=request.data)
    if serializer.is_valid():
        uid_encoded = serializer.validated_data['uid']
        token = serializer.validated_data['token']
        new_password = serializer.validated_data['new_password']
        
        try:
            # Décoder l'UID depuis base64
            uid = force_str(urlsafe_base64_decode(uid_encoded))
            
            # Récupérer l'utilisateur par UID
            user = Utilisateur.objects.get(pk=uid)
            
            # Valider le token
            token_generator = PasswordResetTokenGenerator()
            if not token_generator.check_token(user, token):
                return Response(
                    {"error": "Token invalide ou expiré."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Changer le mot de passe
            user.set_password(new_password)
            user.save()
            
            return Response(
                {"message": "Votre mot de passe a été réinitialisé avec succès. Vous pouvez maintenant vous connecter."},
                status=status.HTTP_200_OK
            )
        
        except (ValueError, TypeError):
            return Response(
                {"error": "UID invalide."},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Utilisateur.DoesNotExist:
            return Response(
                {"error": "Utilisateur non trouvé."},
                status=status.HTTP_404_NOT_FOUND
            )
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)