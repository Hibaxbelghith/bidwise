from django.contrib import admin
from .models import Candidature, Document

@admin.register(Candidature)
class CandidatureAdmin(admin.ModelAdmin):
    list_display = ("candidat", "opportunite", "statut", "date_creation")
    list_filter = ("statut",)

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("type_document", "candidature", "date_upload")
