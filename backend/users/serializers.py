import re
import unicodedata
from pathlib import Path
from urllib.parse import urlparse
from .models import AuditLog, Utilisateur

from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers
from ai.business_families import CONTROLLED_FAMILIES, normalize_family
from ai.embeddings import enqueue_profile_embedding_refresh
from .models import Utilisateur, Profil, ProfileResume, OrganizationProfile
from opportunities.autocomplete.service import normalize_profile_terms
from opportunities.utils.images import is_valid_image_url
from opportunities.normalization.employment import (
    CANONICAL_CONTRACT_TYPES,
    WORK_MODE_UNSPECIFIED,
    normalize_contract_types,
    normalize_work_mode,
)
from opportunities.models import ProfileSuggestionType
from .profile_completion import calculate_profile_completion


PROFILE_LIST_ITEM_MAX_LENGTH = 100
MAX_PROFILE_LIST_ITEMS = 30
MAX_PROFILE_TARGET_ROLES = 10
MAX_PROFILE_BUSINESS_FAMILIES = 5
LOCATION_ITEM_MAX_LENGTH = 100
MAX_PREFERRED_LOCATIONS = 10
CANONICAL_PROFILE_WORK_MODES = ("REMOTE", "HYBRID", "ON_SITE")
DEFAULT_COMPENSATION_CURRENCY = "TND"
CANONICAL_COMPENSATION_PERIODS = ("MONTHLY",)
CANONICAL_OPPORTUNITY_TYPES = ("JOB", "INTERNSHIP", "CALLS_FOR_TENDER")
PROFILE_NAME_LENGTH_ERROR = "Input must contain between 2 and 100 characters."
MIN_MONTHLY_SALARY_TND_ERROR = (
    "The minimum desired salary is too low for the selected currency and pay period."
)
SALARY_LIMITS_BY_PERIOD = {
    "MONTHLY": (500, 30000),
}
MAX_RESUME_FILE_SIZE_BYTES = 5 * 1024 * 1024
ALLOWED_RESUME_EXTENSIONS = {".pdf", ".docx", ".doc", ".rtf", ".txt"}
ALLOWED_RESUME_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "application/rtf",
    "text/rtf",
    "text/plain",
}
MAX_ORGANIZATION_LOGO_SIZE_BYTES = 2 * 1024 * 1024
ALLOWED_ORGANIZATION_LOGO_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
ALLOWED_ORGANIZATION_LOGO_CONTENT_TYPES = {
    "image/png",
    "image/jpeg",
    "image/webp",
}
TUNISIA_PHONE_PATTERN = re.compile(r"^\+216\d{8}$")
UNSAFE_PROFILE_TEXT_PATTERN = re.compile(
    r"(<[^>]*>)|[<>]|(?:javascript\s*:)|(?:data\s*:)",
    flags=re.IGNORECASE,
)

PROFILE_BUSINESS_FAMILY_ALIASES = {
    "it_support_network": "it_network_support",
    "devops": "devops_cloud_infrastructure",
    "dev_ops": "devops_cloud_infrastructure",
    "cloud": "devops_cloud_infrastructure",
    "cloud_infrastructure": "devops_cloud_infrastructure",
    "infrastructure_cloud": "devops_cloud_infrastructure",
    "accounting_finance": "accounting_finance_audit",
    "sales": "sales_business",
    "marketing": "marketing_communication",
    "hr": "hr_administration",
    "administration": "hr_administration",
    "quality_industry": "quality_industry_methods",
    "design": "design_creative",
    "legal": "legal_regulatory",
    "ai": "data_ai",
    "ia": "data_ai",
    "bi": "data_ai",
    "fintech": "accounting_finance_audit",
    "finance": "accounting_finance_audit",
    "banque": "accounting_finance_audit",
    "banking": "accounting_finance_audit",
    "assurance": "accounting_finance_audit",
    "insurance": "accounting_finance_audit",
    "marketing_digital": "marketing_communication",
    "communication": "marketing_communication",
    "rh": "hr_administration",
    "recruitment": "hr_administration",
    "recrutement": "hr_administration",
    "support_it": "it_network_support",
    "it_support": "it_network_support",
    "network": "it_network_support",
    "networks": "it_network_support",
    "cybersecurity": "security_safety",
    "cybersecurite": "security_safety",
    "cybersécurité": "security_safety",
    "logistics": "logistics_supply_chain",
    "logistique": "logistics_supply_chain",
    "industry": "quality_industry_methods",
    "industrie": "quality_industry_methods",
    "education": "education_training",
    "enseignement": "education_training",
    "training": "education_training",
    "formation": "education_training",
    "sante": "healthcare",
    "santé": "healthcare",
    "health": "healthcare",
    "medical": "healthcare",
    "ecommerce": "sales_business",
    "e_commerce": "sales_business",
    "commerce_en_ligne": "sales_business",
}

