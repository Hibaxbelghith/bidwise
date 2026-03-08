"""
Comprehensive tests for the opportunities app — Sprint 1.

Covers:
  - Models: SourceOpportunite, Opportunite (fields, choices, indexes, ordering)
  - Serializers: OpportuniteSerializer (including date validation), SourceOpportuniteSerializer
  - Views: CRUD, filtering, ordering, permissions
  - Permissions: IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly
"""

from datetime import date, timedelta
from unittest.mock import MagicMock

from django.test import TestCase
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from users.models import Utilisateur
from .models import Opportunite, SourceOpportunite, TypeOpportunite, StatutOpportunite
from .serializers import OpportuniteSerializer, SourceOpportuniteSerializer
from .permissions import IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly


# ═══════════════════════════════════════════════════════════
# MODEL TESTS
# ═══════════════════════════════════════════════════════════


class SourceOpportuniteModelTests(TestCase):
    def test_create_source(self):
        source = SourceOpportunite.objects.create(
            nom="LinkedIn", url="https://linkedin.com", type_source="SITE_EMPLOI"
        )
        self.assertEqual(source.nom, "LinkedIn")
        self.assertEqual(str(source), "LinkedIn")

    def test_type_source_choices(self):
        for choice_value in ["SITE_EMPLOI", "PORTAIL_PROJET", "AUTRE"]:
            source = SourceOpportunite(
                nom=f"Source {choice_value}",
                url="https://example.com",
                type_source=choice_value,
            )
            source.full_clean()  # should not raise


class OpportuniteModelTests(TestCase):
    def setUp(self):
        self.user = Utilisateur.objects.create_user(username="org", password="pass1234")
        self.source = SourceOpportunite.objects.create(
            nom="Indeed", url="https://indeed.com", type_source="SITE_EMPLOI"
        )

    def test_create_opportunite(self):
        opp = Opportunite.objects.create(
            titre="Dev Backend",
            description="Développeur Django",
            type_opportunite=TypeOpportunite.EMPLOI,
            statut=StatutOpportunite.ACTIVE,
            date_publication=date.today(),
            organisation=self.user,
            source=self.source,
        )
        self.assertEqual(str(opp), "Dev Backend")
        self.assertEqual(opp.statut, "ACTIVE")

    def test_default_statut_is_active(self):
        opp = Opportunite.objects.create(
            titre="Stage IA",
            description="Stage en IA",
            type_opportunite=TypeOpportunite.STAGE,
            date_publication=date.today(),
            source=self.source,
        )
        self.assertEqual(opp.statut, StatutOpportunite.ACTIVE)

    def test_type_opportunite_choices(self):
        for choice in TypeOpportunite.values:
            opp = Opportunite(
                titre=f"Opp {choice}",
                description="desc",
                type_opportunite=choice,
                date_publication=date.today(),
                source=self.source,
            )
            opp.full_clean()

    def test_statut_choices(self):
        for choice in StatutOpportunite.values:
            opp = Opportunite(
                titre=f"Opp {choice}",
                description="desc",
                type_opportunite=TypeOpportunite.EMPLOI,
                statut=choice,
                date_publication=date.today(),
                source=self.source,
            )
            opp.full_clean()

    def test_date_limite_optional(self):
        opp = Opportunite.objects.create(
            titre="No deadline",
            description="desc",
            type_opportunite=TypeOpportunite.PROJET,
            date_publication=date.today(),
            source=self.source,
        )
        self.assertIsNone(opp.date_limite)

    def test_organisation_optional(self):
        opp = Opportunite.objects.create(
            titre="No org",
            description="desc",
            type_opportunite=TypeOpportunite.FINANCEMENT,
            date_publication=date.today(),
            source=self.source,
        )
        self.assertIsNone(opp.organisation)

    def test_ordering_by_date_publication_desc(self):
        opp1 = Opportunite.objects.create(
            titre="Old",
            description="d",
            type_opportunite=TypeOpportunite.EMPLOI,
            date_publication=date.today() - timedelta(days=5),
            source=self.source,
        )
        opp2 = Opportunite.objects.create(
            titre="New",
            description="d",
            type_opportunite=TypeOpportunite.EMPLOI,
            date_publication=date.today(),
            source=self.source,
        )
        opps = list(Opportunite.objects.all())
        self.assertEqual(opps[0].pk, opp2.pk)
        self.assertEqual(opps[1].pk, opp1.pk)

    def test_auto_timestamps(self):
        opp = Opportunite.objects.create(
            titre="Timestamped",
            description="d",
            type_opportunite=TypeOpportunite.EMPLOI,
            date_publication=date.today(),
            source=self.source,
        )
        self.assertIsNotNone(opp.date_creation)
        self.assertIsNotNone(opp.date_modification)

    def test_organisation_set_null_on_delete(self):
        opp = Opportunite.objects.create(
            titre="Org delete",
            description="d",
            type_opportunite=TypeOpportunite.EMPLOI,
            date_publication=date.today(),
            organisation=self.user,
            source=self.source,
        )
        self.user.delete()
        opp.refresh_from_db()
        self.assertIsNone(opp.organisation)


