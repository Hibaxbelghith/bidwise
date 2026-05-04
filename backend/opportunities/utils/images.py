import ipaddress
import unicodedata
from urllib.parse import urlparse

from django.conf import settings


DEFAULT_COMPANY_LOGO_URL = getattr(
    settings,
    "BIDWISE_DEFAULT_COMPANY_LOGO_URL",
    "https://placehold.co/160x160.png?text=BidWise",
)


REJECTED_IMAGE_URL_TOKENS = (
    "keejob.com/static",
    "logo_keejob",
    "placeholder",
    "placehold.co",
    "placehold.it",
)

ANONYMOUS_ORGANIZATION_TOKENS = {
    "entreprise anonyme",
    "anonymous company",
    "anonymous",
}


def _normalized_text(value) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").strip().lower())
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def is_anonymous_organization(value) -> bool:
    token = " ".join(_normalized_text(value).split())
    return token in ANONYMOUS_ORGANIZATION_TOKENS


def is_valid_image_url(value) -> bool:
    text = str(value or "").strip()
    if not text or any(char.isspace() for char in text):
        return False

    lowered = text.lower()
    if any(token in lowered for token in REJECTED_IMAGE_URL_TOKENS):
        return False

    try:
        parsed = urlparse(text)
    except Exception:
        return False

    if parsed.scheme not in {"http", "https"}:
        return False

    host = (parsed.hostname or "").strip().lower()
    if not host:
        return False

    if host == "localhost" or host.endswith(".local") or host.endswith(".localdomain"):
        return False

    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return True

    return ip.is_global


def normalize_company_logo_url(value, *, organization_name=None) -> str:
    if organization_name is not None and is_anonymous_organization(organization_name):
        return DEFAULT_COMPANY_LOGO_URL

    text = str(value or "").strip()
    if is_valid_image_url(text):
        return text
    return DEFAULT_COMPANY_LOGO_URL