TUNISIAN_LOCATIONS = (
    "Tunis",
    "Sidi Bouzid",
    "Sfax",
    "Sousse",
    "Kairouan",
    "Métouia",
    "Kebili",
    "Sukrah",
    "Gabès",
    "Ariana",
    "Sakiet ed Daier",
    "Gafsa",
    "Msaken",
    "Medenine",
    "Béja",
    "Kasserine",
    "Radès",
    "Hammamet",
    "Tataouine",
    "Monastir",
    "La Marsa",
    "Ben Arous",
    "Sakiet ez Zit",
    "Zarzis",
    "Ben Gardane",
    "Mahdia",
    "Houmt Souk",
    "Fouchana",
    "Le Kram",
    "El Kef",
    "El Hamma",
    "Nabeul",
    "Le Bardo",
    "Djemmal",
    "Korba",
    "Menzel Temime",
    "Ghardimaou",
    "Midoun",
    "Menzel Bourguiba",
    "Manouba",
    "Kélibia",
    "Rass el Djebel",
    "Oued Lill",
    "Moknine",
    "Bir Ali Ben Khalifa",
    "Kelaa Kebira",
    "El Jem",
    "Tebourba",
    "Ksar Hellal",
    "Douz",
    "Bizerte",
    "Jendouba",
    "La Goulette",
    "Jedeïda",
    "Soliman",
    "Hammam Sousse",
    "Sbiba",
    "Tabarka",
    "Sejenane",
    "Metlaoui",
    "Hammam-Lif",
    "Teboulba",
    "Tozeur",
    "Beni Khiar",
    "Dar Chabanne",
    "Aïne Draham",
    "Bou Salem",
    "Ez Zahra",
    "Kalaa Srira",
    "Skhira",
    "Akouda",
    "El Ksar",
    "Mateur",
    "Siliana",
    "Rhennouch",
    "Dahmani",
    "El Alia",
    "Ar Rudayyif",
    "Zaghouan",
)


def _normalize_text_list(
    value,
    *,
    allow_comma_string=False,
    strict_items=False,
    max_item_length=None,
):
    if value is None:
        return []

    if isinstance(value, str):
        if not allow_comma_string:
            raise serializers.ValidationError("Expected a list of strings.")
        if value == "":
            return []
        raw_items = value.split(",")
    elif isinstance(value, list) or (
        allow_comma_string and isinstance(value, (tuple, set))
    ):
        raw_items = value
    else:
        raise serializers.ValidationError("Expected a list of strings.")

    cleaned = []
    seen = set()
    for item in raw_items:
        if strict_items and not isinstance(item, str):
            raise serializers.ValidationError("Each item must be a string.")

        text = item.strip() if isinstance(item, str) else str(item).strip()
        if not text:
            continue
        if max_item_length is not None and len(text) > max_item_length:
            raise serializers.ValidationError(
                f"Each item must be at most {max_item_length} characters."
            )
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(text)
    return cleaned


def _coerce_text_list(value):
    return _normalize_text_list(value, allow_comma_string=True)


def _collapse_location_spacing(value):
    text = re.sub(r"\s+", " ", value.strip())
    return re.sub(r"\s*-\s*", "-", text)


def _strip_accents(value):
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def _profile_term_key(value):
    text = _strip_accents(str(value or "").strip()).casefold()
    text = re.sub(r"[-\s]+", "_", text)
    text = re.sub(r"[^a-z0-9_]+", "", text)
    return re.sub(r"_+", "_", text).strip("_")


def _normalize_safe_profile_text(value):
    text = re.sub(r"\s+", " ", str(value or "").strip())
    text = "".join(
        char
        for char in text
        if unicodedata.category(char)[0] != "C"
    )
    text = re.sub(r"\s+", " ", text).strip()
    if text and UNSAFE_PROFILE_TEXT_PATTERN.search(text):
        raise serializers.ValidationError(
            "Remove HTML, scripts, or unsafe markup from profile fields."
        )
    return text


def _normalize_safe_profile_list(
    value,
    *,
    max_items=MAX_PROFILE_LIST_ITEMS,
    max_item_length=PROFILE_LIST_ITEM_MAX_LENGTH,
):
    cleaned = []
    seen = set()
    for item in _normalize_text_list(
        value,
        strict_items=True,
        max_item_length=max_item_length,
    ):
        text = _normalize_safe_profile_text(item)
        if not text:
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(text)

    if len(cleaned) > max_items:
        raise serializers.ValidationError(f"Choose at most {max_items} items.")
    return cleaned


