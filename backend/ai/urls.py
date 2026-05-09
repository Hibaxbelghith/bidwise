from django.urls import path

from .views import recommendations_view


urlpatterns = [
    path("recommendations/", recommendations_view, name="recommendations"),
]
