from django.urls import path
from .views import (
    interest_suggestions,
    profile_detail,
    profile_resume,
    role_suggestions,
    skill_suggestions,
)

urlpatterns = [
    path('me/', profile_detail, name='profile_detail'),
    path('resume/', profile_resume, name='profile_resume'),
    path('skills/suggest/', skill_suggestions, name='profile_skill_suggestions'),
    path('roles/suggest/', role_suggestions, name='profile_role_suggestions'),
    path('interests/suggest/', interest_suggestions, name='profile_interest_suggestions'),
]
