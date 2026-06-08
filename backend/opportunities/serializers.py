from datetime import timedelta
import re
from pathlib import Path
from urllib.parse import urlparse

from rest_framework import serializers
from django.utils import timezone

from .models import Opportunite, SourceOpportunite, StatutOpportunite, TypeOpportunite
from .normalization import normalize_city_name
from .utils.images import normalize_company_logo_url
from users.serializers import TUNISIAN_LOCATIONS, _location_lookup_key


TUNISIAN_LOCATION_BY_KEY = {
    _location_lookup_key(location): location
    for location in TUNISIAN_LOCATIONS
}


class SourceOpportuniteSerializer(serializers.ModelSerializer):
    class Meta:
        model = SourceOpportunite
        fields = ['id', 'nom', 'url', 'type_source']


class OpportuniteSerializer(serializers.ModelSerializer):
    external_id = serializers.CharField(read_only=True)
    source_item_url = serializers.URLField(read_only=True, allow_null=True)
    company_logo = serializers.SerializerMethodField(read_only=True)
    contract_type = serializers.SerializerMethodField(read_only=True)
    education_level = serializers.SerializerMethodField(read_only=True)
    availability = serializers.SerializerMethodField(read_only=True)
    normalized_work_mode = serializers.CharField(read_only=True)
    experience = serializers.SerializerMethodField(read_only=True)
    salary = serializers.SerializerMethodField(read_only=True)
    skills = serializers.SerializerMethodField(read_only=True)
    normalized_industries = serializers.JSONField(read_only=True)
    languages = serializers.SerializerMethodField(read_only=True)
    languages_fallback = serializers.SerializerMethodField(read_only=True)
    extra_data = serializers.JSONField(read_only=True)
    source = SourceOpportuniteSerializer(read_only=True)
    last_updated_at = serializers.DateTimeField(source="date_modification", read_only=True)
    is_new = serializers.SerializerMethodField(read_only=True)
    source_id = serializers.PrimaryKeyRelatedField(
        queryset=SourceOpportunite.objects.all(), source='source', write_only=True
    )

    class Meta:
        model = Opportunite
        fields = [
            "id",
            "titre",
            "description",
            "description_html",
            "organisation_nom",
            "company_logo",
            "ville",
            "date_confidence",
            "quality_score",
            "type_opportunite",
            "statut",
            "date_publication",
            "date_limite",
            "external_id",
            "source_item_url",
            "contract_type",
            "experience",
            "education_level",
            "availability",
            "normalized_work_mode",
            "salary",
            "skills",
            "normalized_industries",
            "languages",
            "languages_fallback",
            "extra_data",
            "source",
            "source_id",
            "date_creation",
            "date_modification",
            "last_updated_at",
            "is_new",
        ]
        read_only_fields = [
            "id",
            "date_confidence",
            "quality_score",
            "date_creation",
            "date_modification",
            "last_updated_at",
            "is_new",
        ]

    @staticmethod
    def _as_list_of_text(value):
        if not isinstance(value, list):
            return None

        cleaned = []
        for item in value:
            text = str(item).strip()
            if text and text not in cleaned:
                cleaned.append(text)
        return cleaned or None

    def get_salary(self, obj):
        value = getattr(obj, "salary", None)
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _get_optional_text(self, obj, field_name):
        value = getattr(obj, field_name, None)
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def get_company_logo(self, obj):
        return normalize_company_logo_url(
            getattr(obj, "company_logo", ""),
            organization_name=getattr(obj, "organisation_nom", ""),
        )

    def get_contract_type(self, obj):
        return self._get_optional_text(obj, "contract_type")

    def get_education_level(self, obj):
        return self._get_optional_text(obj, "education_level")

    def get_availability(self, obj):
        return self._get_optional_text(obj, "availability")

    def get_experience(self, obj):
        legacy_years = getattr(obj, "experience_years", None)
        min_value = getattr(obj, "experience_min", None)
        max_value = getattr(obj, "experience_max", None)

        if min_value is None:
            min_value = legacy_years
        if max_value is None:
            max_value = legacy_years

        return {
            "min": min_value,
            "max": max_value,
        }

    def get_skills(self, obj):
        value = self._as_list_of_text(getattr(obj, "skills", None))
        return value or []

    def get_languages(self, obj):
        return self._as_list_of_text(getattr(obj, "languages", None))

    def get_languages_fallback(self, obj):
        return self._as_list_of_text(getattr(obj, "languages_fallback", None))

    def get_is_new(self, obj):
        created_at = getattr(obj, "date_creation", None)
        if created_at is None:
            return False
        return created_at >= timezone.now() - timedelta(hours=24)

    def to_internal_value(self, data):
        # Keep API backward-compatible: ignore legacy owner payload key.
        if isinstance(data, dict):
            data = data.copy()
            data.pop("organisation", None)
        return super().to_internal_value(data)

    def validate(self, attrs):
        """Business rule: date_limite must be >= date_publication when set."""
        # Support both create and partial update by falling back to instance values.
        date_publication = attrs.get('date_publication') or getattr(self.instance, 'date_publication', None)
        date_limite = attrs.get('date_limite') if 'date_limite' in attrs else getattr(self.instance, 'date_limite', None)

        if date_limite and date_publication and date_limite < date_publication:
            raise serializers.ValidationError({
                'date_limite': "La date limite ne peut pas être antérieure à la date de publication."
            })

        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["ville"] = normalize_city_name(data.get("ville"))
        return data


