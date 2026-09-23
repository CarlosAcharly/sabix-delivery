import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from .models import Conversation, ConversationParticipant, Message, MessageRead


class ChatConsumer(AsyncWebsocketConsumer):
    """
    Consumer para el chat en tiempo real
    """
    async def connect(self):
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.group_name = f'chat_{self.conversation_id}'
        self.user = self.scope.get('user')
        
        # Verificar autenticación
        if not self.user or not self.user.is_authenticated:
            print("❌ Usuario no autenticado")
            await self.close(code=4401)
            return
        
        # Verificar que el usuario sea participante
        is_participant = await self.check_participant()
        if not is_participant:
            print(f"❌ Usuario {self.user.username} no es participante de conversación {self.conversation_id}")
            await self.close(code=4403)
            return
        
        # Unirse al grupo
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Marcar mensajes como leídos
        await self.mark_messages_as_read()
        
        # Notificar al grupo que el usuario está en línea
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'user_online',
                'user_id': self.user.id,
                'username': self.user.get_full_name() or self.user.username,
            }
        )
        
        print(f"✅ Chat conectado - Usuario: {self.user.username} (ID: {self.user.id}) - Conversación: {self.conversation_id}")
    
    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            # Notificar que el usuario se desconectó
            try:
                await self.channel_layer.group_send(
                    self.group_name,
                    {
                        'type': 'user_offline',
                        'user_id': self.user.id,
                        'username': self.user.get_full_name() or self.user.username,
                    }
                )
            except Exception:
                pass
            
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )
        
        print(f"🔌 Chat desconectado - Usuario: {getattr(self.user, 'username', 'unknown')} - Código: {close_code}")
    
    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            action = data.get('action')
            
            if action == 'send_message':
                await self.handle_send_message(data)
            
            elif action == 'mark_read':
                message_id = data.get('message_id')
                if message_id:
                    await self.mark_message_as_read(message_id)
            
            elif action == 'typing':
                is_typing = data.get('is_typing', True)
                await self.channel_layer.group_send(
                    self.group_name,
                    {
                        'type': 'user_typing',
                        'user_id': self.user.id,
                        'username': self.user.get_full_name() or self.user.username,
                        'is_typing': is_typing,
                    }
                )
            
            elif action == 'ping':
                await self.send(text_data=json.dumps({'type': 'pong'}))
        
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'JSON inválido'
            }))
        except Exception as e:
            print(f"❌ Error en receive: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': str(e)
            }))
    
    async def handle_send_message(self, data):
        """Manejar envío de mensaje"""
        content = data.get('content', '').strip()
        if not content:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'El contenido es requerido'
            }))
            return
        
        message_type = data.get('message_type', 'text')
        metadata = data.get('metadata', {})
        reply_to_id = data.get('reply_to_id')
        
        # Guardar mensaje
        message = await self.save_message(
            content=content,
            message_type=message_type,
            metadata=metadata,
            reply_to_id=reply_to_id
        )
        
        # Enviar a todos los participantes
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'chat_message',
                'message': message,
            }
        )
        
        # Enviar notificaciones push
        await self.send_push_notifications(message)
    
    # =============================================
    # HANDLERS DE GRUPO
    # =============================================
    
    async def chat_message(self, event):
        """Enviar mensaje al WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'new_message',
            'message': event['message'],
        }))
    
    async def user_typing(self, event):
        """Notificar que un usuario está escribiendo"""
        # No enviar al mismo usuario
        if event['user_id'] == self.user.id:
            return
        
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'user_id': event['user_id'],
            'username': event['username'],
            'is_typing': event['is_typing'],
        }))
    
    async def user_online(self, event):
        """Notificar que un usuario está en línea"""
        if event['user_id'] == self.user.id:
            return
        
        await self.send(text_data=json.dumps({
            'type': 'user_online',
            'user_id': event['user_id'],
            'username': event['username'],
        }))
    
    async def user_offline(self, event):
        """Notificar que un usuario se desconectó"""
        if event['user_id'] == self.user.id:
            return
        
        await self.send(text_data=json.dumps({
            'type': 'user_offline',
            'user_id': event['user_id'],
            'username': event['username'],
        }))
    
    # =============================================
    # MÉTODOS DE BASE DE DATOS
    # =============================================
    
    @database_sync_to_async
    def check_participant(self):
        """Verificar si el usuario es participante"""
        # Admin/Soporte: verificar asignación
        if self.user.user_type == 'admin' or self.user.is_superuser:
            return ConversationParticipant.objects.filter(
                conversation_id=self.conversation_id,
                user=self.user,
                is_active=True
            ).exists()
        
        # Otros usuarios: verificar participación
        return ConversationParticipant.objects.filter(
            conversation_id=self.conversation_id,
            user=self.user,
            is_active=True
        ).exists()
    
    @database_sync_to_async
    def save_message(self, content, message_type, metadata, reply_to_id=None):
        """Guardar mensaje en la base de datos"""
        conversation = Conversation.objects.get(id=self.conversation_id)
        
        reply_to = None
        if reply_to_id:
            try:
                reply_to = Message.objects.get(id=reply_to_id, conversation=conversation)
            except Message.DoesNotExist:
                pass
        
        message = Message.objects.create(
            conversation=conversation,
            sender=self.user,
            content=content,
            message_type=message_type,
            metadata=metadata,
            reply_to=reply_to
        )
        
        # Marcar como leído por el emisor
        MessageRead.objects.create(message=message, user=self.user)
        
        # Actualizar last_read_at
        ConversationParticipant.objects.filter(
            conversation=conversation,
            user=self.user
        ).update(last_read_at=timezone.now())
        
        # Actualizar updated_at de la conversación
        conversation.save(update_fields=['updated_at'])
        
        return {
            'id': message.id,
            'conversation_id': conversation.id,
            'sender_id': self.user.id,
            'sender_name': self.user.get_full_name() or self.user.username,
            'sender_type': self.user.user_type,
            'content': message.content,
            'message_type': message.message_type,
            'metadata': message.metadata,
            'reply_to': {
                'id': reply_to.id,
                'content': reply_to.content[:100],
                'sender_name': reply_to.sender.get_full_name() or reply_to.sender.username,
            } if reply_to else None,
            'created_at': message.created_at.isoformat(),
        }
    
    @database_sync_to_async
    def mark_message_as_read(self, message_id):
        """Marcar un mensaje como leído"""
        try:
            message = Message.objects.get(
                id=message_id,
                conversation_id=self.conversation_id
            )
            MessageRead.objects.get_or_create(message=message, user=self.user)
        except Message.DoesNotExist:
            pass
    
    @database_sync_to_async
    def mark_messages_as_read(self):
        """Marcar todos los mensajes como leídos"""
        conversation = Conversation.objects.get(id=self.conversation_id)
        
        # Actualizar last_read_at
        ConversationParticipant.objects.filter(
            conversation=conversation,
            user=self.user
        ).update(last_read_at=timezone.now())
        
        # Crear registros de lectura para mensajes no leídos
        unread_messages = Message.objects.filter(
            conversation=conversation,
            is_deleted=False
        ).exclude(
            reads__user=self.user
        ).exclude(sender=self.user)
        
        for message in unread_messages:
            MessageRead.objects.get_or_create(message=message, user=self.user)
    
    @database_sync_to_async
    def send_push_notifications(self, message):
        """Enviar notificaciones push a los participantes"""
        try:
            from notifications.push_service import PushNotificationService
            
            conversation = Conversation.objects.get(id=self.conversation_id)
            participants = conversation.participants.filter(is_active=True).exclude(user=self.user)
            
            for participant in participants:
                PushNotificationService.send_push_notification(
                    user_id=participant.user.id,
                    title=f"💬 Nuevo mensaje - Pedido #{conversation.order.id}",
                    body=f"{self.user.get_full_name() or self.user.username}: {message['content'][:100]}",
                    data={
                        'type': 'chat_message',
                        'conversation_id': conversation.id,
                        'order_id': conversation.order.id,
                        'screen': 'chat',
                    }
                )
        except Exception as e:
            print(f"⚠️ Error enviando push: {e}")