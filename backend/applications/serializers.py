from pathlib import Path
from urllib.parse import unquote, urlparse

from django.conf import settings
from rest_framework import serializers

from opportunities.models import StatutOpportunite
from users.models import ProfileResume

from .models import Candidature, Document, StatutSuiviCandidature


MAX_COVER_LETTER_SIZE_BYTES = 5 * 1024 * 1024
ALLOWED_COVER_LETTER_EXTENSIONS = {".pdf", ".docx"}
ALLOWED_COVER_LETTER_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def _has_expected_file_signature(uploaded_file, extension):
    position = uploaded_file.tell() if hasattr(uploaded_file, "tell") else 0
    header = uploaded_file.read(8)
    if hasattr(uploaded_file, "seek"):
        uploaded_file.seek(position)

    if extension == ".pdf":
        return header.startswith(b"%PDF-")
    if extension == ".docx":
        return header.startswith(b"PK")
    return False


class InternalApplicationCreateSerializer(serializers.Serializer):
    cv_id = serializers.IntegerField(min_value=1)
    cover_letter_url = serializers.URLField(
        required=False,
        allow_blank=True,
        max_length=1000,
    )
    contact_email = serializers.EmailField()
    contact_phone = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=20,
    )

    def validate_cv_id(self, value):
        request = self.context["request"]
        profile = getattr(request.user, "profil", None)
        if profile is None:
            raise serializers.ValidationError("Complete your candidate profile before applying.")

        resume = ProfileResume.objects.filter(pk=value, profile=profile).first()
        if resume is None or not resume.file:
            raise serializers.ValidationError("Select a resume from your profile.")

        self.context["resume"] = resume
        return value

    def validate_cover_letter_url(self, value):
        value = str(value or "").strip()
        if not value:
            return value

        request = self.context["request"]
        parsed = urlparse(value)
        path = unquote(parsed.path or "")
        expected_path = f"/application_cover_letters/{request.user.pk}/"
        if expected_path not in path:
            raise serializers.ValidationError("Upload the cover letter from this application form.")

        if getattr(settings, "PROFILE_RESUME_USE_CLOUDINARY", False):
            cloud_name = str(getattr(settings, "CLOUDINARY_CLOUD_NAME", "") or "").strip()
            if parsed.scheme != "https" or parsed.netloc != "res.cloudinary.com":
                raise serializers.ValidationError("Invalid cover letter storage URL.")
            if cloud_name and f"/{cloud_name}/" not in path:
                raise serializers.ValidationError("Invalid cover letter storage URL.")

        extension = Path(path).suffix.lower()
        if extension not in ALLOWED_COVER_LETTER_EXTENSIONS:
            raise serializers.ValidationError("Use an uploaded PDF or DOCX cover letter.")
        return value

    def validate_contact_phone(self, value):
        phone = "".join(str(value or "").split())
        if phone and (not phone.startswith("+216") or len(phone) != 12 or not phone[1:].isdigit()):
            raise serializers.ValidationError("Enter a Tunisia phone number in the format +21612345678.")
        return phone


class CoverLetterUploadSerializer(serializers.Serializer):
    file = serializers.FileField()

    def validate_file(self, value):
        extension = Path(value.name or "").suffix.lower()
        if extension not in ALLOWED_COVER_LETTER_EXTENSIONS:
            raise serializers.ValidationError("Use a PDF or DOCX cover letter.")
        if getattr(value, "size", 0) > MAX_COVER_LETTER_SIZE_BYTES:
            raise serializers.ValidationError("Cover letter must be 5 MB or smaller.")

        content_type = str(getattr(value, "content_type", "") or "").lower()
        if content_type and content_type not in ALLOWED_COVER_LETTER_CONTENT_TYPES:
            raise serializers.ValidationError("Unsupported cover letter file type.")
        if not _has_expected_file_signature(value, extension):
            raise serializers.ValidationError("The cover letter content does not match its file type.")
        return value


class ExternalApplicationStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=[
            StatutSuiviCandidature.EXTERNAL_APPLIED_CONFIRMED,
            StatutSuiviCandidature.EXTERNAL_REMIND_LATER,
        ]
    )