def _normalize_profile_business_families(value):
    cleaned = []
    seen = set()
    raw_items = _normalize_safe_profile_list(
        value,
        max_items=MAX_PROFILE_BUSINESS_FAMILIES,
        max_item_length=PROFILE_LIST_ITEM_MAX_LENGTH,
    )
    for item in raw_items:
        key = _profile_term_key(item)
        canonical = PROFILE_BUSINESS_FAMILY_ALIASES.get(key) or normalize_family(key)
        if not canonical or canonical not in CONTROLLED_FAMILIES:
            continue
        canonical = PROFILE_BUSINESS_FAMILY_ALIASES.get(canonical, canonical)
        if canonical in seen:
            continue
        seen.add(canonical)
        cleaned.append(canonical)

    if not cleaned:
        raise serializers.ValidationError("Choose at least one sector.")
    return cleaned


def _location_lookup_key(value):
    text = _strip_accents(_collapse_location_spacing(value))
    text = text.replace("-", " ")
    return re.sub(r"\s+", " ", text).strip().casefold()


TUNISIAN_LOCATION_BY_KEY = {
    _location_lookup_key(location): location
    for location in TUNISIAN_LOCATIONS
}


def _normalize_required_profile_text(value):
    text = re.sub(r"\s+", " ", (value or "").strip())
    if not text:
        raise serializers.ValidationError("This field may not be blank.")
    return text


def _normalize_candidate_name(value):
    text = re.sub(r"\s+", " ", (value or "").strip())
    if not text:
        return ""
    if len(text) < 2 or len(text) > 100:
        raise serializers.ValidationError(PROFILE_NAME_LENGTH_ERROR)
    return text


def _normalize_optional_url(value):
    if value in (None, ""):
        return ""
    return str(value).strip()


def _has_expected_logo_signature(uploaded_file, extension):
    position = uploaded_file.tell() if hasattr(uploaded_file, "tell") else 0
    header = uploaded_file.read(12)
    if hasattr(uploaded_file, "seek"):
        uploaded_file.seek(position)

    if extension == ".png":
        return header.startswith(b"\x89PNG\r\n\x1a\n")
    if extension in {".jpg", ".jpeg"}:
        return header.startswith(b"\xff\xd8\xff")
    if extension == ".webp":
        return header.startswith(b"RIFF") and header[8:12] == b"WEBP"
    return False


def _normalize_tunisian_phone(value):
    phone = re.sub(r"\s+", "", (value or "").strip())
    if not TUNISIA_PHONE_PATTERN.fullmatch(phone):
        raise serializers.ValidationError(
            "Enter a Tunisia phone number in the format +21612345678."
        )
    return phone


def _normalize_custom_location(value):
    letters = [char for char in value if char.isalpha()]
    if letters and (
        all(char.islower() for char in letters)
        or all(char.isupper() for char in letters)
    ):
        return value.title()
    return value


def _normalize_location(value):
    text = _collapse_location_spacing(value)
    if not text:
        return ""

    canonical = TUNISIAN_LOCATION_BY_KEY.get(_location_lookup_key(text))
    if canonical:
        return canonical

    return _normalize_custom_location(text)


def _normalize_location_list(value, *, strict_payload=True):
    if not isinstance(value, list):
        if strict_payload:
            raise serializers.ValidationError("Expected a list of locations.")
        if value is None:
            return []
        if isinstance(value, str):
            value = [value]
        else:
            return []

    cleaned = []
    seen = set()
    for item in value:
        if not isinstance(item, str):
            raise serializers.ValidationError("Each location must be a string.")

        text = _normalize_location(item)
        if not text:
            continue
        if len(text) > LOCATION_ITEM_MAX_LENGTH:
            raise serializers.ValidationError(
                f"Each location must be at most {LOCATION_ITEM_MAX_LENGTH} characters."
            )

        key = _location_lookup_key(text)
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(text)

    if len(cleaned) > MAX_PREFERRED_LOCATIONS:
        raise serializers.ValidationError(
            f"Choose at most {MAX_PREFERRED_LOCATIONS} preferred locations."
        )

    return cleaned


def _normalize_profile_employment_types(
    value,
    *,
    strict_payload=True,
    reject_unknown=True,
):
    if not isinstance(value, list):
        if strict_payload:
            raise serializers.ValidationError("Expected a list of employment types.")
        if value is None:
            return []
        if isinstance(value, str):
            value = [value]
        else:
            return []

    cleaned = []
    seen = set()
    for item in value:
        if not isinstance(item, str):
            raise serializers.ValidationError("Each employment type must be a string.")

        text = item.strip()
        if not text:
            continue

        upper_text = text.upper()
        canonical_values = (
            [upper_text]
            if upper_text in CANONICAL_CONTRACT_TYPES
            else normalize_contract_types(text)
        )
        if not canonical_values:
            if not reject_unknown:
                continue
            raise serializers.ValidationError(
                f"Unsupported employment type preference: {text}."
            )

        for canonical in canonical_values:
            if canonical in seen:
                continue
            seen.add(canonical)
            cleaned.append(canonical)

    return cleaned


