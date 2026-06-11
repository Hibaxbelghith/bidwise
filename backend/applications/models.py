import secrets
from pathlib import Path

from django.db import models

from opportunities.models import Opportunite
from users.models import ProfileResume, Utilisateur


class StatutSuiviCandidature(models.TextChoices):
    VUE = "VUE", "Vue"
    INTERESSEE = "INTERESSEE", "Intéressée"
    POSTULEE_EXTERNEMENT = "POSTULEE_EXTERNEMENT", "Postulée (site externe)"
    ABANDONNEE = "ABANDONNEE", "Abandonnée"
    SUBMITTED = "SUBMITTED", "Submitted"
    VIEWED_BY_ORGANIZATION = "VIEWED_BY_ORGANIZATION", "Viewed by organization"
    SHORTLISTED = "SHORTLISTED", "Shortlisted"
    REJECTED = "REJECTED", "Rejected"
    WITHDRAWN = "WITHDRAWN", "Withdrawn"
    EXTERNAL_CLICKED = "EXTERNAL_CLICKED", "External application opened"
    EXTERNAL_APPLIED_CONFIRMED = (
        "EXTERNAL_APPLIED_CONFIRMED",
        "External application confirmed",
    )
    EXTERNAL_REMIND_LATER = "EXTERNAL_REMIND_LATER", "External reminder requested"


INTERNAL_APPLICATION_STATUSES = {
    StatutSuiviCandidature.SUBMITTED,
    StatutSuiviCandidature.VIEWED_BY_ORGANIZATION,
    StatutSuiviCandidature.SHORTLISTED,
    StatutSuiviCandidature.REJECTED,
    StatutSuiviCandidature.WITHDRAWN,
}

EXTERNAL_APPLICATION_STATUSES = {
    StatutSuiviCandidature.EXTERNAL_CLICKED,
    StatutSuiviCandidature.EXTERNAL_APPLIED_CONFIRMED,
    StatutSuiviCandidature.EXTERNAL_REMIND_LATER,
}


def application_cover_letter_upload_to(instance, filename):
    """Kept for historical migration 0003; new applications store the uploaded URL."""
    extension = Path(filename or "").suffix.lower()
    candidate_id = instance.candidat_id or "unknown"
    return f"application_cover_letters/{candidate_id}/{secrets.token_hex(16)}{extension}"


class Candidature(models.Model):
    candidat = models.ForeignKey(
        Utilisateur,
        on_delete=models.CASCADE,
        related_name="candidatures",
    )
    opportunite = models.ForeignKey(
        Opportunite,
        on_delete=models.CASCADE,
        related_name="candidatures",
    )
    statut = models.CharField(
        max_length=30,
        choices=StatutSuiviCandidature.choices,
        default=StatutSuiviCandidature.VUE,
    )
    url_source = models.URLField(
        help_text="Lien vers la page externe de candidature",
        null=True,
        blank=True,
    )
    cv = models.ForeignKey(
        ProfileResume,
        on_delete=models.PROTECT,
        related_name="applications",
        null=True,
        blank=True,
    )
    cover_letter_url = models.URLField(max_length=1000, blank=True, default="")
    contact_email = models.EmailField(blank=True, default="")
    contact_phone = models.CharField(max_length=20, blank=True, default="")
    submitted_at = models.DateTimeField(null=True, blank=True, db_index=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    derniere_mise_a_jour = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["candidat", "opportunite"]

    def __str__(self):
        return f"{self.candidat} - {self.opportunite}"

    @property
    def is_internal_workflow(self):
        return self.statut in INTERNAL_APPLICATION_STATUSES

    @property
    def is_external_workflow(self):
        return self.statut in EXTERNAL_APPLICATION_STATUSES


class TypeDocument(models.TextChoices):
    CV = "CV", "CV"
    LETTRE_MOTIVATION = "LETTRE", "Lettre de motivation"
    DOSSIER_PROJET = "DOSSIER", "Dossier de projet"
    AUTRE = "AUTRE", "Autre"


class Document(models.Model):
    candidature = models.ForeignKey(
        Candidature,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    type_document = models.CharField(
        max_length=20,
        choices=TypeDocument.choices,
    )
    fichier = models.FileField(upload_to="documents/")
    date_upload = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.type_document} - {self.candidature}"
