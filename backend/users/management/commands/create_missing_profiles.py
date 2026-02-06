from django.core.management.base import BaseCommand
from users.models import Utilisateur, Profil


class Command(BaseCommand):
    help = "Crée les profils manquants pour les utilisateurs existants"

    def handle(self, *args, **options):
        count = 0
        for user in Utilisateur.objects.all():
            if not hasattr(user, 'profil'):
                Profil.objects.create(utilisateur=user)
                count += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'✅ {count} profil(s) créé(s)')
        )
