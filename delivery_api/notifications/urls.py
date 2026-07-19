from django.urls import path
from .views import (
    NotificationListView,
    UnreadNotificationsView,
    NotificationDetailView,
    MarkNotificationReadView,
    MarkAllNotificationsReadView,
    UnreadCountView,
    NotificationPreferenceView,
    DeviceTokenListCreateView,
    DeviceTokenDeleteView,
    AdminNotificationCreateView,
    AdminBroadcastNotificationView,
    AdminNotificationStatsView,
)

urlpatterns = [
    # =============================================
    # NOTIFICACIONES DEL USUARIO
    # =============================================
    path('', NotificationListView.as_view(), name='notification-list'),
    path('unread/', UnreadNotificationsView.as_view(), name='notification-unread'),
    path('unread/count/', UnreadCountView.as_view(), name='notification-unread-count'),
    path('<int:pk>/', NotificationDetailView.as_view(), name='notification-detail'),
    path('<int:pk>/read/', MarkNotificationReadView.as_view(), name='notification-mark-read'),
    path('read-all/', MarkAllNotificationsReadView.as_view(), name='notification-read-all'),
    
    # =============================================
    # PREFERENCIAS
    # =============================================
    path('preferences/', NotificationPreferenceView.as_view(), name='notification-preferences'),
    
    # =============================================
    # TOKENS DE DISPOSITIVOS (PUSH)
    # =============================================
    path('devices/', DeviceTokenListCreateView.as_view(), name='device-token-list'),
    path('devices/<int:pk>/', DeviceTokenDeleteView.as_view(), name='device-token-delete'),
    
    # =============================================
    # ADMINISTRACIÓN (SOLO ADMIN)
    # =============================================
    path('admin/create/', AdminNotificationCreateView.as_view(), name='admin-notification-create'),
    path('admin/broadcast/', AdminBroadcastNotificationView.as_view(), name='admin-notification-broadcast'),
    path('admin/stats/', AdminNotificationStatsView.as_view(), name='admin-notification-stats'),
]