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
        print(f"🔍 [CONNECT] User ID from URL: {self.user_id}")
        print(f"🔍 [CONNECT] Path: {self.scope['path']}")
        print(f"🔍 [CONNECT] Query string: {self.scope['query_string'].decode()}")

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

        print(f"🔍 [CONNECT] Token encontrado: {token[:30] if token else 'NO TOKEN'}...")

        if token:
            try:
                access_token = AccessToken(token)
                user_id_from_token = access_token.payload.get('user_id')
                print(f"🔍 [CONNECT] User ID from token: {user_id_from_token}")

                if str(user_id_from_token) == self.user_id:
                    try:
                        self.user = await database_sync_to_async(User.objects.get)(id=user_id_from_token)
                        print(f"✅ [CONNECT] Usuario autenticado: {self.user.username} (ID: {self.user.id})")
                    except User.DoesNotExist:
                        print(f"❌ [CONNECT] Usuario ID {user_id_from_token} no existe en la base de datos")
                        await self.close(code=4401)
                        return
                else:
                    print(f"❌ [CONNECT] ID no coincide: token={user_id_from_token}, URL={self.user_id}")
                    await self.close(code=4401)
                    return
            except Exception as e:
                print(f"❌ [CONNECT] Error de autenticación WebSocket: {str(e)}")
                await self.close(code=4401)
                return
        else:
            print("❌ [CONNECT] No se proporcionó token")
            await self.close(code=4401)
            return

        # =============================================
        # GRUPOS POR ROL
        # =============================================
        self.user_group = f'notifications_{self.user_id}'
        self.role_group = None

        user_type = self.user.user_type
        print(f"🔍 [CONNECT] Tipo de usuario: {user_type}")

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
        print(f"✅ [CONNECT] Unido al grupo: {self.user_group}")

        # Unirse al grupo específico del rol
        if self.role_group:
            await self.channel_layer.group_add(
                self.role_group,
                self.channel_name
            )
            print(f"✅ [CONNECT] Unido al grupo de rol: {self.role_group}")

        await self.accept()
        print(f"✅ [CONNECT] WebSocket aceptado para usuario {self.user.username}")

        # Enviar contador inicial de no leídas
        unread_count = await self.get_unread_count()
        await self.send(text_data=json.dumps({
            'type': 'unread_count',
            'count': unread_count
        }))
        print(f"📊 [CONNECT] Contador de no leídas enviado: {unread_count}")

    async def disconnect(self, close_code):
        print(f"🔌 [DISCONNECT] WebSocket desconectado - Usuario: {getattr(self, 'user_id', 'unknown')} - Código: {close_code}")
        if hasattr(self, 'user_group'):
            await self.channel_layer.group_discard(self.user_group, self.channel_name)
        if hasattr(self, 'role_group') and self.role_group:
            await self.channel_layer.group_discard(self.role_group, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get('action')
        print(f"📩 [RECEIVE] Acción: {action}")
        
        if action == 'mark_read':
            notification_id = data.get('notification_id')
            await self.mark_notification_read(notification_id)
            unread_count = await self.get_unread_count()
            await self.send(text_data=json.dumps({
                'type': 'unread_count',
                'count': unread_count
            }))

    async def notification_message(self, event):
        print(f"📨 [NOTIFICATION] Enviando notificación al cliente: {event['data'].get('title')}")
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'data': event['data']
        }))

    async def notification_count_update(self, event):
        print(f"📊 [COUNT] Actualizando contador: {event['count']}")
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
            print(f"✅ [DB] Notificación {notification_id} marcada como leída")
            return True
        except Notification.DoesNotExist:
            print(f"❌ [DB] Notificación {notification_id} no encontrada")
            return False

    @database_sync_to_async
    def get_unread_count(self):
        count = Notification.objects.filter(
            user_id=self.user_id,
            is_read=False
        ).count()
        print(f"📊 [DB] Contador de no leídas: {count}")
        return count
