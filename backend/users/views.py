import logging

from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, authentication_classes, parser_classes, permission_classes, throttle_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
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


def _request_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


PROFILE_SUGGESTION_LIST_FIELDS = {
    "competences",
    "domaines_interet",
    "target_roles",
    "preferred_locations",
    "employment_types",
    "work_mode_preferences",
}
PROFILE_SUGGESTION_SCALAR_FIELDS = {
    "niveau_experience",
    "annees_experience",
}
PROFILE_SUGGESTION_ALLOWED_FIELDS = PROFILE_SUGGESTION_LIST_FIELDS | PROFILE_SUGGESTION_SCALAR_FIELDS


def _clean_suggestion_list(value):
    if isinstance(value, str):
        raw_items = [value]
    elif isinstance(value, (list, tuple, set)):
        raw_items = value
    else:
        raw_items = []
    output = []
    seen = set()
    for item in raw_items:
        text = " ".join(str(item or "").strip().split())
        key = text.casefold()
        if not text or key in seen:
            continue
        seen.add(key)
        output.append(text)
    return output


def _merge_unique_profile_values(current, suggested):
    output = []
    seen = set()
    for item in [*_clean_suggestion_list(current), *_clean_suggestion_list(suggested)]:
        key = item.casefold()
        if key in seen:
            continue
        seen.add(key)
        output.append(item)
    return output


def _selected_resume_suggestions_payload(profile, suggestions, selected):
    if not isinstance(suggestions, dict):
        suggestions = {}
    if not isinstance(selected, dict):
        selected = {}

    payload = {}
    for field in PROFILE_SUGGESTION_LIST_FIELDS:
        selected_values = selected.get(field)
        if selected_values is True:
            selected_values = suggestions.get(field, [])
        if field == "employment_types":
            expanded_values = []
            for value in _clean_suggestion_list(selected_values):
                expanded_values.extend(part.strip() for part in value.replace("|", "/").split("/"))
            selected_values = expanded_values
        values = _clean_suggestion_list(selected_values)
        if values:
            payload[field] = _merge_unique_profile_values(getattr(profile, field, []), values)

    for field in PROFILE_SUGGESTION_SCALAR_FIELDS:
        if field not in selected:
            continue
        value = selected.get(field)
        if value is True:
            value = suggestions.get(field)
        if value not in (None, ""):
            payload[field] = value
    return payload


