import re
import secrets
from pathlib import Path

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.hashers import make_password, check_password
from django.core.exceptions import ValidationError
from django.utils import timezone

from opportunities.utils.images import is_valid_image_url

from .storage import ProfileResumeStorage


class Utilisateur(AbstractUser):
    """
    Classe utilisateur personnalisée.
    Hérite du système d'authentification Django.
    """

    class AccountType(models.TextChoices):
        CANDIDATE = "candidate", "Candidate"
        ORGANIZATION = "organization", "Organization"

    account_type = models.CharField(
        max_length=20,
        choices=AccountType.choices,
        default=AccountType.CANDIDATE,
        db_index=True,
        help_text="BidWise account type. Existing auth flows default to candidate.",
    )
    is_admin = models.BooleanField(
        default=False,
        help_text="Can access BidWise admin backoffice APIs.",
    )
    is_suspended = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Account suspended by admin moderation.",
    )
    suspension_reason = models.CharField(
        max_length=20,
        choices=[
            ("spam", "Spam"),
            ("abuse", "Abuse"),
            ("fraud", "Fraud"),
            ("other", "Other"),
        ],
        blank=True,
        default="",
        help_text="Reason for suspension.",
    )
    suspended_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when user was suspended.",
    )

    def __str__(self):
        return self.username


class Profil(models.Model):
    utilisateur = models.OneToOneField(
        Utilisateur,
        on_delete=models.CASCADE,
        related_name="profil"
    )
    nom = models.CharField(max_length=100, blank=True)
    prenom = models.CharField(max_length=100, blank=True)
    competences = models.JSONField(
        default=list,
        blank=True,
        help_text="Structured list of profile skills used for ML features"
    )
    raw_skills = models.JSONField(
        default=list,
        blank=True,
        help_text="User-entered skill strings preserved for recommendation features.",
    )
    normalized_skills = models.JSONField(
        default=list,
        blank=True,
        help_text="Reserved structured skill metadata. Kept empty by the current JobBERT/LLM pipeline.",
    )
    skills_normalization_hash = models.CharField(max_length=64, blank=True, default="")
    skills_normalization_updated_at = models.DateTimeField(null=True, blank=True)
    skills_normalization_error = models.TextField(blank=True, default="")
    domaines_interet = models.JSONField(
        default=list,
        blank=True,
        help_text="Structured list of interest domains used for recommendations"
    )
    embedding = models.JSONField(
        null=True,
        blank=True,
        help_text="Cached user embedding generated from normalized profile features"
    )
    embedding_features_hash = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text="Hash of the normalized profile features used for the cached embedding"
    )
    last_embedding_update = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time the cached profile embedding was generated"
    )
    embedding_model = models.CharField(
        max_length=160,
        blank=True,
        default="",
        help_text="Embedding model identifier used for the cached profile vector"
    )
    embedding_dimensions = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Dimension count of the cached profile embedding vector"
    )
    embedding_updated_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time the versioned profile embedding metadata was updated"
    )
    embedding_content_hash = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text="Deterministic hash of semantic profile content used for embeddings"
    )
    jobbert_embedding = models.JSONField(null=True, blank=True)
    jobbert_embedding_model = models.CharField(max_length=200, blank=True, default="")
    jobbert_embedding_content_hash = models.CharField(max_length=64, blank=True, default="")
    jobbert_embedding_updated_at = models.DateTimeField(null=True, blank=True)

    class NiveauExperience(models.TextChoices):
        DEBUTANT = 'DEBUTANT', 'Débutant (0–1 an)'
        JUNIOR = 'JUNIOR', 'Junior (1–3 ans)'
        CONFIRME = 'CONFIRME', 'Confirmé (3–5 ans)'
        SENIOR = 'SENIOR', 'Senior (5+ ans)'

    niveau_experience = models.CharField(
        max_length=20,
        choices=NiveauExperience.choices,
        blank=True,
        help_text="Niveau d'expérience pour le matching automatique"
    )
    
    annees_experience = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Nombre d'années d'expérience (si applicable)"
    )

    # ── Onboarding: Opportunity Intent (Step 0) ────────────
    opportunity_types = models.JSONField(
        default=list, blank=True,
        help_text="Target opportunity types, e.g. ['JOB','INTERNSHIP']"
    )

    # ── Onboarding: Location & Remote (Step 1) ─────────────
    tender_preferences = models.JSONField(
        default=dict,
        blank=True,
        help_text="Calls-for-tender preferences: categories and optional max budget."
    )

    preferred_locations = models.JSONField(
        default=list, blank=True,
        help_text="Preferred Tunisian cities/regions and custom locations"
    )
    remote_preference = models.CharField(
        max_length=10,
        choices=[('ON_SITE', 'On-site'), ('REMOTE', 'Remote'), ('HYBRID', 'Hybrid')],
        null=True, blank=True,
        help_text="Legacy single remote work preference"
    )
    work_mode_preferences = models.JSONField(
        default=list, blank=True,
        help_text="Canonical desired work modes, e.g. ['REMOTE','HYBRID']"
    )

    # ── Onboarding: Salary (Step 2) ────────────────────────
    compensation_expectation = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Expected compensation amount"
    )
    compensation_min_expectation = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Minimum expected compensation amount"
    )
    compensation_max_expectation = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Maximum expected compensation amount"
    )
    compensation_currency = models.CharField(
        max_length=3,
        default="TND",
        blank=True,
        help_text="ISO currency code for expected compensation"
    )
    compensation_period = models.CharField(
        max_length=10,
        choices=[
            ('MONTHLY', 'Monthly'),
            ('YEARLY', 'Yearly'),
            ('DAILY', 'Daily'),
            ('HOURLY', 'Hourly'),
        ],
        null=True, blank=True,
        help_text="Compensation period"
    )

    # ── Onboarding: Employment Type (Step 3) ───────────────
    employment_types = models.JSONField(
        default=list, blank=True,
        help_text="Canonical desired contract/employment types"
    )

    # ── Onboarding: Target Roles (Step 4) ──────────────────
    target_roles = models.JSONField(
        default=list, blank=True,
        help_text="Target job titles/roles, e.g. ['Backend Developer','Data Engineer']"
    )

    # ── Onboarding: Visibility (Step 5) ────────────────────
    profile_visibility = models.BooleanField(
        default=True,
        help_text="Whether profile is discoverable by recruiters"
    )

    # ── Onboarding tracking ────────────────────────────────
    onboarding_completed = models.BooleanField(
        default=False,
        help_text="True after user completes onboarding wizard"
    )
    last_onboarding_step = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text="Last completed onboarding step (0-5)"
    )

    def __str__(self):
        return f"{self.prenom} {self.nom}" if self.prenom and self.nom else f"Profil #{self.id}"


