from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Notification, DeviceToken
import json
import logging

logger = logging.getLogger(__name__)

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
        group_name = f'notifications_{user_id}'
        
        try:
            async_to_sync(channel_layer.group_send)(
                group_name,
                {
                    'type': 'notification_message',
                    'data': notification_data
                }
            )
            logger.debug(f"✅ Notificación enviada al grupo {group_name}")
            return True
        except Exception as e:
            logger.error(f"❌ Error enviando al grupo {group_name}: {e}")
            return False
    
    @staticmethod
    def send_to_role(user_id, role, notification_data):
        """
        Enviar notificación a un grupo específico por rol
        """
        channel_layer = get_channel_layer()
        role_group = f'{role}_{user_id}'
        
        try:
            async_to_sync(channel_layer.group_send)(
                role_group,
                {
                    'type': 'notification_message',
                    'data': notification_data
                }
            )
            logger.debug(f"✅ Notificación enviada al grupo {role_group}")
            return True
        except Exception as e:
            logger.error(f"❌ Error enviando al grupo {role_group}: {e}")
            return False
    
    @staticmethod
    def update_unread_count(user_id):
        """
        Actualizar el contador de notificaciones no leídas
        """
        from .models import Notification
        
        try:
            count = Notification.objects.filter(
                user_id=user_id,
                is_read=False
            ).count()
            
            channel_layer = get_channel_layer()
            group_name = f'notifications_{user_id}'
            
            async_to_sync(channel_layer.group_send)(
                group_name,
                {
                    'type': 'notification_count_update',
                    'count': count
                }
            )
            logger.debug(f"✅ Contador actualizado para usuario {user_id}: {count}")
            return True
        except Exception as e:
            logger.error(f"❌ Error actualizando contador para usuario {user_id}: {e}")
            return False
    
    @staticmethod
    def send_push_notification(user_id, title, body, data=None):
        """
        Enviar notificación push a los dispositivos del usuario
        """
        # TODO: Integrar con FCM/APNS
        logger.info(f"📱 Push notification para usuario {user_id}: {title}")
        pass


# Señal para enviar notificaciones en tiempo real
def send_notification_on_create(sender, instance, created, **kwargs):
    if created:
        from notifications.services import NotificationService
        
        notification_data = {
            'id': instance.id,
            'title': instance.title,
            'message': instance.message,
            'type': instance.type,
            'created_at': instance.created_at.isoformat(),
            'data': instance.data,
            'is_read': instance.is_read,
            'priority': instance.priority,
        }
        
        # Enviar via WebSocket al grupo general
        NotificationService.send_to_user(instance.user.id, notification_data)
        
        # Enviar al grupo específico del rol
        role = instance.user.user_type
        NotificationService.send_to_role(instance.user.id, role, notification_data)
        
        # Actualizar contador de no leídas
        NotificationService.update_unread_count(instance.user.id)
        
        logger.info(f"📨 Notificación #{instance.id} enviada al usuario {instance.user.id} (tipo: {role})")

# Conectar la señal
from django.db.models.signals import post_save
post_save.connect(send_notification_on_create, sender=Notification)