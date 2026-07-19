from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Notification, DeviceToken
import json

class NotificationService:
    """
    Servicio para enviar notificaciones en tiempo real
    """
    
    @staticmethod
    def send_to_user(user_id, notification_data):
        """
        Enviar notificación a un usuario específico via WebSocket
        """
        channel_layer = get_channel_layer()
        
        async_to_sync(channel_layer.group_send)(
            f'notifications_{user_id}',
            {
                'type': 'notification_message',
                'data': notification_data
            }
        )
    
    @staticmethod
    def update_unread_count(user_id):
        """
        Actualizar el contador de notificaciones no leídas
        """
        from .models import Notification
        
        count = Notification.objects.filter(
            user_id=user_id,
            is_read=False
        ).count()
        
        channel_layer = get_channel_layer()
        
        async_to_sync(channel_layer.group_send)(
            f'notifications_{user_id}',
            {
                'type': 'notification_count_update',
                'count': count
            }
        )
    
    @staticmethod
    def send_push_notification(user_id, title, body, data=None):
        """
        Enviar notificación push a los dispositivos del usuario
        """
        # Aquí iría la integración con FCM/APNS
        pass

# Señal para enviar notificaciones en tiempo real
def send_notification_on_create(sender, instance, created, **kwargs):
    if created:
        from notifications.services import NotificationService
        
        # Enviar via WebSocket
        NotificationService.send_to_user(
            instance.user.id,
            {
                'id': instance.id,
                'title': instance.title,
                'message': instance.message,
                'type': instance.type,
                'created_at': instance.created_at.isoformat(),
                'data': instance.data
            }
        )
        
        # Actualizar contador de no leídas
        NotificationService.update_unread_count(instance.user.id)

# Conectar la señal
from django.db.models.signals import post_save
post_save.connect(send_notification_on_create, sender=Notification)