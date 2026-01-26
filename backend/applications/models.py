from django.db import models
from users.models import Utilisateur
from opportunities.models import Opportunite

class StatutSuiviCandidature(models.TextChoices):
    VUE = "VUE", "Vue"
    INTERESSEE = "INTERESSEE", "Intéressée"
    POSTULEE_EXTERNEMENT = "POSTULEE_EXTERNEMENT", "Postulée (site externe)"
    ABANDONNEE = "ABANDONNEE", "Abandonnée"


class Candidature(models.Model):
    candidat = models.ForeignKey(
        Utilisateur,
        on_delete=models.CASCADE,
        related_name="candidatures"
    )

    opportunite = models.ForeignKey(
        Opportunite,
        on_delete=models.CASCADE,
        related_name="candidatures"
    )

    statut = models.CharField(
        max_length=30,
        choices=StatutSuiviCandidature.choices,
        default=StatutSuiviCandidature.VUE
    )

    url_source = models.URLField(
    help_text="Lien vers la page externe de candidature",
    null=True,
    blank=True
    )

    date_creation = models.DateTimeField(auto_now_add=True)

    derniere_mise_a_jour = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['candidat', 'opportunite']

    def __str__(self):
        return f"{self.candidat} - {self.opportunite}"

class TypeDocument(models.TextChoices):
    CV = "CV", "CV"
    LETTRE_MOTIVATION = "LETTRE", "Lettre de motivation"
    DOSSIER_PROJET = "DOSSIER", "Dossier de projet"
    AUTRE = "AUTRE", "Autre"

class Document(models.Model):
    candidature = models.ForeignKey(
        Candidature,
        on_delete=models.CASCADE,
        related_name="documents"
    )

    type_document = models.CharField(
        max_length=20,
        choices=TypeDocument.choices
    )

    fichier = models.FileField(upload_to="documents/")

    date_upload = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.type_document} - {self.candidature}"
