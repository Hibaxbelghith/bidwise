import secrets

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone


class Utilisateur(AbstractUser):
    """
    Classe utilisateur personnalisée.
    Hérite du système d'authentification Django.
    """

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
    competences = models.TextField(
        blank=True,
        help_text="Liste des compétences séparées par des virgules"
    )
    domaines_interet = models.TextField(
        blank=True,
        help_text="Domaines d'intérêt (ex: web, IA, finance)"
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
    preferred_location = models.CharField(
        max_length=255, null=True, blank=True,
        help_text="Preferred city/region, free text"
    )
    remote_preference = models.CharField(
        max_length=10,
        choices=[('ON_SITE', 'On-site'), ('REMOTE', 'Remote'), ('HYBRID', 'Hybrid')],
        null=True, blank=True,
        help_text="Remote work preference"
    )

    # ── Onboarding: Salary (Step 2) ────────────────────────
    compensation_expectation = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Expected compensation amount"
    )
    compensation_period = models.CharField(
        max_length=10,
        choices=[('HOURLY', 'Hourly'), ('MONTHLY', 'Monthly'), ('YEARLY', 'Yearly')],
        null=True, blank=True,
        help_text="Compensation period"
    )

    # ── Onboarding: Employment Type (Step 3) ───────────────
    employment_types = models.JSONField(
        default=list, blank=True,
        help_text="Desired employment types, e.g. ['FULL_TIME','CONTRACT']"
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
        """True if a fresh OTP was created within the cooldown window."""
        cutoff = timezone.now() - timezone.timedelta(seconds=cls.COOLDOWN_SECONDS)
        return cls.objects.filter(email=email, created_at__gte=cutoff, is_used=False).exists()