# ═══════════════════════════════════════════════════════════
# SERIALIZER TESTS
# ═══════════════════════════════════════════════════════════


class SourceOpportuniteSerializerTests(TestCase):
    def test_serializes_fields(self):
        source = SourceOpportunite.objects.create(
            nom="Test", url="https://test.com", type_source="AUTRE"
        )
        data = SourceOpportuniteSerializer(source).data
        self.assertEqual(set(data.keys()), {"id", "nom", "url", "type_source"})

    def test_deserializes_valid_data(self):
        s = SourceOpportuniteSerializer(
            data={"nom": "New", "url": "https://new.com", "type_source": "AUTRE"}
        )
        self.assertTrue(s.is_valid())


class OpportuniteSerializerTests(TestCase):
    def setUp(self):
        self.source = SourceOpportunite.objects.create(
            nom="Src", url="https://src.com", type_source="SITE_EMPLOI"
        )

    def test_serializes_with_nested_source(self):
        opp = Opportunite.objects.create(
            titre="Opp",
            description="d",
            type_opportunite=TypeOpportunite.EMPLOI,
            date_publication=date.today(),
            source=self.source,
        )
        data = OpportuniteSerializer(opp).data
        self.assertIn("source", data)
        self.assertEqual(data["source"]["nom"], "Src")

    def test_validate_date_limite_before_publication_rejected(self):
        data = {
            "titre": "Bad dates",
            "description": "d",
            "type_opportunite": "EMPLOI",
            "date_publication": "2026-03-10",
            "date_limite": "2026-03-05",
            "source_id": self.source.pk,
        }
        s = OpportuniteSerializer(data=data)
        self.assertFalse(s.is_valid())
        self.assertIn("date_limite", s.errors)

    def test_validate_date_limite_equal_to_publication_accepted(self):
        today = date.today().isoformat()
        data = {
            "titre": "Same dates",
            "description": "d",
            "type_opportunite": "EMPLOI",
            "date_publication": today,
            "date_limite": today,
            "source_id": self.source.pk,
        }
        s = OpportuniteSerializer(data=data)
        # source is read_only in serializer, so we need to handle it
        # The serializer has source as read_only, so creation via serializer
        # won't include source. This validates the date logic only.
        if not s.is_valid():
            # Only date_limite error matters here
            self.assertNotIn("date_limite", s.errors)

    def test_validate_date_limite_after_publication_accepted(self):
        data = {
            "titre": "Good dates",
            "description": "d",
            "type_opportunite": "EMPLOI",
            "date_publication": "2026-03-01",
            "date_limite": "2026-03-31",
            "source_id": self.source.pk,
        }
        s = OpportuniteSerializer(data=data)
        if not s.is_valid():
            self.assertNotIn("date_limite", s.errors)

    def test_validate_no_date_limite_accepted(self):
        data = {
            "titre": "No deadline",
            "description": "d",
            "type_opportunite": "EMPLOI",
            "date_publication": "2026-03-10",
            "source_id": self.source.pk,
        }
        s = OpportuniteSerializer(data=data)
        if not s.is_valid():
            self.assertNotIn("date_limite", s.errors)


# ═══════════════════════════════════════════════════════════
# PERMISSION TESTS
# ═══════════════════════════════════════════════════════════


class IsAuthenticatedOrReadOnlyPermissionTests(TestCase):
    def setUp(self):
        self.permission = IsAuthenticatedOrReadOnly()

    def _make_request(self, user=None):
        request = MagicMock()
        request.user = user if user else MagicMock(is_authenticated=False)
        return request

    def test_authenticated_user_allowed(self):
        user = Utilisateur.objects.create_user(username="u1", password="pass1234")
        request = self._make_request(user)
        self.assertTrue(self.permission.has_permission(request, None))

    def test_anonymous_user_denied(self):
        request = self._make_request(None)
        self.assertFalse(self.permission.has_permission(request, None))