class OrganizationApplicationRestoreSerializer(serializers.Serializer):
    restore_status = serializers.ChoiceField(
        choices=[
            StatutSuiviCandidature.SUBMITTED,
            StatutSuiviCandidature.VIEWED_BY_ORGANIZATION,
        ],
        required=False,
    )


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ["id", "type_document", "fichier", "date_upload"]


class CandidateApplicationListSerializer(serializers.ModelSerializer):
    opportunity_id = serializers.IntegerField(source="opportunite_id", read_only=True)
    opportunity_title = serializers.CharField(source="opportunite.titre", read_only=True)
    organisation_name = serializers.CharField(
        source="opportunite.organisation_nom",
        read_only=True,
    )
    ville = serializers.CharField(source="opportunite.ville", read_only=True)

    class Meta:
        model = Candidature
        fields = [
            "id",
            "opportunity_id",
            "opportunity_title",
            "organisation_name",
            "ville",
            "statut",
            "submitted_at",
            "cover_letter_url",
        ]


class OrganizationReceivedApplicationSerializer(serializers.ModelSerializer):
    candidate_name = serializers.SerializerMethodField()
    candidate_email = serializers.EmailField(source="candidat.email", read_only=True)
    cv_url = serializers.SerializerMethodField()

    class Meta:
        model = Candidature
        fields = [
            "id",
            "candidate_name",
            "candidate_email",
            "contact_phone",
            "statut",
            "submitted_at",
            "derniere_mise_a_jour",
            "cv_url",
            "cover_letter_url",
        ]

    def get_candidate_name(self, obj):
        profile = getattr(obj.candidat, "profil", None)
        if profile is not None:
            profile_name = f"{profile.prenom} {profile.nom}".strip()
            if profile_name:
                return profile_name

        account_name = f"{obj.candidat.first_name} {obj.candidat.last_name}".strip()
        return account_name or obj.candidat.email

    def get_cv_url(self, obj):
        if obj.cv is None or not obj.cv.file:
            return None

        url = obj.cv.file.url
        request = self.context.get("request")
        if request is not None and not url.startswith(("http://", "https://")):
            return request.build_absolute_uri(url)
        return url


class OrganizationAllApplicationsSerializer(serializers.ModelSerializer):
    candidate_name = serializers.SerializerMethodField()
    candidate_email = serializers.EmailField(source="candidat.email", read_only=True)
    cv_url = serializers.SerializerMethodField()
    opportunity_id = serializers.IntegerField(source="opportunite.id", read_only=True)
    opportunity_title = serializers.CharField(source="opportunite.titre", read_only=True)

    class Meta:
        model = Candidature
        fields = [
            "id",
            "candidate_name",
            "candidate_email",
            "contact_phone",
            "statut",
            "submitted_at",
            "derniere_mise_a_jour",
            "cv_url",
            "cover_letter_url",
            "opportunity_id",
            "opportunity_title",
        ]

    def get_candidate_name(self, obj):
        profile = getattr(obj.candidat, "profil", None)
        if profile is not None:
            profile_name = f"{profile.prenom} {profile.nom}".strip()
            if profile_name:
                return profile_name

        account_name = f"{obj.candidat.first_name} {obj.candidat.last_name}".strip()
        return account_name or obj.candidat.email

    def get_cv_url(self, obj):
        if obj.cv is None or not obj.cv.file:
            return None

        url = obj.cv.file.url
        request = self.context.get("request")
        if request is not None and not url.startswith(("http://", "https://")):
            return request.build_absolute_uri(url)
        return url


