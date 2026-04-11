"""
Google OAuth2 id_token authentication endpoint.

Verifies a Google-issued id_token, auto-creates the user if needed,
and returns the same JWT response shape as the OTP verify endpoint:
    { access, refresh, is_new_user }

No Google tokens are ever stored.
"""

from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.conf import settings

from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests

from .models import Utilisateur, LoginEvent
from .throttles import GoogleAuthThrottle

# ── Generic error — intentionally vague to prevent information leakage ──
_INVALID_TOKEN_ERROR = "Invalid Google token."


class GoogleAuthSerializer(serializers.Serializer):
    """Validates the incoming request body for Google authentication."""
    id_token = serializers.CharField(required=True, trim_whitespace=True)


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([GoogleAuthThrottle])
def google_authenticate(request):
    """
    POST /api/auth/google/
    Body: { "id_token": "<Google id_token>" }

    1. Validate input via serializer.
    2. Verify id_token against Google public keys.
    3. Double-check audience matches our GOOGLE_CLIENT_ID.
    4. Ensure email_verified is True.
    5. Lookup or auto-create user (set_unusable_password).
    6. Issue JWT via RefreshToken.for_user.
    7. Return { access, refresh, is_new_user }.
    """
    # ── Guard: server must be configured ─────────────────
    client_id = getattr(settings, 'GOOGLE_CLIENT_ID', '')
    if not client_id:
        return Response(
            {"error": "Google authentication is not configured."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # ── Input validation ─────────────────────────────────
    serializer = GoogleAuthSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    token = serializer.validated_data['id_token']

    # ── Token verification ───────────────────────────────
    try:
        idinfo = google_id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            client_id,
        )
    except ValueError:
        return Response(
            {"error": _INVALID_TOKEN_ERROR},
            status=status.HTTP_400_BAD_REQUEST,
        )
    except Exception:
        # Network errors, malformed JWTs, key-fetch failures, etc.
        return Response(
            {"error": _INVALID_TOKEN_ERROR},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # ── Audience double-check (defense in depth) ─────────
    if idinfo.get('aud') != client_id:
        return Response(
            {"error": _INVALID_TOKEN_ERROR},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # ── Email verification ───────────────────────────────
    if not idinfo.get('email_verified', False):
        return Response(
            {"error": _INVALID_TOKEN_ERROR},
            status=status.HTTP_400_BAD_REQUEST,
        )

    email = idinfo['email'].lower()

    # ── Resolve or auto-create user ──────────────────────
    is_new_user = False
    try:
        user = Utilisateur.objects.get(email=email)
    except Utilisateur.DoesNotExist:
        user = Utilisateur(username=email, email=email)
        user.set_unusable_password()
        user.save()
        is_new_user = True

    if not user.is_active:
        return Response(
            {"error": _INVALID_TOKEN_ERROR},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Record login event and detect suspicious activity
    LoginEvent.record(user, request)

    # ── Issue JWT (same mechanism as OTP verify) ─────────
    refresh = RefreshToken.for_user(user)

    return Response(
        {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "is_new_user": is_new_user,
        },
        status=status.HTTP_200_OK,
    )