@api_view(['GET', 'POST', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated, IsSuspensionNotBlocked])
@parser_classes([MultiPartParser, FormParser, JSONParser])
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
        resume_id = request.query_params.get("resume_id") or request.data.get("resume_id")
        if resume_id:
            resume = ProfileResume.objects.filter(profile=profil, pk=resume_id).first()
            if not resume:
                return Response({"detail": "Resume not found."}, status=status.HTTP_404_NOT_FOUND)
            was_active = resume.is_active
            if was_active:
                resume.is_active = False
                resume.save(update_fields=["is_active"])
                transaction.on_commit(
                    lambda profile_id=profil.pk: enqueue_profile_embedding_refresh(profile_id)
                )
            else:
                resume.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        if active_resume:
            active_resume.is_active = False
            active_resume.save(update_fields=["is_active"])
            transaction.on_commit(
                lambda profile_id=profil.pk: enqueue_profile_embedding_refresh(profile_id)
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    if request.method == 'PATCH':
        resume_id = request.data.get("resume_id")
        if not resume_id:
            return Response({"resume_id": ["This field is required."]}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            resume = (
                ProfileResume.objects
                .select_for_update()
                .filter(profile=profil, pk=resume_id)
                .first()
            )
            if not resume:
                return Response({"detail": "Resume not found."}, status=status.HTTP_404_NOT_FOUND)
            ProfileResume.objects.filter(profile=profil, is_active=True).exclude(pk=resume.pk).update(is_active=False)
            if not resume.is_active:
                resume.is_active = True
                resume.save(update_fields=["is_active"])
            transaction.on_commit(
                lambda profile_id=profil.pk: enqueue_profile_embedding_refresh(profile_id)
            )

        output = ProfileResumeSerializer(resume, context={"request": request})
        return Response({"resume": output.data}, status=status.HTTP_200_OK)

    serializer = ProfileResumeSerializer(
        data=request.data,
        context={
            "request": request,
            "profile": profil,
            "activate_resume": _request_bool(request.data.get("activate"), default=True),
        },
    )
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        if serializer.context["activate_resume"]:
            ProfileResume.objects.filter(profile=profil, is_active=True).update(is_active=False)
        resume = serializer.save()
        transaction.on_commit(
            lambda resume_id=resume.pk: enqueue_profile_resume_parse(resume_id)
        )

    output = ProfileResumeSerializer(resume, context={"request": request})
    return Response({"resume": output.data}, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsSuspensionNotBlocked])
@parser_classes([JSONParser])
def apply_resume_profile_suggestions(request):
    try:
        profil = request.user.profil
    except Profil.DoesNotExist:
        return Response(
            {"error": "Profil non trouvÃƒÂ©"},
            status=status.HTTP_404_NOT_FOUND,
        )

    resume_id = request.data.get("resume_id")
    selected = request.data.get("selected") or {}
    if not resume_id:
        return Response({"resume_id": ["This field is required."]}, status=status.HTTP_400_BAD_REQUEST)
    if not isinstance(selected, dict):
        return Response({"selected": ["Expected an object of selected suggestions."]}, status=status.HTTP_400_BAD_REQUEST)

    unknown_fields = sorted(set(selected) - PROFILE_SUGGESTION_ALLOWED_FIELDS)
    if unknown_fields:
        return Response(
            {"selected": [f"Unsupported suggestion fields: {', '.join(unknown_fields)}."]},
            status=status.HTTP_400_BAD_REQUEST,
        )

    with transaction.atomic():
        resume = (
            ProfileResume.objects
            .select_for_update()
            .filter(profile=profil, pk=resume_id, is_active=True)
            .first()
        )
        if not resume:
            return Response({"detail": "Active resume not found."}, status=status.HTTP_404_NOT_FOUND)

        if str(resume.semantic_resume_status or "").upper() != "SUCCEEDED":
            return Response(
                {"detail": "Resume analysis is not completed yet."},
                status=status.HTTP_409_CONFLICT,
            )

        metadata = resume.semantic_resume_metadata if isinstance(resume.semantic_resume_metadata, dict) else {}
        enrichment = metadata.get("llm_enrichment") if isinstance(metadata, dict) else {}
        suggestions = enrichment.get("profile_suggestions") if isinstance(enrichment, dict) else {}
        payload = _selected_resume_suggestions_payload(profil, suggestions, selected)
        if not payload:
            return Response(
                {"selected": ["Select at least one resume suggestion to apply."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ProfilUpdateSerializer(profil, data=payload, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        saved_profile = serializer.save()
        metadata = dict(metadata)
        metadata["profile_suggestions_applied_at"] = timezone.now().isoformat()
        metadata["profile_suggestions_applied_fields"] = sorted(payload)
        resume.semantic_resume_metadata = metadata
        resume.save(update_fields=["semantic_resume_metadata"])
        transaction.on_commit(
            lambda profile_id=saved_profile.pk: enqueue_profile_embedding_refresh(profile_id)
        )

    request.user.profil = saved_profile
    user_serializer = UtilisateurSerializer(request.user)
    output_resume = ProfileResumeSerializer(resume, context={"request": request})
    return Response(
        {
            "user": user_serializer.data,
            "profile": user_serializer.data.get("profil"),
            "resume": output_resume.data,
            "applied_fields": sorted(payload),
        },
        status=status.HTTP_200_OK,
    )


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
