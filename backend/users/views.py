import logging

from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import IsAdminUser, IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from .models import Utilisateur, Profil, OTPChallenge, LoginEvent
from .otp_service import deliver_otp, otp_response_message, resolve_client_type
from .serializers import (
    UtilisateurSerializer,
    ProfilUpdateSerializer,
    OTPRequestSerializer,
    OTPVerifySerializer,
)
from .throttles import OTPRequestThrottle, OTPVerifyThrottle, OTPVerifyEmailThrottle

logger = logging.getLogger(__name__)


class UtilisateurViewSet(viewsets.ModelViewSet):
    """Admin-only user list. Restricted to Django staff users."""
    queryset = Utilisateur.objects.all()
    serializer_class = UtilisateurSerializer
    permission_classes = [IsAdminUser]


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
        serializer = UtilisateurSerializer(request.user)
        return Response(serializer.data)

    elif request.method == 'PUT':
        serializer = ProfilUpdateSerializer(profil, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            user_serializer = UtilisateurSerializer(request.user)
            return Response(user_serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ══════════════════════════════════════════════════════════
# Passwordless OTP endpoints
# ══════════════════════════════════════════════════════════

@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([OTPRequestThrottle])
def request_otp(request):
    """
    POST /api/auth/passwordless/request/
    Send a 6-digit OTP to any valid email address.

    - New emails will have their account auto-created at verification time.
    - No user or role check at this stage.

    Security:
    - 60-second per-email cooldown.
    - 10 requests/hour per IP (DRF throttle).
    - Purges expired OTPs on every call.
    """
    serializer = OTPRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    email = serializer.validated_data['email'].lower()
    client_type = resolve_client_type(
        request,
        serializer.validated_data.get('client_type'),
    )

    # Housekeeping — delete expired/used rows globally
    OTPChallenge.purge_expired()

    # Ensure verified OTPs for this email are cleared so they
    # never block the cooldown check (e.g. user already logged in
    # on another device and wants a new OTP immediately).
    OTPChallenge.objects.filter(email=email, is_used=True).delete()

    # Per-email cooldown (only if an unused, non-expired OTP exists)
    if OTPChallenge.is_on_cooldown(email):
        return Response(
            {"message": otp_response_message(client_type)},
            status=status.HTTP_200_OK,
        )

    # Invalidate any previous challenges for this email
    OTPChallenge.purge_for_email(email)

    # Create new challenge (hashed)
    _challenge, plaintext_otp = OTPChallenge.create_for_email(email)

    # Send or simulate based on client type.
    try:
        deliver_otp(
            email=email,
            otp_code=plaintext_otp,
            expiry_minutes=OTPChallenge.OTP_EXPIRY_MINUTES,
            client_type=client_type,
        )
    except Exception:
        # Delete the orphaned challenge — user never received the code
        # so it must not remain as a valid (but undeliverable) credential.
        _challenge.delete()
        logger.error("[OTP] Email delivery failed for %s", email, exc_info=True)
        return Response(
            {"error": "Impossible d'envoyer l'email. Veuillez réessayer."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    return Response(
        {"message": otp_response_message(client_type)},
        status=status.HTTP_200_OK,
    )


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([OTPVerifyThrottle, OTPVerifyEmailThrottle])
def verify_otp(request):
    """
    POST /api/auth/passwordless/verify/
    Verify a 6-digit OTP and issue JWT tokens.

    On success: returns {access, refresh} — identical shape to /api/auth/login/.
    On failure: generic error (no distinction between wrong code / expired / unknown).
    """
    serializer = OTPVerifySerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    email = serializer.validated_data['email'].lower()
    otp = serializer.validated_data['otp']

    # Find the latest active challenge for this email
    challenge = (
        OTPChallenge.objects
        .filter(email=email, is_used=False)
        .order_by('-created_at')
        .first()
    )

    if not challenge:
        return Response(
            {"error": "Code invalide ou expiré."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Too many wrong attempts on this challenge
    if challenge.is_locked:
        return Response(
            {"error": "Trop de tentatives. Veuillez demander un nouveau code."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Verify OTP (increments attempts on failure, marks used on success)
    if not challenge.verify(otp):
        return Response(
            {"error": "Code invalide ou expiré."},
            status=status.HTTP_400_BAD_REQUEST,
        )

        # OTP valid — resolve or auto-create user.
    # get_or_create is atomic and prevents a duplicate-user race condition
    # when two verify requests for a brand-new email arrive simultaneously.
    user, is_new_user = Utilisateur.objects.get_or_create(
        email=email,
        defaults={'username': email},
    )
    if is_new_user:
        user.set_unusable_password()
        user.save(update_fields=['password'])

    if not user.is_active:
        return Response(
            {"error": "Code invalide ou expiré."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Record login event and detect suspicious activity
    LoginEvent.record(user, request)

    refresh = RefreshToken.for_user(user)

    return Response(
        {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "is_new_user": is_new_user,
        },
        status=status.HTTP_200_OK,
    )


# ══════════════════════════════════════════════════════════
# Logout (token blacklist)
# ══════════════════════════════════════════════════════════

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """
    POST /api/auth/logout/
    Blacklist the provided refresh token so it can no longer be used.
    """
    refresh_token = request.data.get('refresh')
    if not refresh_token:
        return Response(
            {"error": "Refresh token is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        token = RefreshToken(refresh_token)
        token.blacklist()
    except TokenError:
        return Response(
            {"error": "Token is invalid or already blacklisted."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response({"detail": "Successfully logged out."}, status=status.HTTP_200_OK)