class IsOwnerOrReadOnlyPermissionTests(TestCase):
    def setUp(self):
        self.permission = IsOwnerOrReadOnly()
        self.owner = Utilisateur.objects.create_user(username="owner", password="pass1234")
        self.other = Utilisateur.objects.create_user(username="other", password="pass1234")
        self.source = SourceOpportunite.objects.create(
            nom="S", url="https://s.com", type_source="AUTRE"
        )
        self.opp = Opportunite.objects.create(
            titre="Owned",
            description="d",
            type_opportunite=TypeOpportunite.EMPLOI,
            date_publication=date.today(),
            organisation=self.owner,
            source=self.source,
        )

    def _make_request(self, user, method="GET"):
        request = MagicMock()
        request.user = user
        request.method = method
        return request

    def test_owner_can_modify(self):
        request = self._make_request(self.owner, "PUT")
        self.assertTrue(self.permission.has_object_permission(request, None, self.opp))

    def test_non_owner_cannot_modify(self):
        request = self._make_request(self.other, "PUT")
        self.assertFalse(self.permission.has_object_permission(request, None, self.opp))

    def test_non_owner_can_read(self):
        request = self._make_request(self.other, "GET")
        self.assertTrue(self.permission.has_object_permission(request, None, self.opp))

    def test_safe_methods_allowed(self):
        for method in ("GET", "HEAD", "OPTIONS"):
            request = self._make_request(self.other, method)
            self.assertTrue(self.permission.has_object_permission(request, None, self.opp))


# ═══════════════════════════════════════════════════════════
# VIEW / API TESTS
# ═══════════════════════════════════════════════════════════


