import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken
from .models import Notification

User = get_user_model()

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user_id = self.scope['url_route']['kwargs']['user_id']
        
        # =============================================
        # AUTENTICACIÓN POR TOKEN EN URL
        # =============================================
        query_string = self.scope['query_string'].decode()
        token = None
        
        # Extraer token de la query string
        for param in query_string.split('&'):
            if param.startswith('token='):
                token = param.split('=')[1]
                break
        
        # Verificar token
        if token:
            try:
                access_token = AccessToken(token)
                user_id_from_token = access_token.payload.get('user_id')
                
                if str(user_id_from_token) == self.user_id:
                    self.user = await database_sync_to_async(User.objects.get)(id=user_id_from_token)
                else:
                    print(f"❌ ID de usuario no coincide: {user_id_from_token} vs {self.user_id}")
                    await self.close()
                    return
            except Exception as e:
                print(f"❌ Error de autenticación WebSocket: {e}")
                await self.close()
                return
        else:
            print("❌ No se proporcionó token")
            await self.close()
            return
        
        # =============================================
        # GRUPOS POR ROL
        # =============================================
        self.user_group = f'notifications_{self.user_id}'
        self.role_group = None
        
        user_type = self.user.user_type
        
        if user_type == 'restaurant':
            self.role_group = f'restaurant_{self.user_id}'
        elif user_type == 'delivery':
            self.role_group = f'delivery_{self.user_id}'
        elif user_type == 'client':
            self.role_group = f'client_{self.user_id}'
        elif user_type == 'admin':
            self.role_group = f'admin_{self.user_id}'
        
        # Unirse al grupo general de notificaciones
        await self.channel_layer.group_add(
            self.user_group,
            self.channel_name
        )
        
        # Unirse al grupo específico del rol
        if self.role_group:
            await self.channel_layer.group_add(
                self.role_group,
                self.channel_name
            )
        
        await self.accept()
        
        # Enviar contador inicial de no leídas
        unread_count = await self.get_unread_count()
        await self.send(text_data=json.dumps({
            'type': 'unread_count',
            'count': unread_count
        }))
        
        print(f"✅ WebSocket conectado - Usuario: {self.user.username} (ID: {self.user_id})")
    
    async def disconnect(self, close_code):
        # Abandonar grupos
        await self.channel_layer.group_discard(
            self.user_group,
            self.channel_name
        )
        if self.role_group:
            await self.channel_layer.group_discard(
                self.role_group,
                self.channel_name
            )
        print(f"🔌 WebSocket desconectado - Usuario: {self.user_id}")
    
    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get('action')
        
        if action == 'mark_read':
            notification_id = data.get('notification_id')
            await self.mark_notification_read(notification_id)
            
            # Enviar actualización de contador
            unread_count = await self.get_unread_count()
            await self.send(text_data=json.dumps({
                'type': 'unread_count',
                'count': unread_count
            }))
    
    async def notification_message(self, event):
        """Enviar notificación al cliente"""
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'data': event['data']
        }))
    
    async def notification_count_update(self, event):
        """Actualizar contador de notificaciones no leídas"""
        await self.send(text_data=json.dumps({
            'type': 'unread_count',
            'count': event['count']
        }))
    
    @database_sync_to_async
    def mark_notification_read(self, notification_id):
        try:
            notification = Notification.objects.get(
                id=notification_id,
                user_id=self.user_id
            )
            notification.mark_as_read()
            return True
        except Notification.DoesNotExist:
            return False
    
    @database_sync_to_async
    def get_unread_count(self):
        return Notification.objects.filter(
            user_id=self.user_id,
            is_read=False
        ).count()