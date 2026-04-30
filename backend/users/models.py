import logging
import secrets

import requests
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone


class Utilisateur(AbstractUser):
    """
    Classe utilisateur personnalisée.
    Hérite du système d'authentification Django.
    """

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