def _normalize_required_text(value):
    return re.sub(r"\s+", " ", (value or "").strip())


class OrganizationProfile(models.Model):
    class OrganizationType(models.TextChoices):
        COMPANY = "company", "Company"
        STARTUP = "startup", "Startup"
        PUBLIC = "public", "Public"
        NGO = "ngo", "NGO"
        OTHER = "other", "Other"

    user = models.OneToOneField(
        Utilisateur,
        on_delete=models.CASCADE,
        related_name="organization_profile",
    )
    organization_name = models.CharField(max_length=180)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    website = models.URLField(max_length=255, blank=True, default="")
    logo = models.URLField(max_length=1000, blank=True, default="")
    phone = models.CharField(max_length=16)
    organization_type = models.CharField(
        max_length=20,
        choices=OrganizationType.choices,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["organization_type"], name="org_profile_type_idx"),
            models.Index(fields=["created_at"], name="org_profile_created_idx"),
        ]

    def __str__(self):
        return self.organization_name or f"OrganizationProfile #{self.id}"

    def _normalize_fields(self):
        self.organization_name = _normalize_required_text(self.organization_name)
        self.first_name = _normalize_required_text(self.first_name)
        self.last_name = _normalize_required_text(self.last_name)
        self.website = (self.website or "").strip()
        self.logo = (self.logo or "").strip()
        self.phone = re.sub(r"\s+", "", (self.phone or "").strip())
        self.organization_type = (self.organization_type or "").strip()

    def clean_fields(self, exclude=None):
        self._normalize_fields()
        super().clean_fields(exclude=exclude)

    def clean(self):
        self._normalize_fields()
        errors = {}

        if self.user_id and self.user.account_type != Utilisateur.AccountType.ORGANIZATION:
            errors["user"] = "Organization profiles can only belong to organization accounts."

        if not re.fullmatch(r"\+216\d{8}", self.phone or ""):
            errors["phone"] = "Enter a Tunisia phone number in the format +21612345678."

        if self.logo and not is_valid_image_url(self.logo):
            errors["logo"] = "Enter a valid public image URL."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


