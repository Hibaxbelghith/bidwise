from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    CandidatureViewSet,
    apply_to_organization_opportunity,
    list_candidate_applications,
    register_external_application_click,
    upload_application_cover_letter,
    update_candidate_external_application_status,
    withdraw_candidate_application,
)


router = DefaultRouter()
router.register(r"candidatures", CandidatureViewSet, basename="candidature")

urlpatterns = [
    path(
        "me/applications/",
        list_candidate_applications,
        name="list_candidate_applications",
    ),
    path(
        "me/applications/<int:application_id>/withdraw/",
        withdraw_candidate_application,
        name="withdraw_candidate_application",
    ),
    path(
        "me/applications/<int:application_id>/external-status/",
        update_candidate_external_application_status,
        name="update_candidate_external_application_status",
    ),
    path(
        "applications/cover-letter-upload/",
        upload_application_cover_letter,
        name="upload_application_cover_letter",
    ),
    path(
        "opportunities/<int:opportunity_id>/apply/",
        apply_to_organization_opportunity,
        name="apply_to_organization_opportunity",
    ),
    path(
        "opportunities/<int:opportunity_id>/external-apply-click/",
        register_external_application_click,
        name="register_external_application_click",
    ),
]
urlpatterns += router.urls