class SimilarOpportunitySerializer(serializers.ModelSerializer):
    similarity_score = serializers.SerializerMethodField(read_only=True)
    organisation_nom = serializers.SerializerMethodField(read_only=True)
    last_updated_at = serializers.DateTimeField(source="date_modification", read_only=True)
    is_new = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Opportunite
        fields = ["id", "titre", "organisation_nom", "similarity_score", "last_updated_at", "is_new"]
        read_only_fields = fields

    def get_organisation_nom(self, obj):
        value = getattr(obj, "organisation_nom", None)
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def get_similarity_score(self, obj):
        score = getattr(obj, "similarity_score", None)
        if score is None:
            return None
        try:
            return round(max(0.0, min(1.0, float(score))), 4)
        except (TypeError, ValueError):
            return None

    def get_is_new(self, obj):
        created_at = getattr(obj, "date_creation", None)
        if created_at is None:
            return False
        return created_at >= timezone.now() - timedelta(hours=24)


class OrganizationOpportunitySerializer(serializers.ModelSerializer):
    title = serializers.CharField(source="titre", read_only=True)
    type = serializers.CharField(source="type_opportunite", read_only=True)
    status = serializers.CharField(source="statut", read_only=True)
    location = serializers.CharField(source="ville", read_only=True)
    contract = serializers.CharField(source="contract_type", read_only=True)
    published_at = serializers.DateField(source="date_publication", read_only=True)
    deadline = serializers.DateField(source="date_limite", read_only=True)
    updated_at = serializers.DateTimeField(source="date_modification", read_only=True)
    applications_count = serializers.IntegerField(read_only=True)
    description = serializers.CharField(read_only=True)
    internship_details = serializers.SerializerMethodField(read_only=True)
    seasonal_details = serializers.SerializerMethodField(read_only=True)
    project_details = serializers.SerializerMethodField(read_only=True)
    suspended_from = serializers.SerializerMethodField(read_only=True)
    closed_from = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Opportunite
        fields = [
            "id",
            "title",
            "type",
            "status",
            "location",
            "contract",
            "availability",
            "experience_min",
            "experience_max",
            "education_level",
            "salary",
            "skills",
            "published_at",
            "deadline",
            "applications_count",
            "updated_at",
            "description",
            "internship_details",
            "seasonal_details",
            "project_details",
            "suspended_from",
            "closed_from",
        ]
        read_only_fields = fields

    def get_internship_details(self, obj):
        extra_data = getattr(obj, "extra_data", None)
        if not isinstance(extra_data, dict):
            return None
        details = extra_data.get("internship_details")
        return details if isinstance(details, dict) else None

    def get_seasonal_details(self, obj):
        extra_data = getattr(obj, "extra_data", None)
        if not isinstance(extra_data, dict):
            return None
        details = extra_data.get("seasonal_details")
        return details if isinstance(details, dict) else None

    def get_project_details(self, obj):
        extra_data = getattr(obj, "extra_data", None)
        if not isinstance(extra_data, dict):
            return None
        details = extra_data.get("project_details")
        return details if isinstance(details, dict) else None

    def get_suspended_from(self, obj):
        extra_data = getattr(obj, "extra_data", None)
        if not isinstance(extra_data, dict):
            return None
        organization_status = extra_data.get("organization_status")
        if not isinstance(organization_status, dict):
            return None
        value = organization_status.get("suspended_from")
        if value in {StatutOpportunite.ACTIVE, StatutOpportunite.PENDING_REVIEW}:
            return value
        return None

    def get_closed_from(self, obj):
        extra_data = getattr(obj, "extra_data", None)
        if not isinstance(extra_data, dict):
            return None
        organization_status = extra_data.get("organization_status")
        if not isinstance(organization_status, dict):
            return None
        value = organization_status.get("closed_from")
        if value in {
            StatutOpportunite.ACTIVE,
            StatutOpportunite.SUSPENDUE,
            StatutOpportunite.PENDING_REVIEW,
            StatutOpportunite.REJECTED,
        }:
            return value
        return None