def profile_resume_upload_to(instance, filename):
    extension = Path(filename or "").suffix.lower()
    if extension not in {".pdf", ".docx", ".doc", ".rtf", ".txt"}:
        extension = ".bin"
    return f"profile_resumes/{instance.profile_id}/{secrets.token_hex(16)}{extension}"


class ProfileResume(models.Model):
    class SourceType(models.TextChoices):
        UPLOAD = "UPLOAD", "Upload"
        BUILDER = "BUILDER", "BidWise Builder"

    class ParsingStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PROCESSING = "PROCESSING", "Processing"
        SUCCEEDED = "SUCCEEDED", "Succeeded"
        EMPTY = "EMPTY", "Empty"
        FAILED = "FAILED", "Failed"
        UNSUPPORTED = "UNSUPPORTED", "Unsupported"

    profile = models.ForeignKey(
        Profil,
        on_delete=models.CASCADE,
        related_name="resumes",
    )
    file = models.FileField(
        upload_to=profile_resume_upload_to,
        storage=ProfileResumeStorage(),
        null=True,
        blank=True,
    )
    uploaded_at = models.DateTimeField(auto_now_add=True, db_index=True)
    parsed_text = models.TextField(blank=True, default="")
    parsing_status = models.CharField(
        max_length=20,
        choices=ParsingStatus.choices,
        default=ParsingStatus.PENDING,
        db_index=True,
        help_text="Asynchronous resume parsing lifecycle status",
    )
    parsing_error = models.TextField(
        blank=True,
        default="",
        help_text="Safe user-neutral parsing error detail for operators",
    )
    parsed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when resume parsing last completed",
    )
    resume_text_embedding_source = models.TextField(
        blank=True,
        default="",
        help_text="Clean deterministic resume text source prepared for future embeddings"
    )
    extracted_skills = models.JSONField(
        blank=True,
        default=list,
        help_text="Canonical semantic skills extracted from the resume. Does not overwrite user-entered skills.",
    )
    extracted_raw_skills = models.JSONField(
        blank=True,
        default=list,
        help_text="Raw semantic skill mentions extracted from the resume.",
    )
    extracted_normalized_skills = models.JSONField(
        blank=True,
        default=list,
        help_text="Reserved structured skill metadata. Kept empty by the current Qwen extraction pipeline.",
    )
    extracted_skills_normalization_hash = models.CharField(max_length=64, blank=True, default="")
    extracted_skills_normalization_updated_at = models.DateTimeField(null=True, blank=True)
    extracted_skills_normalization_error = models.TextField(blank=True, default="")
    extracted_domains = models.JSONField(
        blank=True,
        default=list,
        help_text="Canonical semantic domains inferred from the resume.",
    )
    extracted_tools = models.JSONField(
        blank=True,
        default=list,
        help_text="Canonical tools and platforms extracted from the resume.",
    )
    extracted_languages = models.JSONField(
        blank=True,
        default=list,
        help_text="Languages detected in the parsed resume text.",
    )
    semantic_resume_version = models.CharField(
        max_length=32,
        blank=True,
        default="",
        help_text="Version of the semantic resume enrichment pipeline.",
    )
    semantic_resume_content_hash = models.CharField(
        max_length=64,
        blank=True,
        default="",
        db_index=True,
        help_text="Content hash used to skip repeated semantic CV inference.",
    )
    semantic_resume_updated_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time semantic resume enrichment completed.",
    )
    semantic_resume_confidence = models.FloatField(
        default=0.0,
        help_text="Confidence score for extracted semantic resume signals.",
    )
    semantic_resume_status = models.CharField(
        max_length=20,
        blank=True,
        default="PENDING",
        db_index=True,
        help_text="Lifecycle status for semantic resume enrichment.",
    )
    semantic_resume_error = models.TextField(
        blank=True,
        default="",
        help_text="Safe operator-facing semantic enrichment error.",
    )
    semantic_resume_metadata = models.JSONField(
        blank=True,
        default=dict,
        help_text="Diagnostic metadata for semantic resume enrichment.",
    )
    source_type = models.CharField(
        max_length=16,
        choices=SourceType.choices,
        default=SourceType.UPLOAD,
        db_index=True,
    )
    metadata = models.JSONField(blank=True, default=dict)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["-uploaded_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["profile"],
                condition=models.Q(is_active=True),
                name="uniq_active_resume_per_profile",
            ),
        ]
        indexes = [
            models.Index(fields=["profile", "is_active", "-uploaded_at"], name="profile_resume_active_idx"),
        ]

    def __str__(self):
        return f"ProfileResume<{self.profile_id}:{self.source_type}:{self.is_active}>"


