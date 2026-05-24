import logging

from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, authentication_classes, parser_classes, permission_classes, throttle_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAdminUser, IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from ai.embeddings import enqueue_profile_embedding_refresh
from opportunities.autocomplete.service import coerce_limit, suggest_profile_terms
from opportunities.models import ProfileSuggestionType

from .permissions import IsSuspensionNotBlocked
from .models import (
    Utilisateur,
    Profil,
    ProfileResume,
    OrganizationProfile,
    OTPChallenge,
    LoginEvent,
)
from .otp_service import deliver_otp, otp_response_message, resolve_client_type
from .serializers import (
    UtilisateurSerializer,
    OrganizationProfileSerializer,
    ProfileResumeSerializer,
    ProfilUpdateSerializer,
    OTPRequestSerializer,
    OTPVerifySerializer,
)
from .tasks import enqueue_profile_resume_parse
from .throttles import (
    OTPRequestThrottle,
    OTPVerifyEmailThrottle,
    OTPVerifyThrottle,
    ProfileSuggestionThrottle,
)

logger = logging.getLogger(__name__)


@ensure_csrf_cookie
@api_view(['GET'])
@permission_classes([AllowAny])
def csrf_token(request):
    return Response({"csrfToken": get_token(request)})


class UtilisateurViewSet(viewsets.ModelViewSet):
    """Admin-only user list. Restricted to Django staff users."""
    queryset = (
        Utilisateur.objects
        .select_related("profil", "organization_profile")
        .prefetch_related("profil__resumes")
        .all()
    )
    serializer_class = UtilisateurSerializer
    permission_classes = [IsAdminUser]


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated, IsSuspensionNotBlocked])
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
            saved_profile = serializer.save()
            saved_profile.refresh_from_db()
            request.user.profil = saved_profile
            user_serializer = UtilisateurSerializer(request.user)
            return Response(user_serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated, IsSuspensionNotBlocked])
def organization_profile_detail(request):
    if (
        request.method == 'GET'
        and request.user.account_type != Utilisateur.AccountType.ORGANIZATION
    ):
        return Response(
            {"error": "Organization account required."},
            status=status.HTTP_403_FORBIDDEN,
        )

    try:
        profile = request.user.organization_profile
    except OrganizationProfile.DoesNotExist:
        profile = None

    if request.method == 'GET':
        if profile is None:
            return Response(
                {"error": "Organization profile not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = OrganizationProfileSerializer(profile, context={"request": request})
        return Response(serializer.data)

    if profile is not None and request.user.account_type != Utilisateur.AccountType.ORGANIZATION:
        return Response(
            {"error": "Organization account required."},
            status=status.HTTP_403_FORBIDDEN,
        )

    serializer = OrganizationProfileSerializer(
        profile,
        data=request.data,
        partial=profile is not None,
        context={"request": request, "user": request.user},
    )
    if serializer.is_valid():
        with transaction.atomic():
            if request.user.account_type != Utilisateur.AccountType.ORGANIZATION:
                request.user.account_type = Utilisateur.AccountType.ORGANIZATION
                request.user.save(update_fields=["account_type"])
            saved_profile = serializer.save()
        output = OrganizationProfileSerializer(
            saved_profile,
            context={"request": request},
        )
        return Response(
            output.data,
            status=status.HTTP_200_OK if profile else status.HTTP_201_CREATED,
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


def _profile_suggestion_response(request, term_type):
    query = request.query_params.get('q', '')
    limit = coerce_limit(request.query_params.get('limit'))
    return Response(suggest_profile_terms(term_type, query, limit=limit))


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsSuspensionNotBlocked])
@throttle_classes([ProfileSuggestionThrottle])
def skill_suggestions(request):
    return _profile_suggestion_response(request, ProfileSuggestionType.SKILL)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsSuspensionNotBlocked])
@throttle_classes([ProfileSuggestionThrottle])
def role_suggestions(request):
    return _profile_suggestion_response(request, ProfileSuggestionType.ROLE)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsSuspensionNotBlocked])
@throttle_classes([ProfileSuggestionThrottle])
def interest_suggestions(request):
    return _profile_suggestion_response(request, ProfileSuggestionType.INTEREST)


@api_view(['GET', 'POST', 'DELETE'])
@permission_classes([IsAuthenticated, IsSuspensionNotBlocked])
@parser_classes([MultiPartParser, FormParser])
def profile_resume(request):
    try:
        profil = request.user.profil
    except Profil.DoesNotExist:
        return Response(
            {"error": "Profil non trouvÃ©"},
            status=status.HTTP_404_NOT_FOUND,
        )

    active_resume = (
        ProfileResume.objects
        .filter(profile=profil, is_active=True)
        .order_by("-uploaded_at", "-id")
        .first()
    )

    if request.method == 'GET':
        if not active_resume:
            return Response({"resume": None}, status=status.HTTP_200_OK)
        serializer = ProfileResumeSerializer(active_resume, context={"request": request})
        return Response({"resume": serializer.data}, status=status.HTTP_200_OK)

    if request.method == 'DELETE':
        if active_resume:
            active_resume.is_active = False
            active_resume.save(update_fields=["is_active"])
            transaction.on_commit(
                lambda profile_id=profil.pk: enqueue_profile_embedding_refresh(profile_id)
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = ProfileResumeSerializer(
        data=request.data,
        context={"request": request, "profile": profil},
    )
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        ProfileResume.objects.filter(profile=profil, is_active=True).update(is_active=False)
        resume = serializer.save()
        transaction.on_commit(
            lambda resume_id=resume.pk: enqueue_profile_resume_parse(resume_id)
        )

    output = ProfileResumeSerializer(resume, context={"request": request})
    return Response({"resume": output.data}, status=status.HTTP_201_CREATED)


# ══════════════════════════════════════════════════════════
# Passwordless OTP endpoints
# ══════════════════════════════════════════════════════════

@api_view(['POST'])
@authentication_classes([])
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
@authentication_classes([])
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

    if user.is_suspended:
        return Response(
            {"error": "Votre compte a été suspendu. Veuillez contacter le support pour plus d'informations."},
            status=status.HTTP_403_FORBIDDEN,
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
