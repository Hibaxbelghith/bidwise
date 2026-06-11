"""
Comprehensive tests for the applications (candidatures) app — Sprint 1.

Covers:
  - Models: Candidature, Document (fields, constraints, relationships)
  - Serializers: CandidatureSerializer, DocumentSerializer
  - Views: CandidatureViewSet (CRUD, ownership scoping, auto-assign candidat)
  - Permissions: IsOwnerCandidature
"""

from datetime import date
from unittest.mock import MagicMock

from django.test import TestCase
from django.db import IntegrityError

from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from users.models import Utilisateur
from opportunities.models import Opportunite, SourceOpportunite
from .models import Candidature, Document, StatutSuiviCandidature, TypeDocument
from .serializers import CandidatureSerializer, DocumentSerializer
from .permissions import IsOwnerCandidature


# ═══════════════════════════════════════════════════════════
# MODEL TESTS
# ═══════════════════════════════════════════════════════════


class CandidatureModelTests(TestCase):
    def setUp(self):
        self.user = Utilisateur.objects.create_user(username="cand1", password="pass1234")
        self.source = SourceOpportunite.objects.create(
            nom="Src", url="https://src.com", type_source="SITE_EMPLOI"
        )
        self.opp = Opportunite.objects.create(
            titre="Dev Backend",
            description="desc",
            type_opportunite="EMPLOI",
            date_publication=date.today(),
            source=self.source,
        )

    def test_create_candidature(self):
        cand = Candidature.objects.create(
            candidat=self.user, opportunite=self.opp
        )
        self.assertEqual(cand.statut, StatutSuiviCandidature.VUE)
        self.assertIsNone(cand.url_source)
        self.assertIsNotNone(cand.date_creation)
        self.assertIsNotNone(cand.derniere_mise_a_jour)

    def test_str(self):
        cand = Candidature.objects.create(
            candidat=self.user, opportunite=self.opp
        )
        s = str(cand)
        self.assertIn(str(self.user), s)
        self.assertIn(str(self.opp), s)

    def test_statut_choices(self):
        for choice in StatutSuiviCandidature.values:
            cand = Candidature(
                candidat=self.user,
                opportunite=self.opp,
                statut=choice,
            )
            cand.full_clean()

    def test_default_statut_is_vue(self):
        cand = Candidature.objects.create(
            candidat=self.user, opportunite=self.opp
        )
        self.assertEqual(cand.statut, "VUE")

    def test_unique_together_candidat_opportunite(self):
        Candidature.objects.create(candidat=self.user, opportunite=self.opp)
        with self.assertRaises(IntegrityError):
            Candidature.objects.create(candidat=self.user, opportunite=self.opp)

    def test_url_source_optional(self):
        cand = Candidature.objects.create(
            candidat=self.user,
            opportunite=self.opp,
            url_source="https://apply.example.com/123",
        )
        self.assertEqual(cand.url_source, "https://apply.example.com/123")

    def test_cascade_delete_user(self):
        Candidature.objects.create(candidat=self.user, opportunite=self.opp)
        self.user.delete()
        self.assertEqual(Candidature.objects.count(), 0)

    def test_cascade_delete_opportunite(self):
        Candidature.objects.create(candidat=self.user, opportunite=self.opp)
        self.opp.delete()
        self.assertEqual(Candidature.objects.count(), 0)

    def test_multiple_candidatures_different_users(self):
        user2 = Utilisateur.objects.create_user(username="cand2", password="pass1234")
        Candidature.objects.create(candidat=self.user, opportunite=self.opp)
        Candidature.objects.create(candidat=user2, opportunite=self.opp)
        self.assertEqual(Candidature.objects.filter(opportunite=self.opp).count(), 2)

    def test_multiple_candidatures_different_opps(self):
        opp2 = Opportunite.objects.create(
            titre="Second",
            description="d",
            type_opportunite="STAGE",
            date_publication=date.today(),
            source=self.source,
        )
        Candidature.objects.create(candidat=self.user, opportunite=self.opp)
        Candidature.objects.create(candidat=self.user, opportunite=opp2)
        self.assertEqual(Candidature.objects.filter(candidat=self.user).count(), 2)