def _normalize_work_mode_preference(value):
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise serializers.ValidationError("Expected a work mode string.")

    text = value.strip()
    if not text:
        return None

    upper_text = text.upper()
    canonical = (
        upper_text
        if upper_text in CANONICAL_PROFILE_WORK_MODES
        else normalize_work_mode(text)
    )
    if canonical == WORK_MODE_UNSPECIFIED or canonical not in CANONICAL_PROFILE_WORK_MODES:
        raise serializers.ValidationError(
            f"Unsupported work mode preference: {text}."
        )
    return canonical


def _normalize_work_mode_list(value, *, strict_payload=True):
    if not isinstance(value, list):
        if strict_payload:
            raise serializers.ValidationError("Expected a list of work mode preferences.")
        if value is None:
            return []
        if isinstance(value, str):
            value = [value]
        else:
            return []

    cleaned = []
    seen = set()
    for item in value:
        if not isinstance(item, str):
            if strict_payload:
                raise serializers.ValidationError(
                    "Each work mode preference must be a string."
                )
            continue
        canonical = _normalize_work_mode_preference(item)
        if not canonical or canonical in seen:
            continue
        seen.add(canonical)
        cleaned.append(canonical)

    return cleaned


class TextListField(serializers.Field):
    def to_internal_value(self, data):
        return _coerce_text_list(data)

    def to_representation(self, value):
        return _coerce_text_list(value)


class ProfileTextListField(serializers.Field):
    def to_internal_value(self, data):
        return _normalize_text_list(
            data,
            strict_items=True,
            max_item_length=PROFILE_LIST_ITEM_MAX_LENGTH,
        )

    def to_representation(self, value):
        return _coerce_text_list(value)


class PreferredLocationsField(serializers.Field):
    def to_internal_value(self, data):
        return _normalize_location_list(data)

    def to_representation(self, value):
        return _normalize_location_list(value, strict_payload=False)


class LegacyPreferredLocationField(serializers.Field):
    def to_internal_value(self, data):
        if data is None or data == "":
            return []
        if not isinstance(data, str):
            raise serializers.ValidationError("Expected a location string.")
        return _normalize_location_list([data])

    def to_representation(self, value):
        locations = _normalize_location_list(value, strict_payload=False)
        return locations[0] if locations else None


class EmploymentTypesField(serializers.Field):
    def to_internal_value(self, data):
        return _normalize_profile_employment_types(data)

    def to_representation(self, value):
        return _normalize_profile_employment_types(
            value,
            strict_payload=False,
            reject_unknown=False,
        )


class WorkModePreferencesField(serializers.Field):
    def to_internal_value(self, data):
        return _normalize_work_mode_list(data)

    def to_representation(self, value):
        return _normalize_work_mode_list(value, strict_payload=False)


class LegacyRemotePreferenceField(serializers.Field):
    def to_internal_value(self, data):
        return _normalize_work_mode_preference(data)

    def to_representation(self, value):
        try:
            return _normalize_work_mode_preference(value)
        except serializers.ValidationError:
            return None


