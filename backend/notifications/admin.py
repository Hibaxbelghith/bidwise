from django.contrib import admin
from .models import Notification, RecommendationNotificationDispatch

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("utilisateur", "type_notification", "lu", "date_creation")
    list_filter = ("type_notification", "lu")


@admin.register(RecommendationNotificationDispatch)
class RecommendationNotificationDispatchAdmin(admin.ModelAdmin):
    list_display = ("utilisateur", "opportunite", "sent_at")
    search_fields = ("utilisateur__email", "opportunite__titre", "opportunite__organisation_nom")