class DocumentModelTests(TestCase):
    def setUp(self):
        self.user = Utilisateur.objects.create_user(username="docuser", password="pass1234")
        self.source = SourceOpportunite.objects.create(
            nom="S", url="https://s.com", type_source="AUTRE"
        )
        self.opp = Opportunite.objects.create(
            titre="Opp",
            description="d",
            type_opportunite="EMPLOI",
            date_publication=date.today(),
            source=self.source,
        )
        self.cand = Candidature.objects.create(
            candidat=self.user, opportunite=self.opp
        )

    def test_type_document_choices(self):
        for choice in TypeDocument.values:
            doc = Document(
                candidature=self.cand,
                type_document=choice,
                fichier="documents/test.pdf",
            )
            doc.full_clean()

    def test_str(self):
        doc = Document.objects.create(
            candidature=self.cand,
            type_document=TypeDocument.CV,
            fichier="documents/cv.pdf",
        )
        self.assertIn("CV", str(doc))

    def test_cascade_delete_candidature(self):
        Document.objects.create(
            candidature=self.cand,
            type_document=TypeDocument.CV,
            fichier="documents/cv.pdf",
        )
        self.cand.delete()
        self.assertEqual(Document.objects.count(), 0)


# ═══════════════════════════════════════════════════════════
# SERIALIZER TESTS
# ═══════════════════════════════════════════════════════════


class DocumentSerializerTests(TestCase):
    def test_fields(self):
        s = DocumentSerializer()
        expected = {"id", "type_document", "fichier", "date_upload"}
        self.assertEqual(set(s.fields.keys()), expected)


class CandidatureSerializerTests(TestCase):
    def setUp(self):
        self.user = Utilisateur.objects.create_user(username="seruser", password="pass1234")
        self.source = SourceOpportunite.objects.create(
            nom="S", url="https://s.com", type_source="AUTRE"
        )
        self.opp = Opportunite.objects.create(
            titre="Opp",
            description="d",
            type_opportunite="EMPLOI",
            date_publication=date.today(),
            source=self.source,
        )

    def test_serializes_all_fields(self):
        cand = Candidature.objects.create(candidat=self.user, opportunite=self.opp)
        data = CandidatureSerializer(cand).data
        expected = {
            "id", "candidat", "opportunite", "statut", "url_source",
            "cv", "cover_letter_url", "contact_email", "contact_phone",
            "submitted_at", "date_creation", "derniere_mise_a_jour", "documents"
        }
        self.assertEqual(set(data.keys()), expected)

    def test_read_only_fields(self):
        s = CandidatureSerializer()
        self.assertIn("date_creation", s.Meta.read_only_fields)
        self.assertIn("derniere_mise_a_jour", s.Meta.read_only_fields)

    def test_documents_nested_read_only(self):
        cand = Candidature.objects.create(candidat=self.user, opportunite=self.opp)
        Document.objects.create(
            candidature=cand,
            type_document="CV",
            fichier="documents/cv.pdf",
        )
        data = CandidatureSerializer(cand).data
        self.assertEqual(len(data["documents"]), 1)
        self.assertEqual(data["documents"][0]["type_document"], "CV")

    def test_deserializes_valid_data(self):
        data = {
            "candidat": self.user.pk,
            "opportunite": self.opp.pk,
            "statut": "INTERESSEE",
        }
        s = CandidatureSerializer(data=data)
        self.assertTrue(s.is_valid(), s.errors)

    def test_rejects_application_for_non_active_opportunity(self):
        for opportunity_status in ("SUSPENDUE", "FERMEE"):
            self.opp.statut = opportunity_status
            self.opp.save(update_fields=["statut"])
            serializer = CandidatureSerializer(data={
                "candidat": self.user.pk,
                "opportunite": self.opp.pk,
                "statut": "INTERESSEE",
            })
            self.assertFalse(serializer.is_valid())
            self.assertIn("opportunite", serializer.errors)