class ProfileResumeSerializer(serializers.ModelSerializer):
    file = serializers.FileField(write_only=True, required=False)
    file_url = serializers.SerializerMethodField()
    parsed_text_available = serializers.SerializerMethodField()
    profile_suggestions = serializers.SerializerMethodField()

    class Meta:
        model = ProfileResume
        fields = [
            "id",
            "file",
            "file_url",
            "uploaded_at",
            "source_type",
            "is_active",
            "metadata",
            "parsing_status",
            "parsing_error",
            "parsed_at",
            "parsed_text_available",
            "semantic_resume_status",
            "semantic_resume_confidence",
            "semantic_resume_updated_at",
            "semantic_resume_version",
            "semantic_resume_metadata",
            "extracted_skills",
            "profile_suggestions",
        ]
        read_only_fields = [
            "id",
            "file_url",
            "uploaded_at",
            "is_active",
            "metadata",
            "parsing_status",
            "parsing_error",
            "parsed_at",
            "parsed_text_available",
            "semantic_resume_status",
            "semantic_resume_confidence",
            "semantic_resume_updated_at",
            "semantic_resume_version",
            "semantic_resume_metadata",
            "extracted_skills",
            "profile_suggestions",
        ]

    def get_file_url(self, obj):
        if not obj.file:
            return None
        request = self.context.get("request")
        url = obj.file.url
        if request and not urlparse(url).scheme:
            return request.build_absolute_uri(url)
        return url

    def get_parsed_text_available(self, obj):
        return bool(getattr(obj, "parsed_text", ""))

    def get_profile_suggestions(self, obj):
        metadata = getattr(obj, "semantic_resume_metadata", {}) or {}
        if not isinstance(metadata, dict):
            return {}
        if metadata.get("profile_suggestions_applied_at"):
            return {}
        enrichment = metadata.get("llm_enrichment") or {}
        if not isinstance(enrichment, dict):
            return {}
        suggestions = enrichment.get("profile_suggestions") or {}
        return suggestions if isinstance(suggestions, dict) else {}

    def validate_file(self, value):
        if not value:
            raise serializers.ValidationError("Resume file is required.")

        extension = Path(value.name or "").suffix.lower()
        if extension not in ALLOWED_RESUME_EXTENSIONS:
            raise serializers.ValidationError("Use a PDF, DOCX, DOC, RTF, or TXT resume.")

        if getattr(value, "size", 0) > MAX_RESUME_FILE_SIZE_BYTES:
            raise serializers.ValidationError("Resume file must be 5 MB or smaller.")

        content_type = getattr(value, "content_type", "")
        if content_type and content_type not in ALLOWED_RESUME_CONTENT_TYPES:
            raise serializers.ValidationError("Unsupported resume file type.")

        return value

    def create(self, validated_data):
        profile = self.context["profile"]
        uploaded_file = validated_data.get("file")
        activate_resume = self.context.get("activate_resume", True)
        resume = ProfileResume.objects.create(
            profile=profile,
            file=uploaded_file,
            source_type=ProfileResume.SourceType.UPLOAD,
            parsed_text="",
            parsing_status=ProfileResume.ParsingStatus.PENDING,
            parsing_error="",
            parsed_at=None,
            resume_text_embedding_source="",
            metadata={
                "original_filename": Path(uploaded_file.name or "").name if uploaded_file else "",
                "content_type": getattr(uploaded_file, "content_type", ""),
                "size": getattr(uploaded_file, "size", 0),
            },
            is_active=activate_resume,
        )
        resume.metadata = {
            **(resume.metadata or {}),
            "stored_name": resume.file.name or "",
            "storage_provider": "cloudinary" if getattr(settings, "PROFILE_RESUME_USE_CLOUDINARY", False) else "local",
        }
        resume.save(update_fields=["metadata"])
        return resume


class ProfilSerializer(serializers.ModelSerializer):
    competences = ProfileTextListField(read_only=True)
    domaines_interet = ProfileTextListField(read_only=True)
    preferred_locations = PreferredLocationsField(read_only=True)
    preferred_location = serializers.SerializerMethodField()
    work_mode_preferences = WorkModePreferencesField(read_only=True)
    remote_preference = serializers.SerializerMethodField()
    employment_types = EmploymentTypesField(read_only=True)
    active_resume = serializers.SerializerMethodField()
    profile_completion = serializers.SerializerMethodField()

    class Meta:
        model = Profil
        fields = [
            'id', 'nom', 'prenom', 'competences', 'domaines_interet',
            'niveau_experience', 'annees_experience',
            'opportunity_types', 'preferred_locations', 'preferred_location',
            'remote_preference', 'work_mode_preferences',
            'compensation_expectation', 'compensation_min_expectation',
            'compensation_max_expectation', 'compensation_currency', 'compensation_period',
            'employment_types', 'target_roles', 'profile_visibility',
            'onboarding_completed', 'last_onboarding_step',
            'active_resume', 'profile_completion',
        ]
        read_only_fields = ['id']

    def get_preferred_location(self, obj):
        locations = _normalize_location_list(
            getattr(obj, "preferred_locations", []),
            strict_payload=False,
        )
        return locations[0] if locations else None

    def get_remote_preference(self, obj):
        modes = _normalize_work_mode_list(
            getattr(obj, "work_mode_preferences", []),
            strict_payload=False,
        )
        if modes:
            return modes[0]
        try:
            return _normalize_work_mode_preference(getattr(obj, "remote_preference", None))
        except serializers.ValidationError:
            return None

    def get_active_resume(self, obj):
        prefetched = getattr(obj, "_prefetched_objects_cache", {}).get("resumes")
        if prefetched is not None:
            active_resume = next((resume for resume in prefetched if resume.is_active), None)
        else:
            active_resume = obj.resumes.filter(is_active=True).order_by("-uploaded_at", "-id").first()
        if not active_resume:
            return None
        return ProfileResumeSerializer(active_resume, context=self.context).data

    def get_profile_completion(self, obj):
        return calculate_profile_completion(obj)


class OrganizationProfileSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(
        max_length=180,
        trim_whitespace=True,
        allow_blank=False,
    )
    first_name = serializers.CharField(
        max_length=100,
        trim_whitespace=True,
        allow_blank=False,
    )
    last_name = serializers.CharField(
        max_length=100,
        trim_whitespace=True,
        allow_blank=False,
    )
    website = serializers.URLField(
        max_length=255,
        required=False,
        allow_blank=True,
    )
    logo = serializers.URLField(
        max_length=1000,
        required=False,
        allow_blank=True,
    )
    phone = serializers.CharField(
        max_length=16,
        trim_whitespace=True,
        allow_blank=False,
    )
    organization_type = serializers.ChoiceField(
        choices=OrganizationProfile.OrganizationType.choices,
    )

    class Meta:
        model = OrganizationProfile
        fields = [
            "id",
            "organization_name",
            "first_name",
            "last_name",
            "website",
            "logo",
            "phone",
            "organization_type",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_organization_name(self, value):
        return _normalize_required_profile_text(value)

    def validate_first_name(self, value):
        return _normalize_required_profile_text(value)

    def validate_last_name(self, value):
        return _normalize_required_profile_text(value)

    def validate_website(self, value):
        return _normalize_optional_url(value)

    def validate_logo(self, value):
        normalized = _normalize_optional_url(value)
        if normalized and not is_valid_image_url(normalized):
            raise serializers.ValidationError("Enter a valid public image URL.")
        return normalized

    def validate_phone(self, value):
        return _normalize_tunisian_phone(value)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("Submit at least one organization profile field.")
        return attrs

    def _clean_or_raise(self, instance):
        try:
            instance.full_clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict) from exc

    def create(self, validated_data):
        user = self.context["user"]
        instance = OrganizationProfile(user=user, **validated_data)
        self._clean_or_raise(instance)
        instance.save()
        return instance

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        self._clean_or_raise(instance)
        instance.save()
        return instance


class OrganizationLogoUploadSerializer(serializers.Serializer):
    file = serializers.FileField()

    def validate_file(self, value):
        extension = Path(value.name or "").suffix.lower()
        if extension not in ALLOWED_ORGANIZATION_LOGO_EXTENSIONS:
            raise serializers.ValidationError("Use a PNG, JPG, JPEG, or WEBP image.")

        if getattr(value, "size", 0) > MAX_ORGANIZATION_LOGO_SIZE_BYTES:
            raise serializers.ValidationError("Logo must be 2 MB or smaller.")

        content_type = getattr(value, "content_type", "")
        if content_type and content_type not in ALLOWED_ORGANIZATION_LOGO_CONTENT_TYPES:
            raise serializers.ValidationError("Unsupported logo file type.")

        if not _has_expected_logo_signature(value, extension):
            raise serializers.ValidationError("Uploaded file does not look like a valid image.")

        return value


class UtilisateurSerializer(serializers.ModelSerializer):
    profil = ProfilSerializer(read_only=True)
    organization_profile = serializers.SerializerMethodField()
    is_admin = serializers.SerializerMethodField()

    class Meta:
        model = Utilisateur
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'account_type', 'is_active', 'is_admin', 'date_joined',
            'profil', 'organization_profile',
        ]
        read_only_fields = ['id', 'date_joined']

    def get_is_admin(self, obj):
        return bool(obj.is_admin or obj.is_staff or obj.is_superuser)

    def get_organization_profile(self, obj):
        try:
            profile = obj.organization_profile
        except OrganizationProfile.DoesNotExist:
            return None
        return OrganizationProfileSerializer(profile, context=self.context).data


