from django.contrib import admin
from .models import Opportunite, SourceOpportunite

@admin.register(SourceOpportunite)
class SourceAdmin(admin.ModelAdmin):
    list_display = ("nom", "type_source")

@admin.register(Opportunite)
class OpportuniteAdmin(admin.ModelAdmin):
    list_display = ("titre", "type_opportunite", "statut", "date_publication")
    list_filter = ("type_opportunite", "statut")
    search_fields = ("titre",)
