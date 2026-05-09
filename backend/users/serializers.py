import re
import unicodedata
from pathlib import Path

from django.db import transaction
from rest_framework import serializers
from ai.embeddings import enqueue_profile_embedding_refresh
from .models import Utilisateur, Profil, ProfileResume
from opportunities.autocomplete.service import normalize_profile_terms
from opportunities.normalization.employment import (
    CANONICAL_CONTRACT_TYPES,
    WORK_MODE_UNSPECIFIED,
    normalize_contract_types,
    normalize_work_mode,
)
from opportunities.models import ProfileSuggestionType
from .profile_completion import calculate_profile_completion


PROFILE_LIST_ITEM_MAX_LENGTH = 100
LOCATION_ITEM_MAX_LENGTH = 100
MAX_PREFERRED_LOCATIONS = 10
CANONICAL_PROFILE_WORK_MODES = ("REMOTE", "HYBRID", "ON_SITE")
DEFAULT_COMPENSATION_CURRENCY = "TND"
CANONICAL_COMPENSATION_PERIODS = ("MONTHLY", "YEARLY", "DAILY", "HOURLY")
SALARY_LIMITS_BY_PERIOD = {
    "MONTHLY": (200, 30000),
    "YEARLY": (2400, 360000),
    "DAILY": (10, 1500),
    "HOURLY": (2, 150),
}
MAX_RESUME_FILE_SIZE_BYTES = 5 * 1024 * 1024
ALLOWED_RESUME_EXTENSIONS = {".pdf", ".docx"}
ALLOWED_RESUME_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
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


def _location_lookup_key(value):
    text = _strip_accents(_collapse_location_spacing(value))
    text = text.replace("-", " ")
    return re.sub(r"\s+", " ", text).strip().casefold()


TUNISIAN_LOCATION_BY_KEY = {
    _location_lookup_key(location): location
    for location in TUNISIAN_LOCATIONS
}


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
        ]

    def get_file_url(self, obj):
        if not obj.file:
            return None
        request = self.context.get("request")
        url = obj.file.url
        return request.build_absolute_uri(url) if request else url

    def get_parsed_text_available(self, obj):
        return bool(getattr(obj, "parsed_text", ""))

    def validate_file(self, value):
        if not value:
            raise serializers.ValidationError("Resume file is required.")

        extension = Path(value.name or "").suffix.lower()
        if extension not in ALLOWED_RESUME_EXTENSIONS:
            raise serializers.ValidationError("Upload a PDF or DOCX resume.")

        if getattr(value, "size", 0) > MAX_RESUME_FILE_SIZE_BYTES:
            raise serializers.ValidationError("Resume file must be 5 MB or smaller.")

        content_type = getattr(value, "content_type", "")
        if content_type and content_type not in ALLOWED_RESUME_CONTENT_TYPES:
            raise serializers.ValidationError("Unsupported resume file type.")

        return value

    def create(self, validated_data):
        profile = self.context["profile"]
        uploaded_file = validated_data.get("file")
        return ProfileResume.objects.create(
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
            is_active=True,
        )


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
            'compensation_expectation', 'compensation_currency', 'compensation_period',
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


class UtilisateurSerializer(serializers.ModelSerializer):
    profil = ProfilSerializer(read_only=True)
    is_admin = serializers.SerializerMethodField()

    class Meta:
        model = Utilisateur
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'is_active', 'is_admin', 'date_joined', 'profil',
        ]
        read_only_fields = ['id', 'date_joined']

    def get_is_admin(self, obj):
        return bool(obj.is_admin or obj.is_staff or obj.is_superuser)


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
            'compensation_expectation', 'compensation_currency', 'compensation_period',
            'employment_types', 'target_roles', 'profile_visibility',
            'onboarding_completed', 'last_onboarding_step',
        ]

    def validate_niveau_experience(self, value):
        """Convert null to empty string for the CharField."""
        return value if value is not None else ''

    def validate_competences(self, value):
        return normalize_profile_terms(ProfileSuggestionType.SKILL, value)

    def validate_domaines_interet(self, value):
        return normalize_profile_terms(
            ProfileSuggestionType.INTEREST,
            _coerce_text_list(value),
            preserve_unknown=False,
        )

    def validate_opportunity_types(self, value):
        return _coerce_text_list(value)

    def validate_employment_types(self, value):
        return value

    def validate_target_roles(self, value):
        return normalize_profile_terms(ProfileSuggestionType.ROLE, _coerce_text_list(value))

    def validate_compensation_currency(self, value):
        if value in (None, ""):
            return DEFAULT_COMPENSATION_CURRENCY
        currency = str(value).strip().upper()
        if currency != DEFAULT_COMPENSATION_CURRENCY:
            raise serializers.ValidationError("Only TND is currently supported.")
        return currency

    def validate_compensation_period(self, value):
        if value in (None, ""):
            return None
        period = str(value).strip().upper()
        if period not in CANONICAL_COMPENSATION_PERIODS:
            raise serializers.ValidationError("Unsupported compensation period.")
        return period

    def _validate_compensation(self, attrs):
        if "compensation_expectation" not in attrs and "compensation_period" not in attrs:
            return attrs

        amount = attrs.get(
            "compensation_expectation",
            getattr(self.instance, "compensation_expectation", None),
        )
        if amount is None:
            return attrs

        period = attrs.get(
            "compensation_period",
            getattr(self.instance, "compensation_period", None),
        ) or "MONTHLY"
        limits = SALARY_LIMITS_BY_PERIOD.get(period)
        if not limits:
            raise serializers.ValidationError({"compensation_period": "Unsupported compensation period."})

        minimum, maximum = limits
        if amount < minimum:
            raise serializers.ValidationError({
                "compensation_expectation": f"Expected salary is too low for {period.lower()} TND."
            })
        if amount > maximum:
            raise serializers.ValidationError({
                "compensation_expectation": f"Expected salary is too high for {period.lower()} TND."
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
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

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
