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
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    competences = models.TextField(blank=True)
    domaines_interet = models.TextField(blank=True)
    niveau_experience = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.prenom} {self.nom}"
