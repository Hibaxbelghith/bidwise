from django.db import models
from users.models import Utilisateur


class TypeNotification(models.TextChoices):
    RECOMMANDATION = "RECOMMANDATION", "Nouvelle recommandation"
    RAPPEL_ECHEANCE = "RAPPEL_ECHEANCE", "Rappel d'échéance"
    INFO_SYSTEME = "INFO_SYSTEME", "Information système"
    ERREUR_SOURCE = "ERREUR_SOURCE", "Erreur de source"


class Notification(models.Model):
    utilisateur = models.ForeignKey(
        Utilisateur,
        on_delete=models.CASCADE,
        related_name="notifications"
    )

    type_notification = models.CharField(
        max_length=30,
        choices=TypeNotification.choices
    )

    message = models.TextField()

    lu = models.BooleanField(default=False)

    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.type_notification} - {self.utilisateur}"
