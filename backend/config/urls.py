"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView
from users.views import request_otp, verify_otp, logout_view
from users.google_auth import google_authenticate


urlpatterns = [
    path('admin/', admin.site.urls),
    # Passwordless OTP authentication
    path('api/auth/passwordless/request/', request_otp, name='otp_request'),
    path('api/auth/passwordless/verify/', verify_otp, name='otp_verify'),
    # Google OAuth2
    path('api/auth/google/', google_authenticate, name='google_auth'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/logout/', logout_view, name='auth_logout'),
    path('api/profile/', include('users.urls')),
    path('api/', include('opportunities.urls')),
    path('api/', include('applications.urls')),
]