class OrganizationCandidateApplicationProfileSerializer(serializers.ModelSerializer):
    candidate_name = serializers.SerializerMethodField()
    candidate_email = serializers.EmailField(source="candidat.email", read_only=True)
    cv_url = serializers.SerializerMethodField()
    opportunity = serializers.SerializerMethodField()
    profile_visible = serializers.SerializerMethodField()
    profile = serializers.SerializerMethodField()

    class Meta:
        model = Candidature
        fields = [
            "id",
            "candidate_name",
            "candidate_email",
            "contact_phone",
            "statut",
            "submitted_at",
            "cv_url",
            "cover_letter_url",
            "opportunity",
            "profile_visible",
            "profile",
        ]

    def get_candidate_name(self, obj):
        profile = getattr(obj.candidat, "profil", None)
        if profile is not None:
            profile_name = f"{profile.prenom} {profile.nom}".strip()
            if profile_name:
                return profile_name

        account_name = f"{obj.candidat.first_name} {obj.candidat.last_name}".strip()
        return account_name or obj.candidat.email

    def get_cv_url(self, obj):
        if obj.cv is None or not obj.cv.file:
            return None

        url = obj.cv.file.url
        request = self.context.get("request")
        if request is not None and not url.startswith(("http://", "https://")):
            return request.build_absolute_uri(url)
        return url

    def get_opportunity(self, obj):
        opportunity = obj.opportunite
        return {
            "id": opportunity.pk,
            "title": opportunity.titre,
            "location": opportunity.ville,
            "type": opportunity.type_opportunite,
            "status": opportunity.statut,
        }

    def get_profile_visible(self, obj):
        profile = getattr(obj.candidat, "profil", None)
        return bool(getattr(profile, "profile_visibility", False))

    def get_profile(self, obj):
        profile = getattr(obj.candidat, "profil", None)
        if profile is None or not profile.profile_visibility:
            return None

        active_resume = obj.cv
        extracted_skills = []
        resume_summary = ""
        if active_resume is not None:
            extracted_skills = list(getattr(active_resume, "extracted_skills", []) or [])
            resume_summary = str(
                getattr(active_resume, "resume_text_embedding_source", "")
                or getattr(active_resume, "parsed_text", "")
                or ""
            ).strip()
            if len(resume_summary) > 1200:
                resume_summary = f"{resume_summary[:1200].rstrip()}..."

        return {
            "first_name": profile.prenom,
            "last_name": profile.nom,
            "full_name": self.get_candidate_name(obj),
            "headline": ", ".join(profile.target_roles[:2]) if profile.target_roles else "",
            "summary": resume_summary,
            "skills": profile.competences or extracted_skills,
            "resume_skills": extracted_skills,
            "interests": profile.domaines_interet,
            "target_roles": profile.target_roles,
            "preferred_locations": profile.preferred_locations,
            "work_mode_preferences": profile.work_mode_preferences,
            "employment_types": profile.employment_types,
            "experience_level": profile.niveau_experience,
            "years_experience": profile.annees_experience,
            "compensation": {
                "min": profile.compensation_min_expectation,
                "max": profile.compensation_max_expectation,
                "currency": profile.compensation_currency,
                "period": profile.compensation_period,
            },
        }


class CandidatureSerializer(serializers.ModelSerializer):
    documents = DocumentSerializer(many=True, read_only=True)

    class Meta:
        model = Candidature
        fields = [
            "id",
            "candidat",
            "opportunite",
            "statut",
            "url_source",
            "cv",
            "cover_letter_url",
            "contact_email",
            "contact_phone",
            "submitted_at",
            "date_creation",
            "derniere_mise_a_jour",
            "documents",
        ]
        read_only_fields = [
            "candidat",
            "submitted_at",
            "date_creation",
            "derniere_mise_a_jour",
        ]

    def validate_opportunite(self, value):
        if value.statut != StatutOpportunite.ACTIVE:
            raise serializers.ValidationError("Applications are closed for this opportunity.")
        return value

    def validate(self, attrs):
        request = self.context.get("request")
        candidate = getattr(request, "user", None)
        opportunity = attrs.get("opportunite") or getattr(self.instance, "opportunite", None)
        if (
            self.instance is None
            and getattr(candidate, "is_authenticated", False)
            and opportunity is not None
            and Candidature.objects.filter(
                candidat=candidate,
                opportunite=opportunity,
            ).exists()
        ):
            raise serializers.ValidationError(
                {"detail": "You already track or applied to this opportunity."}
            )
        return attrs
