from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Utilisateur, Profil


@receiver(post_save, sender=Utilisateur)
def create_profil_for_user(sender, instance, created, **kwargs):
    """
    Crée automatiquement un profil quand un utilisateur est créé.
    """
    if created:
        Profil.objects.create(utilisateur=instance)


@receiver(post_save, sender=Utilisateur)
def save_profil_for_user(sender, instance, **kwargs):
    """
    Enregistre le profil si l'utilisateur est sauvegardé.
    """
    if hasattr(instance, 'profil'):
        instance.profil.save()
