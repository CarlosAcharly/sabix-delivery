from django.urls import path
from .views import (
    # Autenticación
    RegisterView,
    LoginView,
    UserProfileView,
    LogoutView,
    PasswordChangeView,
    CheckUsernameView,
    CheckEmailView,
    CustomTokenRefreshView,
    APIRootView,
    
    # Administración de usuarios (NUEVAS)
    AdminUserListView,
    AdminUserDetailView,
    AdminUserToggleActiveView,
    AdminUserToggleVerifyView,
    AdminUserStatsView,
    AdminUserFilterView,
)

urlpatterns = [
    # =============================================
    # RAÍZ DE LA API
    # =============================================
    path('', APIRootView.as_view(), name='api-root'),
    
    # =============================================
    # AUTENTICACIÓN
    # =============================================
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('change-password/', PasswordChangeView.as_view(), name='change-password'),
    path('token/refresh/', CustomTokenRefreshView.as_view(), name='token-refresh'),
    
    # =============================================
    # VALIDACIONES
    # =============================================
    path('check-username/', CheckUsernameView.as_view(), name='check-username'),
    path('check-email/', CheckEmailView.as_view(), name='check-email'),
    
    # =============================================
    # ADMINISTRACIÓN DE USUARIOS (SOLO ADMIN)
    # =============================================
    path('admin/users/', AdminUserListView.as_view(), name='admin-user-list'),
    path('admin/users/filter/', AdminUserFilterView.as_view(), name='admin-user-filter'),
    path('admin/users/<int:id>/', AdminUserDetailView.as_view(), name='admin-user-detail'),
    path('admin/users/<int:user_id>/toggle-active/', AdminUserToggleActiveView.as_view(), name='admin-user-toggle-active'),
    path('admin/users/<int:user_id>/toggle-verify/', AdminUserToggleVerifyView.as_view(), name='admin-user-toggle-verify'),
    path('admin/stats/', AdminUserStatsView.as_view(), name='admin-stats'),
]