class ProfilUpdateSerializer(serializers.ModelSerializer):
    """Serializer pour permettre à l'utilisateur de modifier son profil."""
    # CharField fields accept blank=True in the model but not null;
    # the frontend may send null for unset values, so we convert it.
    niveau_experience = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    competences = ProfileTextListField(required=False)
    domaines_interet = ProfileTextListField(required=False)
    opportunity_types = TextListField(required=False, allow_null=True)
    preferred_locations = PreferredLocationsField(required=False)
    preferred_location = LegacyPreferredLocationField(required=False, write_only=True)
    remote_preference = LegacyRemotePreferenceField(required=False, allow_null=True)
    work_mode_preferences = WorkModePreferencesField(required=False)
    employment_types = EmploymentTypesField(required=False)
    target_roles = TextListField(required=False, allow_null=True)
    compensation_currency = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    compensation_period = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    EMBEDDING_FEATURE_FIELDS = {
        'competences',
        'domaines_interet',
        'niveau_experience',
        'annees_experience',
        'preferred_locations',
        'work_mode_preferences',
        'remote_preference',
        'compensation_expectation',
        'compensation_min_expectation',
        'compensation_max_expectation',
        'compensation_currency',
        'compensation_period',
        'employment_types',
        'target_roles',
    }

    class Meta:
        model = Profil
        fields = [
            'nom', 'prenom', 'competences', 'domaines_interet',
            'niveau_experience', 'annees_experience',
            'opportunity_types', 'preferred_locations', 'preferred_location',
            'remote_preference', 'work_mode_preferences',
            'compensation_expectation', 'compensation_min_expectation',
            'compensation_max_expectation', 'compensation_currency', 'compensation_period',
            'employment_types', 'target_roles', 'profile_visibility',
            'onboarding_completed', 'last_onboarding_step',
        ]

    def validate_nom(self, value):
        return _normalize_candidate_name(value)

    def validate_prenom(self, value):
        return _normalize_candidate_name(value)

    def validate_niveau_experience(self, value):
        """Convert null to empty string for the CharField."""
        return value if value is not None else ''

    def validate_annees_experience(self, value):
        if value is None:
            return None
        if value < 0 or value > 60:
            raise serializers.ValidationError("Enter a realistic number of years of experience.")
        return value

    def validate_competences(self, value):
        return normalize_profile_terms(
            ProfileSuggestionType.SKILL,
            _normalize_safe_profile_list(value),
        )

    def validate_domaines_interet(self, value):
        return _normalize_profile_business_families(value)

    def validate_opportunity_types(self, value):
        cleaned = []
        seen = set()
        for item in _coerce_text_list(value):
            canonical = str(item).strip().upper()
            if canonical not in CANONICAL_OPPORTUNITY_TYPES:
                raise serializers.ValidationError("Select a valid opportunity type.")
            if canonical in seen:
                continue
            seen.add(canonical)
            cleaned.append(canonical)
        return cleaned

    def validate_employment_types(self, value):
        return value

    def validate_target_roles(self, value):
        return normalize_profile_terms(
            ProfileSuggestionType.ROLE,
            _normalize_safe_profile_list(value, max_items=MAX_PROFILE_TARGET_ROLES),
            preserve_unknown_roles=True,
        )

    def validate_compensation_currency(self, value):
        if value in (None, ""):
            return DEFAULT_COMPENSATION_CURRENCY
        currency = str(value).strip().upper()
        if currency != DEFAULT_COMPENSATION_CURRENCY:
            raise serializers.ValidationError("Only TND is currently supported.")
        return currency

    def validate_compensation_period(self, value):
        if value in (None, ""):
            return "MONTHLY"
        period = str(value).strip().upper()
        if period not in CANONICAL_COMPENSATION_PERIODS:
            raise serializers.ValidationError("Only monthly salary expectations are supported.")
        return period

    def _validate_compensation(self, attrs):
        compensation_fields = {
            "compensation_expectation",
            "compensation_min_expectation",
            "compensation_max_expectation",
            "compensation_period",
        }
        if not compensation_fields.intersection(attrs):
            return attrs

        period = attrs.get(
            "compensation_period",
            getattr(self.instance, "compensation_period", None),
        ) or "MONTHLY"
        limits = SALARY_LIMITS_BY_PERIOD.get(period)
        if not limits:
            raise serializers.ValidationError({"compensation_period": "Unsupported compensation period."})

        minimum, maximum = limits
        values = {
            "compensation_expectation": attrs.get(
                "compensation_expectation",
                getattr(self.instance, "compensation_expectation", None),
            ),
            "compensation_min_expectation": attrs.get(
                "compensation_min_expectation",
                getattr(self.instance, "compensation_min_expectation", None),
            ),
            "compensation_max_expectation": attrs.get(
                "compensation_max_expectation",
                getattr(self.instance, "compensation_max_expectation", None),
            ),
        }

        for field, amount in values.items():
            if amount is None:
                continue
            if amount < minimum:
                raise serializers.ValidationError({field: MIN_MONTHLY_SALARY_TND_ERROR})
            if amount > maximum:
                raise serializers.ValidationError({
                    field: f"Expected salary is too high for {period.lower()} TND."
                })

        min_amount = values["compensation_min_expectation"]
        max_amount = values["compensation_max_expectation"]
        if min_amount is not None and max_amount is not None and min_amount > max_amount:
            raise serializers.ValidationError({
                "compensation_max_expectation": "Maximum salary must be greater than or equal to minimum salary."
            })
        return attrs

    def validate(self, attrs):
        legacy_locations = attrs.pop('preferred_location', serializers.empty)
        if legacy_locations is not serializers.empty:
            if 'preferred_locations' in attrs:
                if legacy_locations != attrs['preferred_locations']:
                    raise serializers.ValidationError({
                        'preferred_location': (
                            "Do not send preferred_location together with a "
                            "different preferred_locations value."
                        )
                    })
            else:
                attrs['preferred_locations'] = legacy_locations

        legacy_remote = attrs.pop('remote_preference', serializers.empty)
        if legacy_remote is serializers.empty:
            if 'work_mode_preferences' in attrs:
                attrs['remote_preference'] = (
                    attrs['work_mode_preferences'][0]
                    if attrs['work_mode_preferences']
                    else None
                )
            return self._validate_compensation(attrs)

        legacy_modes = [legacy_remote] if legacy_remote else []
        if 'work_mode_preferences' in attrs:
            if legacy_modes != attrs['work_mode_preferences']:
                raise serializers.ValidationError({
                    'remote_preference': (
                        "Do not send remote_preference together with a "
                        "different work_mode_preferences value."
                    )
                })
        else:
            attrs['work_mode_preferences'] = legacy_modes

        attrs['remote_preference'] = legacy_remote

        return self._validate_compensation(attrs)

    def update(self, instance, validated_data):
        should_invalidate_embedding = bool(
            self.EMBEDDING_FEATURE_FIELDS.intersection(validated_data.keys())
        )
        should_refresh_skill_normalization = "competences" in validated_data
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if should_refresh_skill_normalization:
            instance.raw_skills = _normalize_text_list(
                validated_data.get("competences", []),
                strict_items=True,
                max_item_length=PROFILE_LIST_ITEM_MAX_LENGTH,
            )
            instance.normalized_skills = []
            instance.skills_normalization_hash = ""
            instance.skills_normalization_updated_at = None
            instance.skills_normalization_error = ""

        if should_invalidate_embedding:
            instance.embedding = None
            instance.embedding_features_hash = ''
            instance.last_embedding_update = None
            instance.embedding_model = ''
            instance.embedding_dimensions = None
            instance.embedding_updated_at = None
            instance.embedding_content_hash = ''

        instance.save()
        if should_invalidate_embedding:
            transaction.on_commit(
                lambda profile_id=instance.pk: enqueue_profile_embedding_refresh(profile_id)
            )
        return instance


