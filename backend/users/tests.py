"""
Comprehensive tests for the users app — Sprint 1.

Covers:
  - Models: Utilisateur, Profil (auto-creation signal), OTPChallenge
  - Serializers: all user/profile/OTP serializers
  - Views: profile_detail, request_otp, verify_otp, google_authenticate
  - Permissions: IsOwnerProfile
"""

from datetime import timedelta
from unittest.mock import patch, MagicMock

from django.core.cache import cache
from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone
from django.contrib.auth.hashers import check_password

from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from .models import Utilisateur, Profil, OTPChallenge
from .serializers import (
    UtilisateurSerializer,
    ProfilSerializer,
    ProfilUpdateSerializer,
    OTPRequestSerializer,
    OTPVerifySerializer,
)
from .permissions import IsOwnerProfile


# ═══════════════════════════════════════════════════════════
# MODEL TESTS
# ═══════════════════════════════════════════════════════════


class UtilisateurModelTests(TestCase):
    """Tests for the custom Utilisateur user model."""

    def test_create_user(self):
        user = Utilisateur.objects.create_user(
            username="testuser", email="test@example.com", password="securepass123"
        )
        self.assertEqual(user.username, "testuser")
        self.assertEqual(user.email, "test@example.com")
        self.assertTrue(user.check_password("securepass123"))
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)

    def test_create_superuser(self):
        admin = Utilisateur.objects.create_superuser(
            username="admin", email="admin@example.com", password="adminpass123"
        )
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)

    def test_str_returns_username(self):
        user = Utilisateur.objects.create_user(username="alice", password="pass1234")
        self.assertEqual(str(user), "alice")


class ProfilAutoCreationSignalTests(TestCase):
    """Tests that the post_save signal auto-creates a Profil."""

    def test_profil_created_on_user_creation(self):
        user = Utilisateur.objects.create_user(username="bob", password="pass1234")
        self.assertTrue(hasattr(user, "profil"))
        self.assertIsInstance(user.profil, Profil)

    def test_profil_not_duplicated_on_user_save(self):
        user = Utilisateur.objects.create_user(username="carol", password="pass1234")
        user.first_name = "Carol"
        user.save()
        self.assertEqual(Profil.objects.filter(utilisateur=user).count(), 1)


class ProfilModelTests(TestCase):
    """Tests for the Profil model fields and choices."""

    def setUp(self):
        self.user = Utilisateur.objects.create_user(username="dave", password="pass1234")
        self.profil = self.user.profil

    def test_default_values(self):
        self.assertEqual(self.profil.nom, "")
        self.assertEqual(self.profil.prenom, "")
        self.assertEqual(self.profil.competences, "")
        self.assertEqual(self.profil.domaines_interet, "")
        self.assertEqual(self.profil.niveau_experience, "")
        self.assertIsNone(self.profil.annees_experience)
        self.assertEqual(self.profil.opportunity_types, [])
        self.assertIsNone(self.profil.preferred_location)
        self.assertIsNone(self.profil.remote_preference)
        self.assertIsNone(self.profil.compensation_expectation)
        self.assertIsNone(self.profil.compensation_period)
        self.assertEqual(self.profil.employment_types, [])
        self.assertEqual(self.profil.target_roles, [])
        self.assertTrue(self.profil.profile_visibility)
        self.assertFalse(self.profil.onboarding_completed)
        self.assertIsNone(self.profil.last_onboarding_step)

    def test_str_with_name(self):
        self.profil.prenom = "Dave"
        self.profil.nom = "Smith"
        self.profil.save()
        self.assertEqual(str(self.profil), "Dave Smith")

    def test_str_without_name(self):
        self.assertIn("Profil #", str(self.profil))

    def test_niveau_experience_choices(self):
        valid = ["DEBUTANT", "JUNIOR", "CONFIRME", "SENIOR"]
        for choice in valid:
            self.profil.niveau_experience = choice
            self.profil.full_clean()  # should not raise

    def test_onboarding_fields(self):
        self.profil.opportunity_types = ["JOB", "INTERNSHIP"]
        self.profil.preferred_location = "Paris"
        self.profil.remote_preference = "HYBRID"
        self.profil.compensation_expectation = 50000
        self.profil.compensation_period = "YEARLY"
        self.profil.employment_types = ["FULL_TIME"]
        self.profil.target_roles = ["Backend Developer"]
        self.profil.profile_visibility = False
        self.profil.onboarding_completed = True
        self.profil.last_onboarding_step = 5
        self.profil.save()
        self.profil.refresh_from_db()
        self.assertEqual(self.profil.opportunity_types, ["JOB", "INTERNSHIP"])
        self.assertEqual(self.profil.last_onboarding_step, 5)


