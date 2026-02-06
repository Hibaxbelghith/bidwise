from django.urls import path
from .views import profile_detail

urlpatterns = [
    path('me/', profile_detail, name='profile_detail'),
]
