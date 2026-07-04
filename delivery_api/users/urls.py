from django.urls import path
from .views import (
    RegisterView,
    LoginView,
    UserProfileView,
    LogoutView,
    PasswordChangeView,
    CheckUsernameView,
    CheckEmailView,
    CustomTokenRefreshView
)

urlpatterns = [
    # Autenticación
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('change-password/', PasswordChangeView.as_view(), name='change-password'),
    path('token/refresh/', CustomTokenRefreshView.as_view(), name='token-refresh'),
    
    # Validaciones
    path('check-username/', CheckUsernameView.as_view(), name='check-username'),
    path('check-email/', CheckEmailView.as_view(), name='check-email'),
]