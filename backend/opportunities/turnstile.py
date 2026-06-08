from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import requests
from django.conf import settings


logger = logging.getLogger(__name__)

TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


@dataclass(frozen=True)
class TurnstileVerification:
    required: bool
    success: bool
    reason: str = ""


def is_turnstile_required() -> bool:
    return bool(str(getattr(settings, "TURNSTILE_SECRET_KEY", "") or "").strip())


def verify_turnstile_token(token: str | None, *, remote_ip: str | None = None) -> TurnstileVerification:
    secret = str(getattr(settings, "TURNSTILE_SECRET_KEY", "") or "").strip()
    if not secret:
        return TurnstileVerification(required=False, success=True, reason="Turnstile is not configured.")

    clean_token = str(token or "").strip()
    if not clean_token:
        return TurnstileVerification(required=True, success=False, reason="Complete the anti-bot check.")

    payload: dict[str, Any] = {
        "secret": secret,
        "response": clean_token,
    }
    if remote_ip:
        payload["remoteip"] = remote_ip

    try:
        response = requests.post(
            TURNSTILE_VERIFY_URL,
            data=payload,
            timeout=float(getattr(settings, "TURNSTILE_TIMEOUT_SECONDS", 4.0)),
        )
        data = response.json()
    except (requests.RequestException, ValueError) as exc:
        logger.warning("Turnstile verification failed unexpectedly: %s", exc)
        return TurnstileVerification(
            required=True,
            success=False,
            reason="Anti-bot verification is temporarily unavailable. Please try again.",
        )

    if data.get("success") is True:
        return TurnstileVerification(required=True, success=True, reason="Turnstile verified.")

    error_codes = data.get("error-codes") or []
    response_status = int(getattr(response, "status_code", 200) or 200)
    if response_status >= 400:
        logger.error(
            "Turnstile verification request rejected status=%s errors=%s",
            response_status,
            error_codes,
        )
    else:
        logger.info("Turnstile verification rejected token errors=%s", error_codes)

    if "invalid-input-secret" in error_codes or "missing-input-secret" in error_codes:
        return TurnstileVerification(
            required=True,
            success=False,
            reason="Anti-bot verification is temporarily unavailable. Please try again later.",
        )

    return TurnstileVerification(
        required=True,
        success=False,
        reason="The security check expired or was rejected. Please complete it again.",
    )
