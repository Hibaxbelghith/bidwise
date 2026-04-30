from django.contrib import admin
from .models import Utilisateur, Profil, OTPChallenge, LoginEvent

@admin.register(Utilisateur)
class UtilisateurAdmin(admin.ModelAdmin):
    list_display = ("username", "email", "is_admin", "is_staff", "is_active")
    list_filter = ("is_admin", "is_staff", "is_active")
    search_fields = ("username", "email")

@admin.register(Profil)
class ProfilAdmin(admin.ModelAdmin):
    list_display = ("prenom", "nom", "niveau_experience")

@admin.register(OTPChallenge)
class OTPChallengeAdmin(admin.ModelAdmin):
    list_display = ("email", "attempts", "is_used", "created_at", "expires_at")
    list_filter = ("is_used",)
    search_fields = ("email",)
    readonly_fields = ("otp_hash", "created_at")


@admin.register(LoginEvent)
class LoginEventAdmin(admin.ModelAdmin):
    list_display = ("user", "ip_address", "device_type", "created_at")
    list_filter = ("device_type",)
    search_fields = ("user__email", "ip_address")
    readonly_fields = ("created_at",)
