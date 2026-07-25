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

# Endpoint de prueba (agregar al final)
class TestRestaurantNotificationView(APIView):
    """
    Endpoint de prueba para enviar notificaciones a restaurantes
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def post(self, request):
        from django.contrib.auth import get_user_model
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        User = get_user_model()
        
        title = request.data.get('title', 'Notificación de prueba')
        message = request.data.get('message', 'Esta es una notificación de prueba para restaurantes')
        
        restaurants = User.objects.filter(user_type='restaurant', is_active=True)
        channel_layer = get_channel_layer()
        
        if not restaurants.exists():
            return Response(
                {'error': 'No hay restaurantes activos'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        notifications_created = []
        for restaurant in restaurants:
            notification = Notification.objects.create(
                user=restaurant,
                type='system',
                title=title,
                message=message,
                data={'test': True},
                priority=0
            )
            notifications_created.append(notification)
            
            # Enviar al grupo general
            async_to_sync(channel_layer.group_send)(
                f'notifications_{restaurant.id}',
                {
                    'type': 'notification_message',
                    'data': {
                        'id': notification.id,
                        'title': notification.title,
                        'message': notification.message,
                        'type': notification.type,
                        'created_at': notification.created_at.isoformat(),
                        'data': notification.data,
                        'is_read': notification.is_read,
                    }
                }
            )
            
            # Enviar al grupo específico de restaurante
            async_to_sync(channel_layer.group_send)(
                f'restaurant_{restaurant.id}',
                {
                    'type': 'notification_message',
                    'data': {
                        'id': notification.id,
                        'title': notification.title,
                        'message': notification.message,
                        'type': notification.type,
                        'created_at': notification.created_at.isoformat(),
                        'data': notification.data,
                        'is_read': notification.is_read,
                    }
                }
            )
        
        return Response({
            'message': f'Notificación enviada a {restaurants.count()} restaurantes',
            'count': restaurants.count(),
            'restaurants': [r.username for r in restaurants]
        })

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
]