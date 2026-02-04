"""Authentication URL patterns."""
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView
from ..views import (
    CustomTokenObtainPairView,
    RegisterView,
    LogoutView,
    ChangePasswordView,
)

urlpatterns = [
    path('login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('register/', RegisterView.as_view(), name='register'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),
]