class OTPChallenge(models.Model):
    """
    Passwordless OTP for CANDIDAT authentication.

    Security properties:
    - OTP stored as PBKDF2 hash (never plaintext).
    - 5-minute expiry, 5-attempt limit.
    - One-time use (is_used flag).
    - Old OTPs for same email are purged on every new request.
    """

    OTP_LENGTH = 6
    OTP_EXPIRY_MINUTES = 5
    MAX_ATTEMPTS = 5
    COOLDOWN_SECONDS = 60  # Min delay between OTP requests for same email

    email = models.EmailField(db_index=True)
    otp_hash = models.CharField(max_length=128)
    attempts = models.PositiveSmallIntegerField(default=0)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email', 'is_used', 'expires_at']),
        ]

    def __str__(self):
        return f"OTP for {self.email} (expires {self.expires_at})"

    # ── Factory ────────────────────────────────────────────

    @classmethod
    def create_for_email(cls, email: str) -> tuple['OTPChallenge', str]:
        """
        Generate a new OTP challenge.
        Returns (challenge_instance, plaintext_otp).
        Caller is responsible for purging old challenges beforehand.
        """
        plaintext = str(secrets.randbelow(10 ** cls.OTP_LENGTH)).zfill(cls.OTP_LENGTH)
        challenge = cls.objects.create(
            email=email,
            otp_hash=make_password(plaintext),
            expires_at=timezone.now() + timezone.timedelta(minutes=cls.OTP_EXPIRY_MINUTES),
        )
        return challenge, plaintext

    # ── Instance helpers ───────────────────────────────────

    @property
    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at

    @property
    def is_locked(self) -> bool:
        return self.attempts >= self.MAX_ATTEMPTS

    def verify(self, plaintext_otp: str) -> bool:
        """
        Check the submitted OTP against the stored hash.
        Increments attempts on failure; marks used on success.
        Returns True only on valid match.
        """
        if self.is_expired or self.is_used or self.is_locked:
            return False

        if check_password(plaintext_otp, self.otp_hash):
            self.is_used = True
            self.save(update_fields=['is_used'])
            return True

        self.attempts += 1
        self.save(update_fields=['attempts'])
        return False

    # ── Cleanup ────────────────────────────────────────────

    @classmethod
    def purge_expired(cls):
        """Delete all expired or used challenges."""
        cls.objects.filter(
            models.Q(expires_at__lt=timezone.now()) | models.Q(is_used=True)
        ).delete()

    @classmethod
    def purge_for_email(cls, email: str):
        """Invalidate all existing challenges for an email."""
        cls.objects.filter(email=email).delete()

    @classmethod
    def is_on_cooldown(cls, email: str) -> bool:
        """
        True only if a recent, unused, non-expired OTP exists.
        Once the user verifies an OTP (e.g. logs in on one device),
        they can immediately request a new one for another device.
        """
        cutoff = timezone.now() - timezone.timedelta(seconds=cls.COOLDOWN_SECONDS)
        return cls.objects.filter(
            email=email,
            created_at__gte=cutoff,
            is_used=False,
            expires_at__gt=timezone.now(),
        ).exists()