class OTPChallengeModelTests(TestCase):
    """Tests for the OTPChallenge model."""

    def test_create_for_email(self):
        challenge, plaintext = OTPChallenge.create_for_email("user@example.com")
        self.assertEqual(len(plaintext), 6)
        self.assertTrue(plaintext.isdigit())
        self.assertEqual(challenge.email, "user@example.com")
        self.assertFalse(challenge.is_used)
        self.assertEqual(challenge.attempts, 0)
        # OTP stored as hash, not plaintext
        self.assertNotEqual(challenge.otp_hash, plaintext)
        self.assertTrue(check_password(plaintext, challenge.otp_hash))

    def test_verify_correct_otp(self):
        challenge, plaintext = OTPChallenge.create_for_email("user@example.com")
        self.assertTrue(challenge.verify(plaintext))
        challenge.refresh_from_db()
        self.assertTrue(challenge.is_used)

    def test_verify_wrong_otp(self):
        challenge, _plaintext = OTPChallenge.create_for_email("user@example.com")
        self.assertFalse(challenge.verify("000000"))
        challenge.refresh_from_db()
        self.assertEqual(challenge.attempts, 1)
        self.assertFalse(challenge.is_used)

    def test_verify_expired_otp(self):
        challenge, plaintext = OTPChallenge.create_for_email("user@example.com")
        challenge.expires_at = timezone.now() - timedelta(minutes=1)
        challenge.save()
        self.assertTrue(challenge.is_expired)
        self.assertFalse(challenge.verify(plaintext))

    def test_verify_used_otp(self):
        challenge, plaintext = OTPChallenge.create_for_email("user@example.com")
        challenge.verify(plaintext)  # first use
        self.assertFalse(challenge.verify(plaintext))  # second use rejected

    def test_verify_locked_after_max_attempts(self):
        challenge, plaintext = OTPChallenge.create_for_email("user@example.com")
        for _ in range(OTPChallenge.MAX_ATTEMPTS):
            challenge.verify("000000")
        challenge.refresh_from_db()
        self.assertTrue(challenge.is_locked)
        # Even correct OTP fails when locked
        self.assertFalse(challenge.verify(plaintext))

    def test_purge_expired(self):
        c1, _ = OTPChallenge.create_for_email("a@example.com")
        c1.expires_at = timezone.now() - timedelta(minutes=1)
        c1.save()
        c2, _ = OTPChallenge.create_for_email("b@example.com")  # still valid
        OTPChallenge.purge_expired()
        self.assertFalse(OTPChallenge.objects.filter(pk=c1.pk).exists())
        self.assertTrue(OTPChallenge.objects.filter(pk=c2.pk).exists())

    def test_purge_used(self):
        c1, otp = OTPChallenge.create_for_email("a@example.com")
        c1.verify(otp)  # mark used
        OTPChallenge.purge_expired()
        self.assertFalse(OTPChallenge.objects.filter(pk=c1.pk).exists())

    def test_purge_for_email(self):
        OTPChallenge.create_for_email("user@example.com")
        OTPChallenge.create_for_email("user@example.com")
        OTPChallenge.create_for_email("other@example.com")
        OTPChallenge.purge_for_email("user@example.com")
        self.assertEqual(OTPChallenge.objects.filter(email="user@example.com").count(), 0)
        self.assertEqual(OTPChallenge.objects.filter(email="other@example.com").count(), 1)

    def test_is_on_cooldown(self):
        OTPChallenge.create_for_email("user@example.com")
        self.assertTrue(OTPChallenge.is_on_cooldown("user@example.com"))
        self.assertFalse(OTPChallenge.is_on_cooldown("other@example.com"))

    def test_is_on_cooldown_after_expiry(self):
        challenge, _ = OTPChallenge.create_for_email("user@example.com")
        challenge.created_at = timezone.now() - timedelta(seconds=OTPChallenge.COOLDOWN_SECONDS + 1)
        challenge.save(update_fields=["created_at"])
        self.assertFalse(OTPChallenge.is_on_cooldown("user@example.com"))

    def test_str(self):
        challenge, _ = OTPChallenge.create_for_email("user@example.com")
        s = str(challenge)
        self.assertIn("user@example.com", s)

    def test_ordering(self):
        c1, _ = OTPChallenge.create_for_email("a@test.com")
        c2, _ = OTPChallenge.create_for_email("b@test.com")
        challenges = list(OTPChallenge.objects.all())
        # Ordered by -created_at, so c2 first
        self.assertEqual(challenges[0].pk, c2.pk)


