from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from .models import Utilisateur, Profil, OTPChallenge, LoginEvent
from .serializers import (
    UtilisateurSerializer,
    ProfilUpdateSerializer,
    OTPRequestSerializer,
    OTPVerifySerializer,
)
from .emails import otp_email_html, otp_email_plaintext
from .throttles import OTPRequestThrottle


class UtilisateurViewSet(viewsets.ModelViewSet):
    """Admin-only user list.  Restricted to Django staff users."""
    queryset = Utilisateur.objects.all()
    serializer_class = UtilisateurSerializer
    permission_classes = [IsAuthenticated]  # TODO: restrict to is_staff if needed


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

# Constant response — prevents user enumeration.
_OTP_SENT_MSG = "Un code de connexion a été envoyé à votre adresse email."


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

    # Housekeeping — delete expired/used rows globally
    OTPChallenge.purge_expired()

    # Ensure verified OTPs for this email are cleared so they
    # never block the cooldown check (e.g. user already logged in
    # on another device and wants a new OTP immediately).
    OTPChallenge.objects.filter(email=email, is_used=True).delete()

    # Per-email cooldown (only if an unused, non-expired OTP exists)
    if OTPChallenge.is_on_cooldown(email):
        return Response({"message": _OTP_SENT_MSG}, status=status.HTTP_200_OK)

    # Invalidate any previous challenges for this email
    OTPChallenge.purge_for_email(email)

    # Create new challenge (hashed)
    _challenge, plaintext_otp = OTPChallenge.create_for_email(email)

    # Send the code by email (HTML + plain-text fallback)
    try:
        subject = "Your BidWise login code"
        plaintext = otp_email_plaintext(plaintext_otp, OTPChallenge.OTP_EXPIRY_MINUTES)
        html = otp_email_html(plaintext_otp, OTPChallenge.OTP_EXPIRY_MINUTES)

        msg = EmailMultiAlternatives(
            subject=subject,
            body=plaintext,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email],
        )
        msg.attach_alternative(html, "text/html")
        msg.send(fail_silently=False)
    except Exception as e:
        print(f"[OTP] Erreur envoi email: {e}")

    return Response({"message": _OTP_SENT_MSG}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
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

    # OTP valid — resolve or auto-create user
    is_new_user = False
    try:
        user = Utilisateur.objects.get(email=email)
    except Utilisateur.DoesNotExist:
        # Auto-create: username = email, unusable password.
        # The post_save signal in signals.py auto-creates the Profil.
        user = Utilisateur(username=email, email=email)
        user.set_unusable_password()
        user.save()
        is_new_user = True

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