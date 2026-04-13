import logging

from django.conf import settings
from django.core.mail import send_mail

from .emails import otp_email_html, otp_email_plaintext


logger = logging.getLogger(__name__)

CLIENT_TYPE_WEB = "web"
CLIENT_TYPE_MOBILE = "mobile"
SUPPORTED_CLIENT_TYPES = {CLIENT_TYPE_WEB, CLIENT_TYPE_MOBILE}

OTP_SENT_MSG = "Un code de connexion a ete envoye a votre adresse email."
OTP_SIMULATED_MOBILE_MSG = "OTP simulated for mobile"


def normalize_client_type(raw_value):
    value = str(raw_value or "").strip().lower()
    if value in SUPPORTED_CLIENT_TYPES:
        return value
    return CLIENT_TYPE_WEB


def resolve_client_type(request, body_client_type=None):
    header_value = request.META.get("HTTP_X_CLIENT_TYPE")
    normalized_header = normalize_client_type(header_value)
    if header_value:
        return normalized_header
    return normalize_client_type(body_client_type)


def otp_response_message(client_type):
    if normalize_client_type(client_type) == CLIENT_TYPE_MOBILE:
        return OTP_SIMULATED_MOBILE_MSG
    return OTP_SENT_MSG


def deliver_otp(email, otp_code, expiry_minutes, client_type):
    normalized_client_type = normalize_client_type(client_type)

    if normalized_client_type == CLIENT_TYPE_MOBILE:
        if settings.DEBUG:
            # In dev/mobile simulation, expose OTP in console logs for testing.
            logger.warning(
                "OTP simulated (mobile) [dev] email=%s otp=%s expires_in_minutes=%s",
                email,
                otp_code,
                expiry_minutes,
            )
        else:
            logger.info(
                "OTP simulated (mobile) email=%s expires_in_minutes=%s",
                email,
                expiry_minutes,
            )
        return

    subject = "Your BidWise login code"
    plaintext = otp_email_plaintext(otp_code, expiry_minutes)
    html = otp_email_html(otp_code, expiry_minutes)

    send_mail(
        subject=subject,
        message=plaintext,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,
        html_message=html,
    )

    logger.info(
        "OTP sent via email email=%s backend=%s",
        email,
        getattr(settings, "EMAIL_BACKEND", "unknown"),
    )