# ═══════════════════════════════════════════════════════════
# SERIALIZER TESTS
# ═══════════════════════════════════════════════════════════


class ProfilSerializerTests(TestCase):
    def setUp(self):
        self.user = Utilisateur.objects.create_user(username="seruser", password="pass1234")
        self.profil = self.user.profil

    def test_serializes_all_fields(self):
        serializer = ProfilSerializer(self.profil)
        data = serializer.data
        expected_fields = {
            'id', 'nom', 'prenom', 'competences', 'domaines_interet',
            'niveau_experience', 'annees_experience',
            'opportunity_types', 'preferred_location', 'remote_preference',
            'compensation_expectation', 'compensation_period',
            'employment_types', 'target_roles', 'profile_visibility',
            'onboarding_completed', 'last_onboarding_step',
        }
        self.assertEqual(set(data.keys()), expected_fields)

    def test_id_is_read_only(self):
        serializer = ProfilSerializer(self.profil, data={"id": 999, "nom": "Test"}, partial=True)
        self.assertTrue(serializer.is_valid())
        instance = serializer.save()
        self.assertNotEqual(instance.id, 999)


class UtilisateurSerializerTests(TestCase):
    def setUp(self):
        self.user = Utilisateur.objects.create_user(
            username="seruser2", email="ser@test.com", password="pass1234"
        )

    def test_includes_nested_profil(self):
        serializer = UtilisateurSerializer(self.user)
        data = serializer.data
        self.assertIn("profil", data)
        self.assertIsNotNone(data["profil"])
        self.assertIn("nom", data["profil"])

    def test_fields_present(self):
        serializer = UtilisateurSerializer(self.user)
        data = serializer.data
        expected = {'id', 'username', 'email', 'first_name', 'last_name', 'is_active', 'date_joined', 'profil'}
        self.assertEqual(set(data.keys()), expected)


class ProfilUpdateSerializerTests(TestCase):
    def setUp(self):
        self.user = Utilisateur.objects.create_user(username="upduser", password="pass1234")
        self.profil = self.user.profil

    def test_partial_update(self):
        serializer = ProfilUpdateSerializer(
            self.profil,
            data={"nom": "UpdatedNom", "prenom": "UpdatedPrenom"},
            partial=True,
        )
        self.assertTrue(serializer.is_valid())
        instance = serializer.save()
        self.assertEqual(instance.nom, "UpdatedNom")
        self.assertEqual(instance.prenom, "UpdatedPrenom")

    def test_onboarding_fields_update(self):
        data = {
            "opportunity_types": ["JOB"],
            "preferred_location": "Lyon",
            "remote_preference": "REMOTE",
            "compensation_expectation": 3000,
            "compensation_period": "MONTHLY",
            "employment_types": ["CONTRACT"],
            "target_roles": ["DevOps Engineer"],
            "profile_visibility": False,
            "onboarding_completed": True,
            "last_onboarding_step": 5,
        }
        serializer = ProfilUpdateSerializer(self.profil, data=data, partial=True)
        self.assertTrue(serializer.is_valid())
        instance = serializer.save()
        self.assertEqual(instance.preferred_location, "Lyon")
        self.assertTrue(instance.onboarding_completed)


class OTPRequestSerializerTests(TestCase):
    def test_valid_email(self):
        s = OTPRequestSerializer(data={"email": "valid@example.com"})
        self.assertTrue(s.is_valid())
        self.assertEqual(s.validated_data["client_type"], "web")

    def test_valid_mobile_client_type(self):
        s = OTPRequestSerializer(data={"email": "valid@example.com", "client_type": "mobile"})
        self.assertTrue(s.is_valid())

    def test_invalid_client_type(self):
        s = OTPRequestSerializer(data={"email": "valid@example.com", "client_type": "desktop"})
        self.assertFalse(s.is_valid())

    def test_invalid_email(self):
        s = OTPRequestSerializer(data={"email": "not-an-email"})
        self.assertFalse(s.is_valid())

    def test_missing_email(self):
        s = OTPRequestSerializer(data={})
        self.assertFalse(s.is_valid())