# ═══════════════════════════════════════════════════════════
# PERMISSION TESTS
# ═══════════════════════════════════════════════════════════


class IsOwnerCandidaturePermissionTests(TestCase):
    def setUp(self):
        self.permission = IsOwnerCandidature()
        self.owner = Utilisateur.objects.create_user(username="owner", password="pass1234")
        self.other = Utilisateur.objects.create_user(username="other", password="pass1234")
        self.source = SourceOpportunite.objects.create(
            nom="S", url="https://s.com", type_source="AUTRE"
        )
        self.opp = Opportunite.objects.create(
            titre="Opp",
            description="d",
            type_opportunite="EMPLOI",
            date_publication=date.today(),
            source=self.source,
        )
        self.cand = Candidature.objects.create(
            candidat=self.owner, opportunite=self.opp
        )

    def _make_request(self, user):
        request = MagicMock()
        request.user = user
        return request

    def test_owner_has_permission(self):
        request = self._make_request(self.owner)
        self.assertTrue(
            self.permission.has_object_permission(request, None, self.cand)
        )

    def test_non_owner_denied(self):
        request = self._make_request(self.other)
        self.assertFalse(
            self.permission.has_object_permission(request, None, self.cand)
        )

    def test_unauthenticated_denied(self):
        request = MagicMock()
        request.user = MagicMock()
        request.user.is_authenticated = False
        self.assertFalse(
            self.permission.has_object_permission(request, None, self.cand)
        )


# ═══════════════════════════════════════════════════════════
# VIEW / API TESTS
# ═══════════════════════════════════════════════════════════


