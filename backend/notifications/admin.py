from django.contrib import admin
from .models import Notification

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("utilisateur", "type_notification", "lu", "date_creation")
    list_filter = ("type_notification", "lu")
