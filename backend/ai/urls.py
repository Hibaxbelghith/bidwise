from django.urls import path

from .views import (
    opportunity_assistant_question_view,
    recommendations_view,
    resume_match_action_view,
    resume_match_view,
)


urlpatterns = [
    path("recommendations/", recommendations_view, name="recommendations"),
    path("opportunities/<int:opportunity_id>/resume-match/", resume_match_view, name="resume-match"),
    path(
        "opportunities/<int:opportunity_id>/resume-match/actions/",
        resume_match_action_view,
        name="resume-match-actions",
    ),
    path(
        "opportunities/<int:opportunity_id>/assistant/questions/",
        opportunity_assistant_question_view,
        name="opportunity-assistant-questions",
    ),
]
