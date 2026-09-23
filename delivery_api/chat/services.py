from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.contrib.auth import get_user_model

User = get_user_model()


class ChatNotificationService:
    """
    Servicio para enviar notificaciones de chat (WebSocket + Push)
    """
    
    @staticmethod
    def send_to_conversation(conversation_id, event_type, data):
        """
        Enviar un evento a todos los participantes de una conversación vía WebSocket
        """
        channel_layer = get_channel_layer()
        group_name = f'chat_{conversation_id}'
        
        try:
            async_to_sync(channel_layer.group_send)(
                group_name,
                {
                    'type': event_type,
                    'data': data,
                }
            )
        except Exception as e:
            print(f"❌ Error enviando a conversación {conversation_id}: {e}")
    
    @staticmethod
    def notify_new_message(conversation, message, exclude_user=None):
        """
        Notificar a los participantes sobre un nuevo mensaje
        """
        # Enviar por WebSocket
        ChatNotificationService.send_to_conversation(
            conversation_id=conversation.id,
            event_type='new_message',
            data={
                'conversation_id': conversation.id,
                'message': message,
            }
        )
        
        # Enviar push notifications a los que no están conectados
        try:
            from notifications.push_service import PushNotificationService
            
            participants = conversation.participants.filter(is_active=True)
            
            for participant in participants:
                if exclude_user and participant.user.id == exclude_user.id:
                    continue
                
                PushNotificationService.send_push_notification(
                    user_id=participant.user.id,
                    title=f"💬 Nuevo mensaje - Pedido #{conversation.order.id}",
                    body=message[:100] if isinstance(message, str) else "Tienes un nuevo mensaje",
                    data={
                        'type': 'chat_message',
                        'conversation_id': conversation.id,
                        'order_id': conversation.order.id,
                        'screen': 'chat',
                    }
                )
        except Exception as e:
            print(f"⚠️ Error enviando push: {e}")
    
    @staticmethod
    def notify_support_joined(conversation, support_user):
        """
        Notificar que un agente de soporte se unió
        """
        ChatNotificationService.send_to_conversation(
            conversation_id=conversation.id,
            event_type='support_joined',
            data={
                'conversation_id': conversation.id,
                'support_user': {
                    'id': support_user.id,
                    'name': support_user.get_full_name() or support_user.username,
                }
            }
        )
    
    @staticmethod
    def notify_user_typing(conversation_id, user, is_typing=True):
        """
        Notificar que un usuario está escribiendo
        """
        ChatNotificationService.send_to_conversation(
            conversation_id=conversation_id,
            event_type='user_typing',
            data={
                'user_id': user.id,
                'username': user.get_full_name() or user.username,
                'is_typing': is_typing,
            }
        )