import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Notification

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user_id = self.scope['url_route']['kwargs']['user_id']
        
        # Grupos para diferentes roles
        self.user_group = f'notifications_{self.user_id}'
        self.role_group = None
        
        if self.scope['user'].is_authenticated and str(self.scope['user'].id) == self.user_id:
            user_type = self.scope['user'].user_type
            
            # Determinar grupo según rol
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
        else:
            await self.close()
    
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