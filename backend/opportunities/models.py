from django.db import models
from users.models import Utilisateur

class TypeOpportunite(models.TextChoices):
    EMPLOI = "EMPLOI", "Emploi"
    STAGE = "STAGE", "Stage"
    PROJET = "PROJET", "Projet"
    FINANCEMENT = "FINANCEMENT", "Financement"
    RECHERCHE = "RECHERCHE", "Recherche"

class StatutOpportunite(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    EXPIREE = "EXPIREE", "Expirée"
    ARCHIVEE = "ARCHIVEE", "Archivée"


class SourceOpportunite(models.Model):
    nom = models.CharField(max_length=150)
    url = models.URLField()
    type_source = models.CharField(
        max_length=50,
        choices=[
            ("SITE_EMPLOI", "Site d'emploi"),
            ("PORTAIL_PROJET", "Portail de projets"),
            ("AUTRE", "Autre"),
        ]
    )

    def __str__(self):
        return self.nom

class Opportunite(models.Model):
    titre = models.CharField(max_length=255)
    description = models.TextField()

    type_opportunite = models.CharField(
        max_length=30,
        choices=TypeOpportunite.choices
    )

    statut = models.CharField(
        max_length=20,
        choices=StatutOpportunite.choices,
        default=StatutOpportunite.ACTIVE
    )

    date_publication = models.DateField()
    date_limite = models.DateField(null=True, blank=True)

    organisation = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="opportunites_publiees"
    )

    source = models.ForeignKey(
        SourceOpportunite,
        on_delete=models.CASCADE,
        related_name="opportunites"
    )

    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["type_opportunite", "statut"]),
        ]
        ordering = ["-date_publication"]

    def __str__(self):
        return self.titre