class OTPVerifySerializerTests(TestCase):
    def test_valid(self):
        s = OTPVerifySerializer(data={"email": "u@test.com", "otp": "123456"})
        self.assertTrue(s.is_valid())

    def test_otp_too_short(self):
        s = OTPVerifySerializer(data={"email": "u@test.com", "otp": "123"})
        self.assertFalse(s.is_valid())

    def test_otp_too_long(self):
        s = OTPVerifySerializer(data={"email": "u@test.com", "otp": "1234567"})
        self.assertFalse(s.is_valid())

    def test_missing_otp(self):
        s = OTPVerifySerializer(data={"email": "u@test.com"})
        self.assertFalse(s.is_valid())

    def test_missing_email(self):
        s = OTPVerifySerializer(data={"otp": "123456"})
        self.assertFalse(s.is_valid())


# ═══════════════════════════════════════════════════════════
# PERMISSION TESTS
# ═══════════════════════════════════════════════════════════


class IsOwnerProfilePermissionTests(TestCase):
    def setUp(self):
        self.permission = IsOwnerProfile()
        self.user1 = Utilisateur.objects.create_user(username="owner", password="pass1234")
        self.user2 = Utilisateur.objects.create_user(username="other", password="pass1234")

    def _make_request(self, user):
        request = MagicMock()
        request.user = user
        return request

    def test_owner_has_permission(self):
        request = self._make_request(self.user1)
        self.assertTrue(
            self.permission.has_object_permission(request, None, self.user1.profil)
        )

    def test_non_owner_denied(self):
        request = self._make_request(self.user2)
        self.assertFalse(
            self.permission.has_object_permission(request, None, self.user1.profil)
        )


# ═══════════════════════════════════════════════════════════
# VIEW / API TESTS
# ═══════════════════════════════════════════════════════════


