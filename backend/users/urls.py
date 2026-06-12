from django.urls import path
from .views import (
    apply_resume_profile_suggestions,
    interest_suggestions,
    organization_logo_upload,
    organization_profile_detail,
    profile_detail,
    profile_resume,
    role_suggestions,
    skill_suggestions,
)

urlpatterns = [
    path('me/', profile_detail, name='profile_detail'),
    path('organization/', organization_profile_detail, name='organization_profile_detail'),
    path('organization/logo/', organization_logo_upload, name='organization_logo_upload'),
    path('resume/', profile_resume, name='profile_resume'),
    path('resume/apply-suggestions/', apply_resume_profile_suggestions, name='apply_resume_profile_suggestions'),
    path('skills/suggest/', skill_suggestions, name='profile_skill_suggestions'),
    path('roles/suggest/', role_suggestions, name='profile_role_suggestions'),
    path('interests/suggest/', interest_suggestions, name='profile_interest_suggestions'),
]
