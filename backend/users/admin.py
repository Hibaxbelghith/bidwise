from django.contrib import admin
from .models import (
    Utilisateur,
    Profil,
    ProfileResume,
    OrganizationProfile,
    OTPChallenge,
    LoginEvent,
)

@admin.register(Utilisateur)
class UtilisateurAdmin(admin.ModelAdmin):
    list_display = ("username", "email", "account_type", "is_admin", "is_staff", "is_active")
    list_filter = ("account_type", "is_admin", "is_staff", "is_active")
    search_fields = ("username", "email")

@admin.register(Profil)
class ProfilAdmin(admin.ModelAdmin):
    list_display = ("prenom", "nom", "niveau_experience")


@admin.register(OrganizationProfile)
class OrganizationProfileAdmin(admin.ModelAdmin):
    list_display = (
        "organization_name",
        "organization_type",
        "first_name",
        "last_name",
        "phone",
        "created_at",
    )
    list_filter = ("organization_type", "created_at")
    search_fields = (
        "organization_name",
        "first_name",
        "last_name",
        "phone",
        "user__email",
    )
    readonly_fields = ("created_at", "updated_at")


@admin.register(ProfileResume)
class ProfileResumeAdmin(admin.ModelAdmin):
    list_display = ("profile", "source_type", "is_active", "parsing_status", "uploaded_at", "parsed_at")
    list_filter = ("source_type", "is_active", "parsing_status")
    readonly_fields = (
        "uploaded_at",
        "parsed_at",
        "parsing_error",
        "parsed_text",
        "resume_text_embedding_source",
        "metadata",
    )

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