class OpportuniteViewSetTests(APITestCase):
    """Tests for /api/opportunites/ CRUD, filtering, ordering."""

    def setUp(self):
        self.user = Utilisateur.objects.create_user(
            username="apiuser", email="api@test.com", password="pass1234"
        )
        self.other_user = Utilisateur.objects.create_user(
            username="otherapi", email="other@test.com", password="pass1234"
        )
        self.source = SourceOpportunite.objects.create(
            nom="JobBoard", url="https://jobboard.com", type_source="SITE_EMPLOI"
        )
        self.client = APIClient()
        self.url = "/api/opportunites/"

    def _create_opp(self, titre="Dev", type_opp="EMPLOI", statut="ACTIVE",
                     date_pub=None, organisation=None):
        return Opportunite.objects.create(
            titre=titre,
            description="desc",
            type_opportunite=type_opp,
            statut=statut,
            date_publication=date_pub or date.today(),
            organisation=organisation or self.user,
            source=self.source,
        )

    # ── Authentication ────────────────────────────────────

    def test_list_requires_authentication(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_authenticated(self):
        self.client.force_authenticate(user=self.user)
        self._create_opp()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # ── List / Read ───────────────────────────────────────

    def test_list_only_active(self):
        """ViewSet queryset filters to statut=ACTIVE only."""
        self.client.force_authenticate(user=self.user)
        self._create_opp(titre="Active1")
        self._create_opp(titre="Expired", statut="EXPIREE")
        self._create_opp(titre="Archived", statut="ARCHIVEE")
        response = self.client.get(self.url)
        titles = [r["titre"] for r in response.data["results"]]
        self.assertIn("Active1", titles)
        self.assertNotIn("Expired", titles)
        self.assertNotIn("Archived", titles)

    def test_retrieve_single(self):
        self.client.force_authenticate(user=self.user)
        opp = self._create_opp(titre="Single")
        response = self.client.get(f"{self.url}{opp.pk}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["titre"], "Single")

    # ── Create ────────────────────────────────────────────

    def test_create_opportunite(self):
        self.client.force_authenticate(user=self.user)
        data = {
            "titre": "New Opp",
            "description": "A new opportunity",
            "type_opportunite": "STAGE",
            "date_publication": date.today().isoformat(),
            "source_id": self.source.pk,
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["titre"], "New Opp")

    def test_create_unauthenticated(self):
        data = {
            "titre": "Fail",
            "description": "d",
            "type_opportunite": "EMPLOI",
            "date_publication": date.today().isoformat(),
            "source_id": self.source.pk,
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # ── Update ────────────────────────────────────────────

    def test_update_own_opportunite(self):
        self.client.force_authenticate(user=self.user)
        opp = self._create_opp(titre="Old Title", organisation=self.user)
        response = self.client.patch(
            f"{self.url}{opp.pk}/", {"titre": "New Title"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        opp.refresh_from_db()
        self.assertEqual(opp.titre, "New Title")

    def test_update_other_user_opportunite_forbidden(self):
        self.client.force_authenticate(user=self.other_user)
        opp = self._create_opp(titre="Not mine", organisation=self.user)
        response = self.client.patch(
            f"{self.url}{opp.pk}/", {"titre": "Hacked"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ── Delete ────────────────────────────────────────────

    def test_delete_own_opportunite(self):
        self.client.force_authenticate(user=self.user)
        opp = self._create_opp(organisation=self.user)
        response = self.client.delete(f"{self.url}{opp.pk}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Opportunite.objects.filter(pk=opp.pk).exists())

    def test_delete_other_user_opportunite_forbidden(self):
        self.client.force_authenticate(user=self.other_user)
        opp = self._create_opp(organisation=self.user)
        response = self.client.delete(f"{self.url}{opp.pk}/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ── Filtering ─────────────────────────────────────────

    def test_filter_by_type_opportunite(self):
        self.client.force_authenticate(user=self.user)
        self._create_opp(titre="Emploi", type_opp="EMPLOI")
        self._create_opp(titre="Stage", type_opp="STAGE")
        response = self.client.get(self.url, {"type_opportunite": "STAGE"})
        titles = [r["titre"] for r in response.data["results"]]
        self.assertIn("Stage", titles)
        self.assertNotIn("Emploi", titles)

    def test_filter_by_source(self):
        self.client.force_authenticate(user=self.user)
        source2 = SourceOpportunite.objects.create(
            nom="Other", url="https://other.com", type_source="AUTRE"
        )
        self._create_opp(titre="FromJobBoard")
        Opportunite.objects.create(
            titre="FromOther",
            description="d",
            type_opportunite="EMPLOI",
            date_publication=date.today(),
            source=source2,
        )
        response = self.client.get(self.url, {"source": self.source.pk})
        titles = [r["titre"] for r in response.data["results"]]
        self.assertIn("FromJobBoard", titles)
        self.assertNotIn("FromOther", titles)

    # ── Ordering ──────────────────────────────────────────

    def test_ordering_by_date_publication(self):
        self.client.force_authenticate(user=self.user)
        self._create_opp(titre="Old", date_pub=date.today() - timedelta(days=10))
        self._create_opp(titre="New", date_pub=date.today())
        response = self.client.get(self.url, {"ordering": "date_publication"})
        titles = [r["titre"] for r in response.data["results"]]
        self.assertEqual(titles[0], "Old")

    def test_ordering_by_date_publication_desc(self):
        self.client.force_authenticate(user=self.user)
        self._create_opp(titre="Old", date_pub=date.today() - timedelta(days=10))
        self._create_opp(titre="New", date_pub=date.today())
        response = self.client.get(self.url, {"ordering": "-date_publication"})
        titles = [r["titre"] for r in response.data["results"]]
        self.assertEqual(titles[0], "New")

    # ── Pagination ────────────────────────────────────────

    def test_paginated_response(self):
        self.client.force_authenticate(user=self.user)
        self._create_opp()
        response = self.client.get(self.url)
        self.assertIn("results", response.data)
        self.assertIn("count", response.data)


class SourceOpportuniteViewSetTests(APITestCase):
    """Tests for /api/sources/ CRUD."""

    def setUp(self):
        self.user = Utilisateur.objects.create_user(
            username="srcuser", email="src@test.com", password="pass1234"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.url = "/api/sources/"

    def test_list_sources(self):
        SourceOpportunite.objects.create(
            nom="S1", url="https://s1.com", type_source="SITE_EMPLOI"
        )
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_source(self):
        data = {"nom": "New", "url": "https://new.com", "type_source": "AUTRE"}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_retrieve_source(self):
        source = SourceOpportunite.objects.create(
            nom="Ret", url="https://ret.com", type_source="PORTAIL_PROJET"
        )
        response = self.client.get(f"{self.url}{source.pk}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["nom"], "Ret")

    def test_delete_source(self):
        source = SourceOpportunite.objects.create(
            nom="Del", url="https://del.com", type_source="AUTRE"
        )
        response = self.client.delete(f"{self.url}{source.pk}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