class CandidatureViewSetTests(APITestCase):
    """Tests for /api/candidatures/ CRUD and ownership scoping."""

    def setUp(self):
        self.user1 = Utilisateur.objects.create_user(
            username="user1", email="u1@test.com", password="pass1234"
        )
        self.user2 = Utilisateur.objects.create_user(
            username="user2", email="u2@test.com", password="pass1234"
        )
        self.source = SourceOpportunite.objects.create(
            nom="S", url="https://s.com", type_source="SITE_EMPLOI"
        )
        self.opp1 = Opportunite.objects.create(
            titre="Opp1",
            description="d",
            type_opportunite="EMPLOI",
            date_publication=date.today(),
            source=self.source,
        )
        self.opp2 = Opportunite.objects.create(
            titre="Opp2",
            description="d",
            type_opportunite="STAGE",
            date_publication=date.today(),
            source=self.source,
        )
        self.client = APIClient()
        self.url = "/api/candidatures/"

    # ── Authentication ────────────────────────────────────

    def test_list_requires_authentication(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_requires_authentication(self):
        data = {"opportunite": self.opp1.pk, "statut": "VUE"}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # ── List (scoped to user) ─────────────────────────────

    def test_list_only_own_candidatures(self):
        """User1 should only see their own candidatures."""
        self.client.force_authenticate(user=self.user1)
        Candidature.objects.create(candidat=self.user1, opportunite=self.opp1)
        Candidature.objects.create(candidat=self.user2, opportunite=self.opp2)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["opportunite"], self.opp1.pk)

    def test_list_empty_when_no_candidatures(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(self.url)
        self.assertEqual(len(response.data["results"]), 0)

    # ── Create ────────────────────────────────────────────

    def test_create_candidature(self):
        self.client.force_authenticate(user=self.user1)
        data = {"candidat": self.user1.pk, "opportunite": self.opp1.pk, "statut": "VUE"}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # candidat is auto-assigned to the authenticated user
        cand = Candidature.objects.get(pk=response.data["id"])
        self.assertEqual(cand.candidat, self.user1)

    def test_create_candidature_auto_assigns_candidat(self):
        """Even if candidat is passed in body, perform_create overrides it."""
        self.client.force_authenticate(user=self.user1)
        data = {
            "opportunite": self.opp1.pk,
            "candidat": self.user2.pk,  # try to impersonate
            "statut": "VUE",
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        cand = Candidature.objects.get(pk=response.data["id"])
        self.assertEqual(cand.candidat, self.user1)

    def test_create_with_url_source(self):
        self.client.force_authenticate(user=self.user1)
        data = {
            "candidat": self.user1.pk,
            "opportunite": self.opp1.pk,
            "statut": "POSTULEE_EXTERNEMENT",
            "url_source": "https://apply.example.com/job/123",
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["url_source"], "https://apply.example.com/job/123")

    def test_create_duplicate_candidature_rejected(self):
        self.client.force_authenticate(user=self.user1)
        Candidature.objects.create(candidat=self.user1, opportunite=self.opp1)
        data = {"opportunite": self.opp1.pk, "statut": "INTERESSEE"}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ── Retrieve ──────────────────────────────────────────

    def test_retrieve_own_candidature(self):
        self.client.force_authenticate(user=self.user1)
        cand = Candidature.objects.create(candidat=self.user1, opportunite=self.opp1)
        response = self.client.get(f"{self.url}{cand.pk}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], cand.pk)

    def test_retrieve_other_user_candidature_not_found(self):
        """Ownership queryset scoping returns 404 instead of 403."""
        self.client.force_authenticate(user=self.user1)
        cand = Candidature.objects.create(candidat=self.user2, opportunite=self.opp1)
        response = self.client.get(f"{self.url}{cand.pk}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # ── Update ────────────────────────────────────────────

    def test_update_own_candidature_statut(self):
        self.client.force_authenticate(user=self.user1)
        cand = Candidature.objects.create(candidat=self.user1, opportunite=self.opp1)
        response = self.client.patch(
            f"{self.url}{cand.pk}/", {"statut": "INTERESSEE"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        cand.refresh_from_db()
        self.assertEqual(cand.statut, "INTERESSEE")

    def test_update_other_user_candidature_not_found(self):
        self.client.force_authenticate(user=self.user1)
        cand = Candidature.objects.create(candidat=self.user2, opportunite=self.opp1)
        response = self.client.patch(
            f"{self.url}{cand.pk}/", {"statut": "ABANDONNEE"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # ── Delete ────────────────────────────────────────────

    def test_delete_own_candidature(self):
        self.client.force_authenticate(user=self.user1)
        cand = Candidature.objects.create(candidat=self.user1, opportunite=self.opp1)
        response = self.client.delete(f"{self.url}{cand.pk}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Candidature.objects.filter(pk=cand.pk).exists())

    def test_delete_other_user_candidature_not_found(self):
        self.client.force_authenticate(user=self.user1)
        cand = Candidature.objects.create(candidat=self.user2, opportunite=self.opp1)
        response = self.client.delete(f"{self.url}{cand.pk}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # ── Pagination ────────────────────────────────────────

    def test_paginated_response(self):
        self.client.force_authenticate(user=self.user1)
        Candidature.objects.create(candidat=self.user1, opportunite=self.opp1)
        response = self.client.get(self.url)
        self.assertIn("results", response.data)
        self.assertIn("count", response.data)

    # ── Statut transitions ────────────────────────────────

    def test_statut_update_all_valid_transitions(self):
        self.client.force_authenticate(user=self.user1)
        cand = Candidature.objects.create(candidat=self.user1, opportunite=self.opp1)
        for statut_value in StatutSuiviCandidature.values:
            response = self.client.patch(
                f"{self.url}{cand.pk}/", {"statut": statut_value}, format="json"
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            cand.refresh_from_db()
            self.assertEqual(cand.statut, statut_value)
