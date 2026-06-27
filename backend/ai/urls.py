from django.urls import path

from .views import (
    opportunity_assistant_question_view,
    recommendations_view,
    resume_match_ats_cv_export_view,
    resume_match_action_view,
    resume_match_cover_letter_export_view,
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
    path(
        "opportunities/<int:opportunity_id>/resume-match/export-ats-cv/",
        resume_match_ats_cv_export_view,
        name="resume-match-export-ats-cv",
    ),
    path(
        "opportunities/<int:opportunity_id>/resume-match/export-cover-letter/",
        resume_match_cover_letter_export_view,
        name="resume-match-export-cover-letter",
    ),
]
