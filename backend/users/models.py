from django.db import models
from django.contrib.auth.models import AbstractUser

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

    def __str__(self):
        return f"{self.prenom} {self.nom}" if self.prenom and self.nom else f"Profil #{self.id}"
