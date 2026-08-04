from django.urls import path
from .views import FCMDeviceTokenView, FCMDeviceTokenListDeleteView

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
    TestRestaurantNotificationView,
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
    path('admin/test-restaurant/', TestRestaurantNotificationView.as_view(), name='test-restaurant-notification'),

    # =============================================
    # FIREBASE PUSH NOTIFICATIONS
    # =============================================
    path('fcm/device/', FCMDeviceTokenView.as_view(), name='fcm-device'),
    path('fcm/devices/', FCMDeviceTokenListDeleteView.as_view(), name='fcm-devices'),
    path('fcm/devices/<int:token_id>/', FCMDeviceTokenListDeleteView.as_view(), name='fcm-device-delete'),
]