class ProfileDetailViewTests(APITestCase):
    """Tests for GET/PUT /api/profile/me/"""

    def setUp(self):
        self.user = Utilisateur.objects.create_user(
            username="viewuser", email="view@test.com", password="pass1234"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.url = "/api/profile/me/"

    def test_get_profile_authenticated(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], "viewuser")
        self.assertIn("profil", response.data)

    def test_get_profile_unauthenticated(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_put_profile_update(self):
        response = self.client.put(
            self.url,
            {"nom": "Dupont", "prenom": "Jean"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.profil.refresh_from_db()
        self.assertEqual(self.user.profil.nom, "Dupont")
        self.assertEqual(self.user.profil.prenom, "Jean")

    def test_put_profile_partial(self):
        response = self.client.put(self.url, {"competences": "Python, Django"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.profil.refresh_from_db()
        self.assertEqual(self.user.profil.competences, "Python, Django")

    def test_put_onboarding_fields(self):
        data = {
            "opportunity_types": ["JOB", "INTERNSHIP"],
            "preferred_location": "Tunis",
            "remote_preference": "REMOTE",
            "compensation_expectation": 60000,
            "compensation_period": "YEARLY",
            "employment_types": ["FULL_TIME"],
            "target_roles": ["Data Engineer"],
            "profile_visibility": False,
            "onboarding_completed": True,
            "last_onboarding_step": 5,
        }
        response = self.client.put(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.profil.refresh_from_db()
        self.assertTrue(self.user.profil.onboarding_completed)
        self.assertEqual(self.user.profil.preferred_location, "Tunis")

    def test_put_returns_full_user_serializer(self):
        response = self.client.put(self.url, {"nom": "Test"})
        self.assertIn("username", response.data)
        self.assertIn("profil", response.data)


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="test@bidwise.com",
)
class RequestOTPViewTests(APITestCase):
    """Tests for POST /api/auth/passwordless/request/"""

    def setUp(self):
        cache.clear()
        self.url = "/api/auth/passwordless/request/"
        self.client = APIClient()

    def test_request_otp_valid_email(self):
        response = self.client.post(self.url, {"email": "new@example.com"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("message", response.data)
        self.assertEqual(OTPChallenge.objects.filter(email="new@example.com").count(), 1)

    def test_request_otp_web_sends_email_and_logs(self):
        with self.assertLogs("users.otp_service", level="INFO") as logs:
            response = self.client.post(
                self.url,
                {"email": "web@example.com", "client_type": "web"},
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Un code de connexion a ete envoye a votre adresse email.")
        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue(any("OTP sent via email" in line for line in logs.output))

    def test_request_otp_mobile_simulates_without_email_and_logs(self):
        with self.assertLogs("users.otp_service", level="INFO") as logs:
            response = self.client.post(
                self.url,
                {"email": "mobile@example.com", "client_type": "mobile"},
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "OTP simulated for mobile")
        self.assertEqual(len(mail.outbox), 0)
        self.assertTrue(any("OTP simulated (mobile)" in line for line in logs.output))

    def test_request_otp_mobile_header_overrides_body(self):
        with self.assertLogs("users.otp_service", level="INFO") as logs:
            response = self.client.post(
                self.url,
                {"email": "mobile-header@example.com", "client_type": "web"},
                HTTP_X_CLIENT_TYPE="mobile",
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "OTP simulated for mobile")
        self.assertEqual(len(mail.outbox), 0)
        self.assertTrue(any("OTP simulated (mobile)" in line for line in logs.output))

    def test_request_otp_invalid_email(self):
        response = self.client.post(self.url, {"email": "not-email"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_request_otp_missing_email(self):
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_request_otp_email_lowercased(self):
        self.client.post(self.url, {"email": "USER@EXAMPLE.COM"})
        self.assertTrue(OTPChallenge.objects.filter(email="user@example.com").exists())

    def test_request_otp_cooldown(self):
        """Second request within cooldown period returns 200 but no new challenge."""
        self.client.post(self.url, {"email": "cool@example.com"})
        count_before = OTPChallenge.objects.filter(email="cool@example.com").count()
        response = self.client.post(self.url, {"email": "cool@example.com"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        count_after = OTPChallenge.objects.filter(email="cool@example.com").count()
        self.assertEqual(count_before, count_after)

    def test_request_otp_purges_old_challenges(self):
        """Previous non-cooldown challenges are purged when a new one is requested."""
        c, _ = OTPChallenge.create_for_email("purge@example.com")
        # Move created_at outside cooldown window
        c.created_at = timezone.now() - timedelta(seconds=OTPChallenge.COOLDOWN_SECONDS + 10)
        c.save(update_fields=["created_at"])
        self.client.post(self.url, {"email": "purge@example.com"})
        # Old challenge should be purged; exactly 1 new one exists
        self.assertEqual(OTPChallenge.objects.filter(email="purge@example.com").count(), 1)

    def test_constant_response_message(self):
        """Response message is always the same (prevents enumeration)."""
        r1 = self.client.post(self.url, {"email": "exists@example.com"})
        r2 = self.client.post(self.url, {"email": "nonexist@example.com"})
        self.assertEqual(r1.data["message"], r2.data["message"])


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="test@bidwise.com",
)
class VerifyOTPViewTests(APITestCase):
    """Tests for POST /api/auth/passwordless/verify/"""

    def setUp(self):
        cache.clear()
        self.url = "/api/auth/passwordless/verify/"
        self.client = APIClient()
        self.email = "otp@example.com"

    def _create_challenge(self, email=None):
        return OTPChallenge.create_for_email(email or self.email)

    def test_verify_valid_otp_existing_user(self):
        Utilisateur.objects.create_user(
            username="otp@example.com", email="otp@example.com", password="pass1234"
        )
        _challenge, plaintext = self._create_challenge()
        response = self.client.post(self.url, {"email": self.email, "otp": plaintext})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertFalse(response.data["is_new_user"])

    def test_verify_valid_otp_new_user_auto_created(self):
        _challenge, plaintext = self._create_challenge("new@example.com")
        response = self.client.post(
            self.url, {"email": "new@example.com", "otp": plaintext}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["is_new_user"])
        # User auto-created
        user = Utilisateur.objects.get(email="new@example.com")
        self.assertFalse(user.has_usable_password())
        # Profil auto-created via signal
        self.assertTrue(hasattr(user, "profil"))

    def test_verify_wrong_otp(self):
        self._create_challenge()
        response = self.client.post(self.url, {"email": self.email, "otp": "000000"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_verify_expired_otp(self):
        challenge, plaintext = self._create_challenge()
        challenge.expires_at = timezone.now() - timedelta(minutes=1)
        challenge.save()
        response = self.client.post(self.url, {"email": self.email, "otp": plaintext})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_verify_no_challenge_exists(self):
        response = self.client.post(
            self.url, {"email": "none@example.com", "otp": "123456"}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_verify_locked_after_max_attempts(self):
        challenge, plaintext = self._create_challenge()
        for _ in range(OTPChallenge.MAX_ATTEMPTS):
            self.client.post(self.url, {"email": self.email, "otp": "000000"})
        response = self.client.post(self.url, {"email": self.email, "otp": plaintext})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Trop de tentatives", response.data["error"])

    def test_verify_otp_single_use(self):
        _challenge, plaintext = self._create_challenge()
        Utilisateur.objects.create_user(
            username=self.email, email=self.email, password="pass1234"
        )
        r1 = self.client.post(self.url, {"email": self.email, "otp": plaintext})
        self.assertEqual(r1.status_code, status.HTTP_200_OK)
        r2 = self.client.post(self.url, {"email": self.email, "otp": plaintext})
        self.assertEqual(r2.status_code, status.HTTP_400_BAD_REQUEST)

    def test_verify_inactive_user_rejected(self):
        user = Utilisateur.objects.create_user(
            username=self.email, email=self.email, password="pass1234"
        )
        user.is_active = False
        user.save()
        _challenge, plaintext = self._create_challenge()
        response = self.client.post(self.url, {"email": self.email, "otp": plaintext})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_verify_invalid_serializer(self):
        response = self.client.post(self.url, {"email": "bad"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_verify_email_lowercased(self):
        _challenge, plaintext = self._create_challenge("upper@example.com")
        response = self.client.post(
            self.url, {"email": "UPPER@example.com", "otp": plaintext}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)


@override_settings(GOOGLE_CLIENT_ID="test-google-client-id")
class GoogleAuthViewTests(APITestCase):
    """Tests for POST /api/auth/google/"""

    def setUp(self):
        cache.clear()
        self.url = "/api/auth/google/"
        self.client = APIClient()
        self.valid_idinfo = {
            "aud": "test-google-client-id",
            "email": "google@example.com",
            "email_verified": True,
            "sub": "1234567890",
        }

    @patch("users.google_auth.google_id_token.verify_oauth2_token")
    def test_google_auth_new_user(self, mock_verify):
        mock_verify.return_value = self.valid_idinfo
        response = self.client.post(self.url, {"id_token": "valid-token"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertTrue(response.data["is_new_user"])
        user = Utilisateur.objects.get(email="google@example.com")
        self.assertFalse(user.has_usable_password())
        self.assertTrue(hasattr(user, "profil"))

    @patch("users.google_auth.google_id_token.verify_oauth2_token")
    def test_google_auth_existing_user(self, mock_verify):
        mock_verify.return_value = self.valid_idinfo
        Utilisateur.objects.create_user(
            username="google@example.com", email="google@example.com", password="pass"
        )
        response = self.client.post(self.url, {"id_token": "valid-token"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["is_new_user"])

    @patch("users.google_auth.google_id_token.verify_oauth2_token")
    def test_google_auth_inactive_user(self, mock_verify):
        mock_verify.return_value = self.valid_idinfo
        user = Utilisateur.objects.create_user(
            username="google@example.com", email="google@example.com", password="pass"
        )
        user.is_active = False
        user.save()
        response = self.client.post(self.url, {"id_token": "valid-token"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("users.google_auth.google_id_token.verify_oauth2_token")
    def test_google_auth_invalid_token(self, mock_verify):
        mock_verify.side_effect = ValueError("Invalid token")
        response = self.client.post(self.url, {"id_token": "bad-token"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    @patch("users.google_auth.google_id_token.verify_oauth2_token")
    def test_google_auth_network_error(self, mock_verify):
        mock_verify.side_effect = Exception("Network error")
        response = self.client.post(self.url, {"id_token": "some-token"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("users.google_auth.google_id_token.verify_oauth2_token")
    def test_google_auth_wrong_audience(self, mock_verify):
        idinfo = {**self.valid_idinfo, "aud": "wrong-client-id"}
        mock_verify.return_value = idinfo
        response = self.client.post(self.url, {"id_token": "valid-token"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("users.google_auth.google_id_token.verify_oauth2_token")
    def test_google_auth_unverified_email(self, mock_verify):
        idinfo = {**self.valid_idinfo, "email_verified": False}
        mock_verify.return_value = idinfo
        response = self.client.post(self.url, {"id_token": "valid-token"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_google_auth_missing_id_token(self):
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @override_settings(GOOGLE_CLIENT_ID="")
    def test_google_auth_not_configured(self):
        response = self.client.post(self.url, {"id_token": "token"})
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    @patch("users.google_auth.google_id_token.verify_oauth2_token")
    def test_google_auth_email_lowercased(self, mock_verify):
        idinfo = {**self.valid_idinfo, "email": "UPPER@Example.COM"}
        mock_verify.return_value = idinfo
        response = self.client.post(self.url, {"id_token": "valid-token"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(Utilisateur.objects.filter(email="upper@example.com").exists())


class TokenRefreshViewTests(APITestCase):
    """Tests for POST /api/auth/refresh/"""

    def setUp(self):
        self.url = "/api/auth/refresh/"
        self.user = Utilisateur.objects.create_user(
            username="refreshuser", email="refresh@test.com", password="pass1234"
        )

    def test_refresh_valid_token(self):
        from rest_framework_simplejwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(self.user)
        response = self.client.post(self.url, {"refresh": str(refresh)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_refresh_invalid_token(self):
        response = self.client.post(self.url, {"refresh": "invalidtoken"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ═══════════════════════════════════════════════════════════
# SPRINT 1.1 — TOKEN REVOCATION (LOGOUT) TESTS
# ═══════════════════════════════════════════════════════════


class LogoutViewTests(APITestCase):
    """Tests for POST /api/auth/logout/ (token blacklist)."""

    def setUp(self):
        from rest_framework_simplejwt.tokens import RefreshToken

        self.url = "/api/auth/logout/"
        self.user = Utilisateur.objects.create_user(
            username="logoutuser", email="logout@test.com", password="pass1234"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.refresh = RefreshToken.for_user(self.user)

    def test_logout_blacklists_token(self):
        response = self.client.post(self.url, {"refresh": str(self.refresh)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["detail"], "Successfully logged out.")

    def test_blacklisted_token_cannot_refresh(self):
        """After logout, the refresh token can no longer obtain a new access token."""
        self.client.post(self.url, {"refresh": str(self.refresh)})
        response = self.client.post("/api/auth/refresh/", {"refresh": str(self.refresh)})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_already_blacklisted_token(self):
        self.client.post(self.url, {"refresh": str(self.refresh)})
        response = self.client.post(self.url, {"refresh": str(self.refresh)})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logout_missing_refresh_token(self):
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_logout_invalid_refresh_token(self):
        response = self.client.post(self.url, {"refresh": "not-a-real-token"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logout_requires_authentication(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(self.url, {"refresh": str(self.refresh)})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ═══════════════════════════════════════════════════════════
# SPRINT 1.1 — LOGIN EVENT MODEL TESTS
# ═══════════════════════════════════════════════════════════


class LoginEventModelTests(TestCase):
    """Tests for the LoginEvent model."""

    def setUp(self):
        self.user = Utilisateur.objects.create_user(
            username="eventuser", email="event@test.com", password="pass1234"
        )

    def test_str(self):
        from .models import LoginEvent
        event = LoginEvent.objects.create(
            user=self.user, ip_address="1.2.3.4", user_agent="Test Agent"
        )
        self.assertIn("event@test.com", str(event))
        self.assertIn("1.2.3.4", str(event))

    def test_parse_device_type_desktop(self):
        from .models import LoginEvent
        self.assertEqual(LoginEvent._parse_device_type("Mozilla/5.0 Windows NT"), "Desktop")

    def test_parse_device_type_mobile(self):
        from .models import LoginEvent
        self.assertEqual(LoginEvent._parse_device_type("Mozilla/5.0 iPhone"), "Mobile")
        self.assertEqual(LoginEvent._parse_device_type("Mozilla/5.0 Android"), "Mobile")

    def test_parse_device_type_tablet(self):
        from .models import LoginEvent
        self.assertEqual(LoginEvent._parse_device_type("Mozilla/5.0 iPad"), "Tablet")

    def test_get_client_ip_remote_addr(self):
        from .models import LoginEvent
        request = MagicMock()
        request.META = {"REMOTE_ADDR": "192.168.1.1"}
        self.assertEqual(LoginEvent._get_client_ip(request), "192.168.1.1")


    def test_get_client_ip_forwarded(self):
        from .models import LoginEvent
        request = MagicMock()
        request.META = {"HTTP_X_FORWARDED_FOR": "10.0.0.1, 10.0.0.2", "REMOTE_ADDR": "127.0.0.1"}
        self.assertEqual(LoginEvent._get_client_ip(request), "10.0.0.1")


# ═══════════════════════════════════════════════════════════
# SPRINT 1.1 — SUSPICIOUS LOGIN DETECTION TESTS
# ═══════════════════════════════════════════════════════════


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="test@bidwise.com",
)
class SuspiciousLoginDetectionTests(TestCase):
    """Tests for LoginEvent.is_suspicious() and LoginEvent.record()."""

    def setUp(self):
        from .models import LoginEvent
        self.LoginEvent = LoginEvent
        self.user = Utilisateur.objects.create_user(
            username="suspuser", email="susp@test.com", password="pass1234"
        )

    def test_first_login_not_suspicious(self):
        """Very first login for a user is never flagged as suspicious."""
        result = self.LoginEvent.is_suspicious(self.user, "1.2.3.4", "AgentA")
        self.assertFalse(result)

    def test_same_ip_same_ua_not_suspicious(self):
        """Login from same IP + same UA is not suspicious."""
        self.LoginEvent.objects.create(
            user=self.user, ip_address="1.2.3.4", user_agent="AgentA"
        )
        result = self.LoginEvent.is_suspicious(self.user, "1.2.3.4", "AgentA")
        self.assertFalse(result)

    def test_new_ip_is_suspicious(self):
        """Login from a new IP triggers suspicious."""
        self.LoginEvent.objects.create(
            user=self.user, ip_address="1.2.3.4", user_agent="AgentA"
        )
        result = self.LoginEvent.is_suspicious(self.user, "5.6.7.8", "AgentA")
        self.assertTrue(result)

    def test_new_ua_is_suspicious(self):
        """Login from a new user agent triggers suspicious."""
        self.LoginEvent.objects.create(
            user=self.user, ip_address="1.2.3.4", user_agent="AgentA"
        )
        result = self.LoginEvent.is_suspicious(self.user, "1.2.3.4", "AgentB")
        self.assertTrue(result)

    def test_record_creates_event(self):
        """record() creates a LoginEvent in the DB."""
        request = MagicMock()
        request.META = {"REMOTE_ADDR": "10.0.0.1", "HTTP_USER_AGENT": "TestBrowser"}
        event = self.LoginEvent.record(self.user, request)
        self.assertEqual(event.ip_address, "10.0.0.1")
        self.assertEqual(event.user_agent, "TestBrowser")
        self.assertEqual(event.device_type, "Desktop")
        self.assertEqual(self.LoginEvent.objects.filter(user=self.user).count(), 1)

    @patch("users.models.LoginEvent._send_suspicious_email")
    def test_record_sends_email_on_suspicious(self, mock_email):
        """record() sends a suspicious-login email when the device/IP is new."""
        # First login — not suspicious
        request1 = MagicMock()
        request1.META = {"REMOTE_ADDR": "10.0.0.1", "HTTP_USER_AGENT": "BrowserA"}
        self.LoginEvent.record(self.user, request1)
        mock_email.assert_not_called()

        # Second login from new IP — suspicious
        request2 = MagicMock()
        request2.META = {"REMOTE_ADDR": "99.99.99.99", "HTTP_USER_AGENT": "BrowserA"}
        self.LoginEvent.record(self.user, request2)
        mock_email.assert_called_once()

    @patch("users.models.LoginEvent._send_suspicious_email")
    def test_record_no_email_on_known_device(self, mock_email):
        """record() does not send email when logging from a known device."""
        request = MagicMock()
        request.META = {"REMOTE_ADDR": "10.0.0.1", "HTTP_USER_AGENT": "BrowserA"}
        self.LoginEvent.record(self.user, request)
        self.LoginEvent.record(self.user, request)
        mock_email.assert_not_called()


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="test@bidwise.com",
)
class VerifyOTPLoginEventIntegrationTests(APITestCase):
    """Tests that verify_otp creates a LoginEvent."""

    def test_login_event_created_on_verify(self):
        from .models import LoginEvent

        email = "evt@example.com"
        _challenge, plaintext = OTPChallenge.create_for_email(email)
        response = self.client.post(
            "/api/auth/passwordless/verify/",
            {"email": email, "otp": plaintext},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user = Utilisateur.objects.get(email=email)
        self.assertEqual(LoginEvent.objects.filter(user=user).count(), 1)
