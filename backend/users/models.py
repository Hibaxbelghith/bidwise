import logging
import re
import secrets
from pathlib import Path

import requests
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.hashers import make_password, check_password
from django.core.exceptions import ValidationError
from django.utils import timezone

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
    """
    Records every successful login.
    Used to detect suspicious logins from new devices or IP addresses.
    """
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
    def is_suspicious(cls, user, ip_address: str, user_agent: str) -> bool:
        """
        Return True if this IP or user-agent has never been seen before
        for this user (i.e. it's a new device or new location).
        """
        past_events = cls.objects.filter(user=user)
        if not past_events.exists():
            # Very first login — not suspicious
            return False
        known_ip = past_events.filter(ip_address=ip_address).exists()
        known_ua = past_events.filter(user_agent=user_agent).exists()
        return not known_ip or not known_ua

    @classmethod
    def record(cls, user, request):
        """
        Create a LoginEvent from the current request and send a
        suspicious-login email if the device/IP is new.
        """
        ip = cls._get_client_ip(request)
        ua = request.META.get('HTTP_USER_AGENT', '')
        device = cls._parse_device_type(ua)

        suspicious = cls.is_suspicious(user, ip, ua)

        event = cls.objects.create(
            user=user,
            ip_address=ip,
            user_agent=ua,
            device_type=device,
        )

        if suspicious:
            cls._send_suspicious_email(user, event)

        return event

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

    @staticmethod
    def _get_ip_location(ip_address: str) -> str:
        """Resolve IP to a human-readable location using ip-api.com (free)."""
        try:
            resp = requests.get(
                f'http://ip-api.com/json/{ip_address}',
                params={'fields': 'status,city,regionName,country'},
                timeout=3,
            )
            data = resp.json()
            if data.get('status') == 'success':
                parts = [p for p in [data.get('city'), data.get('regionName'), data.get('country')] if p]
                return ', '.join(parts) if parts else 'Unknown'
        except Exception:
            logging.getLogger(__name__).debug('IP geolocation failed for %s', ip_address)
        return 'Unknown'

    @staticmethod
    def _send_suspicious_email(user, event):
        from django.core.mail import EmailMultiAlternatives
        from django.conf import settings

        display_name = user.first_name or user.email
        time_str = event.created_at.strftime('%B %d, %Y at %I:%M %p UTC')
        location = LoginEvent._get_ip_location(event.ip_address)

        location_text = f"  Location:    {location}\n" if location != 'Unknown' else ""
        text_content = (
            f"Hi {display_name},\n\n"
            f"We detected a new sign-in to your BidWise account from "
            f"a device or location we don't recognize.\n\n"
            f"  Device:      {event.device_type}\n"
            f"  IP Address:  {event.ip_address}\n"
            f"{location_text}"
            f"  Date & Time: {time_str}\n\n"
            f"If this was you, no action is needed.\n\n"
            f"If you did NOT sign in, we recommend you:\n"
            f"  1. Log out of all sessions immediately\n"
            f"  2. Contact our support team at support@bidwise.com\n\n"
            f"Stay safe,\n"
            f"The BidWise Security Team"
        )

        location_row = ""
        if location != 'Unknown':
            location_row = f"""
                    <tr>
                        <td style="padding: 12px 16px; color: #6b7280; font-size: 14px; border-bottom: 1px solid #e5e7eb;">&#x1f4cd; Location</td>
                        <td style="padding: 12px 16px; color: #111827; font-size: 14px; font-weight: 600; border-bottom: 1px solid #e5e7eb;">{location}</td>
                    </tr>"""

        html_content = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 0;">
            <div style="background-color: #1e40af; padding: 24px 32px; border-radius: 8px 8px 0 0;">
                <h1 style="color: #ffffff; font-size: 20px; margin: 0;">&#x1f6e1;&#xfe0f; Security Alert</h1>
            </div>
            <div style="background-color: #ffffff; padding: 32px; border: 1px solid #e5e7eb; border-top: none;">
                <p style="color: #111827; font-size: 16px; margin-top: 0;">
                    Hi <strong>{display_name}</strong>,
                </p>
                <p style="color: #374151; font-size: 15px; line-height: 1.6;">
                    We detected a new sign-in to your BidWise account from a device
                    or location we don&rsquo;t recognize.
                </p>
                <table style="width: 100%; border-collapse: collapse; margin: 24px 0; background-color: #f9fafb; border-radius: 8px;">
                    <tr>
                        <td style="padding: 12px 16px; color: #6b7280; font-size: 14px; border-bottom: 1px solid #e5e7eb;">Device</td>
                        <td style="padding: 12px 16px; color: #111827; font-size: 14px; font-weight: 600; border-bottom: 1px solid #e5e7eb;">{event.device_type}</td>
                    </tr>
                    <tr>
                        <td style="padding: 12px 16px; color: #6b7280; font-size: 14px; border-bottom: 1px solid #e5e7eb;">IP Address</td>
                        <td style="padding: 12px 16px; color: #111827; font-size: 14px; font-weight: 600; border-bottom: 1px solid #e5e7eb;">{event.ip_address}</td>
                    </tr>{location_row}
                    <tr>
                        <td style="padding: 12px 16px; color: #6b7280; font-size: 14px;">Date &amp; Time</td>
                        <td style="padding: 12px 16px; color: #111827; font-size: 14px; font-weight: 600;">{time_str}</td>
                    </tr>
                </table>
                <p style="color: #374151; font-size: 15px; line-height: 1.6;">
                    If this was you, no action is needed.
                </p>
                <div style="background-color: #fef2f2; border-left: 4px solid #dc2626; padding: 16px; border-radius: 4px; margin: 24px 0;">
                    <p style="color: #991b1b; font-size: 14px; margin: 0; font-weight: 600;">
                        If you did NOT sign in:
                    </p>
                    <ol style="color: #991b1b; font-size: 14px; margin: 8px 0 0 0; padding-left: 20px;">
                        <li>Log out of all sessions immediately</li>
                        <li>Contact our support team at <a href="mailto:support@bidwise.com" style="color: #1e40af;">support@bidwise.com</a></li>
                    </ol>
                </div>
            </div>
            <div style="background-color: #f9fafb; padding: 16px 32px; border: 1px solid #e5e7eb; border-top: none; border-radius: 0 0 8px 8px; text-align: center;">
                <p style="color: #9ca3af; font-size: 12px; margin: 0;">
                    &copy; BidWise &mdash; This is an automated security notification.
                </p>
            </div>
        </div>
        """

        msg = EmailMultiAlternatives(
            subject='\U0001f6a8 New login detected on your BidWise account',
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send(fail_silently=True)