class LoginEvent(models.Model):
    """Records every successful login."""
    user = models.ForeignKey(
        Utilisateur,
        on_delete=models.CASCADE,
        related_name='login_events',
    )
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True, default='')
    device_type = models.CharField(max_length=50, blank=True, default='')
    location = models.CharField(max_length=255, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f"LoginEvent({self.user.email}, {self.ip_address}, {self.created_at})"

    @classmethod
    def record(cls, user, request):
        """Create a LoginEvent from the current request."""
        ip = cls._get_client_ip(request)
        ua = request.META.get('HTTP_USER_AGENT', '')
        device = cls._parse_device_type(ua)

        return cls.objects.create(
            user=user,
            ip_address=ip,
            user_agent=ua,
            device_type=device,
        )

    @staticmethod
    def _get_client_ip(request) -> str:
        forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if forwarded:
            return forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '0.0.0.0')

    @staticmethod
    def _parse_device_type(user_agent: str) -> str:
        ua_lower = user_agent.lower()
        if 'mobile' in ua_lower or 'android' in ua_lower or 'iphone' in ua_lower:
            return 'Mobile'
        if 'tablet' in ua_lower or 'ipad' in ua_lower:
            return 'Tablet'
        return 'Desktop'


class AuditLog(models.Model):
    """
    Traçabilité MVP des actions admin sensibles sur les comptes utilisateurs.
    Append-only : aucun UPDATE ni DELETE autorisé.
    """
 
    # ── Actions disponibles ─────────────────────────────────────────────────
    class Action(models.TextChoices):
        SUSPEND       = "SUSPEND",    "Suspend user"
        REACTIVATE    = "REACTIVATE", "Reactivate user"
        TOGGLE_ADMIN  = "TOGGLE_ADMIN","Toggle admin privilege"
        TOGGLE_ACTIVE = "TOGGLE_ACTIVE","Toggle active status"
        APPROVE_ORG_OPPORTUNITY = "APPROVE_ORG_OPPORTUNITY", "Approve organization opportunity"
        REJECT_ORG_OPPORTUNITY = "REJECT_ORG_OPPORTUNITY", "Reject organization opportunity"
        UPDATE_ORG_OPPORTUNITY = "UPDATE_ORG_OPPORTUNITY", "Update organization opportunity"
        SUSPEND_ORG_OPPORTUNITY = "SUSPEND_ORG_OPPORTUNITY", "Suspend organization opportunity"
        ACTIVATE_ORG_OPPORTUNITY = "ACTIVATE_ORG_OPPORTUNITY", "Activate organization opportunity"
        CLOSE_ORG_OPPORTUNITY = "CLOSE_ORG_OPPORTUNITY", "Close organization opportunity"
 
    # ── Champs ──────────────────────────────────────────────────────────────
    actor = models.ForeignKey(
        "Utilisateur",
        on_delete=models.SET_NULL,
        null=True,
        related_name="audit_actions",
        help_text="Admin who performed the action.",
    )
    target = models.ForeignKey(
        "Utilisateur",
        on_delete=models.SET_NULL,
        null=True,
        related_name="audit_events",
        help_text="User affected by the action.",
    )
    action = models.CharField(
        max_length=30,
        choices=Action.choices,
        db_index=True,
        help_text="Type of admin action performed.",
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Lightweight context: reason, detail, before/after values. "
            "Keep flat and minimal — not a general-purpose log store."
        ),
    )
    created_at = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        editable=False,
    )
 
    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["actor", "-created_at"]),
            models.Index(fields=["target", "-created_at"]),
        ]
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"
 
    def __str__(self):
        actor_email = self.actor.email if self.actor else "unknown"
        target_email = self.target.email if self.target else "unknown"
        return f"[{self.action}] {actor_email} → {target_email} @ {self.created_at:%Y-%m-%d %H:%M}"
 
    # ── Append-only enforcement ─────────────────────────────────────────────
    def save(self, *args, **kwargs):
        if self.pk is not None:
            # Silently refuse updates — log entries are immutable
            return
        super().save(*args, **kwargs)
 
    def delete(self, *args, **kwargs):
        # Refuse deletion at model level
        raise NotImplementedError("AuditLog entries are immutable and cannot be deleted.")
