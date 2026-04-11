import hashlib
import hmac

from django.conf import settings
from rest_framework.throttling import AnonRateThrottle, SimpleRateThrottle


class OTPRequestThrottle(AnonRateThrottle):
    """
    Per-IP throttle on /auth/passwordless/request/.
    Prevents email bombing and request flooding.
    Rate configured via settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['otp_request'].
    """
    scope = 'otp_request'


class OTPVerifyThrottle(AnonRateThrottle):
    """
    Per-IP throttle on /auth/passwordless/verify/.
    Secondary layer against distributed brute-force across multiple
    challenges once the per-challenge attempt cap (5) is exhausted.
    Rate configured via settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['otp_verify'].
    """
    scope = 'otp_verify'


class OTPVerifyEmailThrottle(SimpleRateThrottle):
    """
    Per-email throttle on /auth/passwordless/verify/.
    Enforces a hard ceiling on verification attempts for a given
    address regardless of the originating IP — neutralising
    distributed attacks that rotate source IPs.
    Rate configured via settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['otp_verify_email'].

    The cache key is an HMAC-SHA256 digest of the email address so that
    plaintext emails are never written to the cache backend.
    """
    scope = 'otp_verify_email'

    def get_cache_key(self, request, view):
        email = request.data.get('email', '').lower().strip()
        if not email or '@' not in email:
            # No email in payload — fall through to IP throttle only.
            return None
        email_digest = hmac.new(
            settings.SECRET_KEY.encode(),
            email.encode(),
            hashlib.sha256,
        ).hexdigest()
        return self.cache_format % {'scope': self.scope, 'ident': email_digest}


class GoogleAuthThrottle(AnonRateThrottle):
    """
    Per-IP throttle on /auth/google/.
    Limits abuse against public Google token verification endpoint.
    """

    scope = 'google_auth'