class OrganizationOpportunityWriteSerializer(serializers.Serializer):
    MAX_TENDER_DOCUMENT_SIZE_BYTES = 5 * 1024 * 1024
    ALLOWED_TENDER_DOCUMENT_EXTENSIONS = {".pdf", ".docx", ".doc"}
    ALLOWED_TENDER_DOCUMENT_CONTENT_TYPES = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    }
    INTERNSHIP_TYPES = {
        "SUMMER",
        "TRAINING",
        "GRADUATION_PROJECT",
    }
    INTERNSHIP_DURATIONS = {
        "1_MONTH",
        "2_MONTHS",
        "3_MONTHS",
        "4_6_MONTHS",
        "6_PLUS_MONTHS",
    }
    SEASONS = {
        "SUMMER",
        "WINTER",
        "RAMADAN",
        "HOLIDAY",
        "EVENT",
        "OTHER",
    }
    PROJECT_DOCUMENT_TYPES = {
        "cahier_des_charges",
        "avis_appel_offres",
        "autres",
    }

    title = serializers.CharField(min_length=5, max_length=180, trim_whitespace=True)
    type = serializers.ChoiceField(choices=TypeOpportunite.choices)
    location = serializers.CharField(max_length=120, trim_whitespace=True)
    description = serializers.CharField(min_length=40, max_length=5000, trim_whitespace=True)
    contract = serializers.CharField(max_length=64, required=False, allow_blank=True, trim_whitespace=True)
    availability = serializers.CharField(max_length=120, required=False, allow_blank=True, trim_whitespace=True)
    experience_min = serializers.IntegerField(min_value=0, max_value=60, required=False, allow_null=True)
    experience_max = serializers.IntegerField(min_value=0, max_value=60, required=False, allow_null=True)
    education_level = serializers.CharField(max_length=120, required=False, allow_blank=True, trim_whitespace=True)
    salary = serializers.CharField(max_length=120, required=False, allow_blank=True, trim_whitespace=True)
    skills = serializers.ListField(
        child=serializers.CharField(max_length=64, trim_whitespace=True, allow_blank=True),
        required=False,
        allow_empty=True,
        max_length=15,
    )
    deadline = serializers.DateField(required=False, allow_null=True)
    internship_details = serializers.DictField(required=False, allow_empty=True)
    seasonal_details = serializers.DictField(required=False, allow_empty=True)
    project_details = serializers.DictField(required=False, allow_empty=True)
    turnstile_token = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=4096,
        trim_whitespace=True,
        write_only=True,
    )

    def validate_location(self, value):
        text = value.strip()
        if not text:
            raise serializers.ValidationError("Location is required.")
        canonical = TUNISIAN_LOCATION_BY_KEY.get(_location_lookup_key(text))
        if not canonical:
            raise serializers.ValidationError("Choose a valid Tunisian location.")
        return canonical

    def validate_skills(self, value):
        cleaned = []
        seen = set()
        for item in value:
            text = str(item).strip()
            if not text:
                continue
            key = text.casefold()
            if key in seen:
                continue
            seen.add(key)
            cleaned.append(text)
        return cleaned

    def validate_salary(self, value):
        text = str(value or "").strip()
        if not text:
            return ""
        if re.search(r"(^|[\s:])-\s*\d", text):
            raise serializers.ValidationError("Salary cannot be negative.")
        if len(text) < 2:
            raise serializers.ValidationError("Salary is too short.")
        return text

    def validate_deadline(self, value):
        if value and value < timezone.localdate():
            raise serializers.ValidationError("Deadline cannot be in the past.")
        return value

    def _validate_internship_details(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Internship details must be an object.")

        internship_type = str(value.get("internship_type") or "").strip().upper()
        duration = str(value.get("duration") or "").strip().upper()
        start_date = value.get("start_date")

        errors = {}
        if internship_type not in self.INTERNSHIP_TYPES:
            errors["internship_type"] = "Choose a valid internship type."
        if duration not in self.INTERNSHIP_DURATIONS:
            errors["duration"] = "Choose a valid internship duration."

        parsed_start_date = None
        if not start_date:
            errors["start_date"] = "Start date is required."
        else:
            date_field = serializers.DateField()
            try:
                parsed_start_date = date_field.to_internal_value(start_date)
            except serializers.ValidationError:
                errors["start_date"] = "Enter a valid start date."

        if parsed_start_date and parsed_start_date < timezone.localdate():
            errors["start_date"] = "Start date cannot be in the past."

        if errors:
            raise serializers.ValidationError(errors)

        return {
            "internship_type": internship_type,
            "duration": duration,
            "start_date": parsed_start_date.isoformat(),
        }

    def _parse_required_future_date(self, value, field_name):
        if not value:
            raise serializers.ValidationError({field_name: "This date is required."})
        date_field = serializers.DateField()
        try:
            parsed = date_field.to_internal_value(value)
        except serializers.ValidationError:
            raise serializers.ValidationError({field_name: "Enter a valid date."})
        if parsed < timezone.localdate():
            raise serializers.ValidationError({field_name: "Date cannot be in the past."})
        return parsed

    def _validate_seasonal_details(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Seasonal details must be an object.")

        season = str(value.get("season") or "").strip().upper()
        errors = {}
        if season not in self.SEASONS:
            errors["season"] = "Choose a valid season."

        start_date = None
        end_date = None
        for field_name in ("start_date", "end_date"):
            try:
                parsed_date = self._parse_required_future_date(value.get(field_name), field_name)
            except serializers.ValidationError as exc:
                errors.update(exc.detail)
            else:
                if field_name == "start_date":
                    start_date = parsed_date
                else:
                    end_date = parsed_date

        if start_date and end_date and end_date < start_date:
            errors["end_date"] = "End date must be greater than or equal to start date."

        if errors:
            raise serializers.ValidationError(errors)

        return {
            "season": season,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }

    def _clean_short_text(self, value, *, max_length=180):
        text = str(value or "").strip()
        if len(text) > max_length:
            raise serializers.ValidationError(f"Use {max_length} characters or less.")
        return text

    def _validate_positive_integer_text(self, value, field_name, *, required=False):
        text = str(value or "").strip()
        if not text:
            if required:
                raise serializers.ValidationError({field_name: "This field is required."})
            return ""
        if not text.isdigit():
            raise serializers.ValidationError({field_name: "Use a positive whole number."})
        if int(text) < 0:
            raise serializers.ValidationError({field_name: "Use a positive whole number."})
        return text

    def _validate_document_url(self, value, field_name):
        text = str(value or "").strip()
        if not text:
            return ""
        url_field = serializers.URLField(max_length=500)
        try:
            cleaned = url_field.to_internal_value(text)
        except serializers.ValidationError:
            raise serializers.ValidationError({field_name: "Enter a valid document URL."})
        parsed = urlparse(cleaned)
        if parsed.scheme not in {"http", "https"} or "." not in parsed.netloc:
            raise serializers.ValidationError({field_name: "Enter a valid public document URL."})
        return cleaned

    def _validate_project_lots(self, value):
        if value in (None, "", []):
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError("Lots must be a list.")
        if len(value) > 20:
            raise serializers.ValidationError("Use up to 20 lots.")

        cleaned = []
        for index, item in enumerate(value, start=1):
            if not isinstance(item, dict):
                raise serializers.ValidationError(f"Lot {index} must be an object.")
            lot_title = self._clean_short_text(item.get("lot") or f"Lot {index}", max_length=80)
            objet = self._clean_short_text(item.get("objet"), max_length=240)
            quantite = self._clean_short_text(item.get("quantite"), max_length=80)
            region = self._clean_short_text(item.get("region"), max_length=120)
            caution = self._clean_short_text(item.get("caution"), max_length=120)
            has_any_value = any([lot_title, objet, quantite, region, caution])
            if not has_any_value:
                continue
            if not objet:
                raise serializers.ValidationError({f"lot_{index}": "Lot object is required."})
            if quantite:
                if not quantite.isdigit() or int(quantite) <= 0:
                    raise serializers.ValidationError({
                        f"lot_{index}_quantite": "Quantity must be a positive whole number."
                    })
            if caution and re.search(r"(^|[\s:])-\s*\d", caution):
                raise serializers.ValidationError({
                    f"lot_{index}_caution": "Provisional guarantee cannot be negative."
                })
            cleaned.append({
                "lot": lot_title,
                "objet": objet,
                "quantite": quantite,
                "region": region,
                "caution": caution,
            })
        return cleaned

    def _validate_project_documents(self, value):
        if value in (None, "", []):
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError("Documents must be a list.")
        if len(value) > 6:
            raise serializers.ValidationError("Use up to 6 document links.")

        cleaned = []
        seen = set()
        for index, item in enumerate(value, start=1):
            if not isinstance(item, dict):
                raise serializers.ValidationError(f"Document {index} must be an object.")
            raw_type = str(item.get("type") or "autres").strip()
            doc_type = raw_type if raw_type in self.PROJECT_DOCUMENT_TYPES else "autres"
            url = self._validate_document_url(item.get("url"), f"document_{index}_url")
            label = self._clean_short_text(item.get("label"), max_length=120)
            if not url:
                continue
            if url in seen:
                continue
            seen.add(url)
            cleaned.append({
                "type": doc_type,
                "url": url,
                "label": label or "Document",
            })
        return cleaned

    def _validate_project_details(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Project details must be an object.")

        errors = {}
        public_buyer = self._clean_short_text(value.get("public_buyer"), max_length=180)
        region_execution = self._clean_short_text(value.get("region_execution"), max_length=120)
        procedure = self._clean_short_text(value.get("procedure"), max_length=180)
        deadline_time = self._clean_short_text(value.get("deadline_time"), max_length=20)

        if not public_buyer:
            errors["public_buyer"] = "Public buyer is required."
        if not region_execution:
            errors["region_execution"] = "Execution region is required."
        if not procedure:
            errors["procedure"] = "Procedure is required."
        if not deadline_time:
            errors["deadline_time"] = "Deadline time is required."
        elif not re.match(r"^\d{2}:\d{2}$", deadline_time):
            errors["deadline_time"] = "Use HH:MM format."

        project_details = {
            "public_buyer": public_buyer,
            "region_execution": region_execution,
            "procedure": procedure,
            "deadline_time": deadline_time,
            "tender_number": self._clean_short_text(value.get("tender_number"), max_length=80),
            "number_of_lots": self._validate_positive_integer_text(value.get("number_of_lots"), "number_of_lots"),
            "lot_type": self._clean_short_text(value.get("lot_type"), max_length=120),
            "price_character": self._clean_short_text(value.get("price_character"), max_length=120),
            "delai_validite": self._validate_positive_integer_text(value.get("delai_validite"), "delai_validite"),
            "execution_start_date": str(value.get("execution_start_date") or "").strip(),
            "full_address": self._clean_short_text(value.get("full_address"), max_length=300),
            "opening_date": str(value.get("opening_date") or "").strip(),
            "opening_time": self._clean_short_text(value.get("opening_time"), max_length=20),
            "opening_address": self._clean_short_text(value.get("opening_address"), max_length=300),
            "evaluation_methodology": self._clean_short_text(value.get("evaluation_methodology"), max_length=180),
            "type_commande": self._clean_short_text(value.get("type_commande"), max_length=160),
            "financement": self._clean_short_text(value.get("financement"), max_length=160),
            "marche_cadre": bool(value.get("marche_cadre")),
            "marche_general": bool(value.get("marche_general")),
        }

        for field_name in ("execution_start_date", "opening_date"):
            if project_details[field_name]:
                date_field = serializers.DateField()
                try:
                    parsed_date = date_field.to_internal_value(project_details[field_name])
                except serializers.ValidationError:
                    errors[field_name] = "Enter a valid date."
                else:
                    if parsed_date < timezone.localdate():
                        errors[field_name] = "Date cannot be in the past."
                    else:
                        project_details[field_name] = parsed_date.isoformat()

        if (
            project_details.get("opening_date")
            and value.get("opening_date")
            and str(value.get("opening_date")) < str(self.initial_data.get("deadline") or "")
        ):
            errors["opening_date"] = "Opening date cannot be before the reception deadline."

        for field_name in ("opening_time",):
            if project_details[field_name] and not re.match(r"^\d{2}:\d{2}$", project_details[field_name]):
                errors[field_name] = "Use HH:MM format."

        try:
            project_details["lots"] = self._validate_project_lots(value.get("lots"))
        except serializers.ValidationError as exc:
            errors["lots"] = exc.detail
        try:
            project_details["documents"] = self._validate_project_documents(value.get("documents"))
        except serializers.ValidationError as exc:
            errors["documents"] = exc.detail

        if errors:
            raise serializers.ValidationError(errors)

        project_details["has_pdf"] = bool(project_details["documents"])
        project_details["pdf_url"] = next(
            (document["url"] for document in project_details["documents"] if document["type"] == "avis_appel_offres"),
            "",
        )
        project_details["cahier_des_charges_url"] = next(
            (document["url"] for document in project_details["documents"] if document["type"] == "cahier_des_charges"),
            "",
        )
        project_details["caution"] = next(
            (lot.get("caution", "") for lot in project_details["lots"] if lot.get("caution")),
            "",
        )
        return {key: value for key, value in project_details.items() if value not in ("", [], None)}

    def validate(self, attrs):
        opportunity_type = attrs.get("type")
        internship_details = attrs.get("internship_details")
        seasonal_details = attrs.get("seasonal_details")
        project_details = attrs.get("project_details")

        if opportunity_type == TypeOpportunite.STAGE:
            if seasonal_details or project_details:
                raise serializers.ValidationError({
                    "detail": "This opportunity type does not allow these extra details."
                })
            attrs["contract"] = "Internship"
            attrs["salary"] = ""
            attrs["experience_min"] = None
            attrs["experience_max"] = None
            if not internship_details:
                raise serializers.ValidationError({
                    "internship_details": "Internship details are required."
                })
            try:
                attrs["internship_details"] = self._validate_internship_details(internship_details)
            except serializers.ValidationError as exc:
                raise serializers.ValidationError({"internship_details": exc.detail})
        elif opportunity_type == TypeOpportunite.SAISONNIER:
            if internship_details or project_details:
                raise serializers.ValidationError({
                    "detail": "This opportunity type does not allow these extra details."
                })
            attrs["contract"] = "Seasonal"
            attrs["experience_min"] = None
            attrs["experience_max"] = None
            if not seasonal_details:
                raise serializers.ValidationError({
                    "seasonal_details": "Seasonal details are required."
                })
            try:
                attrs["seasonal_details"] = self._validate_seasonal_details(seasonal_details)
            except serializers.ValidationError as exc:
                raise serializers.ValidationError({"seasonal_details": exc.detail})
        elif opportunity_type == TypeOpportunite.PROJET:
            if internship_details or seasonal_details:
                raise serializers.ValidationError({
                    "detail": "This opportunity type does not allow these extra details."
                })
            attrs["contract"] = ""
            attrs["availability"] = ""
            attrs["education_level"] = ""
            attrs["salary"] = ""
            attrs["skills"] = []
            attrs["experience_min"] = None
            attrs["experience_max"] = None
            if not attrs.get("deadline"):
                raise serializers.ValidationError({"deadline": "Deadline is required for calls for tender."})
            if not project_details:
                raise serializers.ValidationError({"project_details": "Project details are required."})
            try:
                attrs["project_details"] = self._validate_project_details(project_details)
            except serializers.ValidationError as exc:
                raise serializers.ValidationError({"project_details": exc.detail})
        elif internship_details:
            raise serializers.ValidationError({
                "internship_details": "Internship details are only allowed for internship opportunities."
            })
        elif seasonal_details:
            raise serializers.ValidationError({
                "seasonal_details": "Seasonal details are only allowed for seasonal opportunities."
            })
        elif project_details:
            raise serializers.ValidationError({
                "project_details": "Project details are only allowed for calls for tender."
            })

        min_years = attrs.get("experience_min")
        max_years = attrs.get("experience_max")
        if min_years is not None and max_years is not None and min_years > max_years:
            raise serializers.ValidationError({
                "experience_max": "Maximum experience must be greater than or equal to minimum experience."
            })
        attrs.pop("turnstile_token", None)
        return attrs


class OrganizationTenderDocumentUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    type = serializers.CharField(required=False, allow_blank=True, max_length=80)
    label = serializers.CharField(required=False, allow_blank=True, max_length=120)

    def validate_file(self, value):
        extension = Path(value.name or "").suffix.lower()
        if extension not in OrganizationOpportunityWriteSerializer.ALLOWED_TENDER_DOCUMENT_EXTENSIONS:
            raise serializers.ValidationError("Use a PDF, DOCX, or DOC document.")
        if getattr(value, "size", 0) > OrganizationOpportunityWriteSerializer.MAX_TENDER_DOCUMENT_SIZE_BYTES:
            raise serializers.ValidationError("Document must be 5 MB or smaller.")
        content_type = getattr(value, "content_type", "")
        if (
            content_type
            and content_type not in OrganizationOpportunityWriteSerializer.ALLOWED_TENDER_DOCUMENT_CONTENT_TYPES
        ):
            raise serializers.ValidationError("Unsupported document file type.")
        return value

    def validate_type(self, value):
        text = str(value or "autres").strip()
        if text in OrganizationOpportunityWriteSerializer.PROJECT_DOCUMENT_TYPES:
            return text
        return "autres"

    def validate_label(self, value):
        return str(value or "").strip()