# ── Passwordless OTP serializers ───────────────────────────

class OTPRequestSerializer(serializers.Serializer):
    """Validates the email submitted when requesting an OTP."""
    email = serializers.EmailField(required=True)
    client_type = serializers.ChoiceField(
        choices=[("web", "web"), ("mobile", "mobile")],
        required=False,
        default="web",
    )


class OTPVerifySerializer(serializers.Serializer):
    """Validates email + 6-digit OTP code for passwordless login."""
    email = serializers.EmailField(required=True)
    otp = serializers.CharField(required=True, min_length=6, max_length=6)


class UserSuspensionSerializer(serializers.Serializer):
    """Validates suspension request with reason and optional detail."""
    
    SUSPENSION_REASONS = {
        "spam": "Spam",
        "abuse": "Abuse",
        "fraud": "Fraud",
        "other": "Other",
    }
    
    reason = serializers.ChoiceField(
        choices=list(SUSPENSION_REASONS.keys()),
        required=True,
        error_messages={
            "required": "Reason is required.",
            "invalid_choice": "Reason must be one of: spam, abuse, fraud, other.",
        }
    )
    detail = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        trim_whitespace=True,
    )
    
    def validate(self, data):
        """Validate that detail is required if reason is 'other'."""
        reason = data.get("reason")
        detail = data.get("detail", "").strip()
        
        if reason == "other" and not detail:
            raise serializers.ValidationError(
                {"detail": "Detail is required when reason is 'other'."}
            )
        
        # Clean up empty/whitespace-only detail
        if not detail:
            data["detail"] = ""
        else:
            data["detail"] = detail
        
        return data


# ── Admin user list ───────────────────────────────────────────────────────────

class AdminUserListSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for the admin user management table.

    Exposes only the fields needed for the MVP table:
      email, account_type, is_admin, is_active, is_suspended,
      date_joined, last_login, display_name
    """

    display_name = serializers.SerializerMethodField(
        help_text="Best available display name: first+last name or email fallback."
    )

    class Meta:
        model = Utilisateur
        fields = [
            "id",
            "email",
            "display_name",
            "account_type",
            "is_admin",
            "is_active",
            "is_suspended",
            "suspension_reason",
            "suspended_at",
            "date_joined",
            "last_login",
        ]
        read_only_fields = fields

    def get_display_name(self, obj: Utilisateur) -> str:
        # Prefer profil nom/prenom if the related object is prefetched
        profil = getattr(obj, "profil", None)
        if profil:
            full = f"{profil.prenom} {profil.nom}".strip()
            if full:
                return full
        # Fallback: Django first_name / last_name
        full = f"{obj.first_name} {obj.last_name}".strip()
        return full or obj.email


# ── Audit log (read-only) ─────────────────────────────────────────────────────

class AdminAuditLogSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for the audit log feed.
    Embeds actor and target as lightweight email-only objects.
    """

    actor_email  = serializers.EmailField(source="actor.email",  default=None, read_only=True)
    target_email = serializers.EmailField(source="target.email", default=None, read_only=True)
    action_label = serializers.CharField(source="get_action_display", read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "action",
            "action_label",
            "actor_email",
            "target_email",
            "metadata",
            "created_at",
        ]
        read_only_fields = fields
