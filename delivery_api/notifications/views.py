from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Count
from django.utils import timezone
from datetime import timedelta
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Notification, NotificationPreference, DeviceToken
from .serializers import (
    NotificationSerializer, NotificationCreateSerializer,
    NotificationPreferenceSerializer, DeviceTokenSerializer,
    UnreadCountSerializer
)
from users.permissions import IsAdminUser

# =============================================
# NOTIFICACIONES DEL USUARIO
# =============================================

class NotificationListView(generics.ListAPIView):
    """
    Listar notificaciones del usuario autenticado
    """
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = Notification.objects.filter(user=self.request.user)
        
        # Filtros
        is_read = self.request.query_params.get('is_read')
        is_archived = self.request.query_params.get('is_archived')
        notification_type = self.request.query_params.get('type')
        
        if is_read is not None:
            queryset = queryset.filter(is_read=is_read.lower() == 'true')
        if is_archived is not None:
            queryset = queryset.filter(is_archived=is_archived.lower() == 'true')
        if notification_type:
            queryset = queryset.filter(type=notification_type)
        
        return queryset.order_by('-priority', '-created_at')

class UnreadNotificationsView(generics.ListAPIView):
    """
    Listar notificaciones no leídas del usuario
    """
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Notification.objects.filter(
            user=self.request.user,
            is_read=False,
            is_archived=False
        ).order_by('-priority', '-created_at')

class NotificationDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Ver, actualizar o eliminar una notificación específica
    """
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

class MarkNotificationReadView(APIView):
    """
    Marcar una notificación como leída
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pk):
        try:
            notification = Notification.objects.get(id=pk, user=request.user)
        except Notification.DoesNotExist:
            return Response(
                {'error': 'Notificación no encontrada'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        notification.mark_as_read()
        
        return Response({
            'message': 'Notificación marcada como leída',
            'notification': NotificationSerializer(notification).data
        })

class MarkAllNotificationsReadView(APIView):
    """
    Marcar todas las notificaciones como leídas
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        notifications = Notification.objects.filter(
            user=request.user,
            is_read=False
        )
        
        count = notifications.count()
        for notification in notifications:
            notification.mark_as_read()
        
        return Response({
            'message': f'{count} notificaciones marcadas como leídas',
            'count': count
        })

class UnreadCountView(APIView):
    """
    Obtener el número de notificaciones no leídas
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        count = Notification.objects.filter(
            user=request.user,
            is_read=False,
            is_archived=False
        ).count()
        
        return Response({'count': count})

# =============================================
# PREFERENCIAS DE NOTIFICACIONES
# =============================================

class NotificationPreferenceView(generics.RetrieveUpdateAPIView):
    """
    Obtener o actualizar preferencias de notificaciones
    """
    serializer_class = NotificationPreferenceSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        preference, created = NotificationPreference.objects.get_or_create(
            user=self.request.user
        )
        return preference

# =============================================
# TOKENS DE DISPOSITIVOS (PUSH NOTIFICATIONS)
# =============================================

class DeviceTokenListCreateView(generics.ListCreateAPIView):
    """
    Listar o crear tokens de dispositivos
    """
    serializer_class = DeviceTokenSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return DeviceToken.objects.filter(user=self.request.user, is_active=True)

class DeviceTokenDeleteView(generics.DestroyAPIView):
    """
    Eliminar un token de dispositivo
    """
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return DeviceToken.objects.filter(user=self.request.user)

# =============================================
# ADMINISTRACIÓN (SOLO ADMIN)
# =============================================

class AdminNotificationCreateView(generics.CreateAPIView):
    """
    Crear notificación para un usuario específico (solo admin)
    """
    serializer_class = NotificationCreateSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]

class AdminBroadcastNotificationView(APIView):
    """
    Enviar notificación masiva a usuarios filtrados por tipo (solo admin)
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def post(self, request):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        title = request.data.get('title')
        message = request.data.get('message')
        notification_type = request.data.get('type', 'system')
        data = request.data.get('data', {})
        user_filter = request.data.get('user_filter', 'all')
        priority = request.data.get('priority', 0)
        
        if not title or not message:
            return Response(
                {'error': 'Título y mensaje son requeridos'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # =============================================
        # FILTRAR USUARIOS POR TIPO
        # =============================================
        if user_filter == 'all':
            users = User.objects.filter(is_active=True)
            filter_description = 'todos los usuarios'
        elif user_filter == 'clients':
            users = User.objects.filter(is_active=True, user_type='client')
            filter_description = 'clientes'
        elif user_filter == 'deliveries':
            users = User.objects.filter(is_active=True, user_type='delivery')
            filter_description = 'repartidores'
        elif user_filter == 'restaurants':
            users = User.objects.filter(is_active=True, user_type='restaurant')
            filter_description = 'restaurantes'
        elif user_filter == 'admins':
            users = User.objects.filter(is_active=True, user_type='admin')
            filter_description = 'administradores'
        elif user_filter.startswith('user_'):
            # Enviar a un usuario específico
            try:
                user_id = int(user_filter.split('_')[1])
                users = User.objects.filter(id=user_id, is_active=True)
                filter_description = f'usuario {users.first().username if users.exists() else "no encontrado"}'
            except (ValueError, IndexError):
                return Response(
                    {'error': 'Formato de user_filter inválido. Use: user_<id>'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            return Response(
                {'error': f'Filtro inválido: {user_filter}. Opciones: all, clients, deliveries, restaurants, admins, user_<id>'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not users.exists():
            return Response(
                {'error': f'No hay usuarios activos en la categoría: {filter_description}'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # =============================================
        # CREAR NOTIFICACIONES Y ENVIAR WEBSOCKET
        # =============================================
        channel_layer = get_channel_layer()
        notifications_created = []
        
        for user in users:
            # Crear notificación en base de datos
            notification = Notification.objects.create(
                user=user,
                type=notification_type,
                title=title,
                message=message,
                data=data,
                priority=priority
            )
            notifications_created.append(notification)
            
            # =============================================
            # ENVIAR WEBSOCKET AL GRUPO GENERAL
            # =============================================
            try:
                async_to_sync(channel_layer.group_send)(
                    f'notifications_{user.id}',
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
                            'priority': notification.priority,
                        }
                    }
                )
            except Exception as e:
                print(f"Error enviando WebSocket al usuario {user.id}: {e}")
            
            # =============================================
            # ENVIAR WEBSOCKET AL GRUPO ESPECÍFICO DEL ROL
            # =============================================
            role_group_map = {
                'restaurant': f'restaurant_{user.id}',
                'delivery': f'delivery_{user.id}',
                'client': f'client_{user.id}',
                'admin': f'admin_{user.id}',
            }
            
            role_group = role_group_map.get(user.user_type)
            if role_group:
                try:
                    async_to_sync(channel_layer.group_send)(
                        role_group,
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
                                'priority': notification.priority,
                            }
                        }
                    )
                except Exception as e:
                    print(f"Error enviando WebSocket al grupo {role_group}: {e}")
        
        return Response({
            'message': f'Notificación enviada a {users.count()} {filter_description}',
            'count': users.count(),
            'filter': user_filter,
            'users': [user.username for user in users[:5]]
        }, status=status.HTTP_201_CREATED)

class AdminNotificationStatsView(APIView):
    """
    Estadísticas de notificaciones (solo admin)
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get(self, request):
        from django.db.models import Count, Q
        from datetime import timedelta
        from django.utils import timezone
        
        # Totales por tipo
        type_counts = Notification.objects.values('type').annotate(
            count=Count('id')
        )
        
        # Notificaciones leídas vs no leídas
        read_stats = Notification.objects.aggregate(
            read_count=Count('id', filter=Q(is_read=True)),
            unread_count=Count('id', filter=Q(is_read=False)),
            total_count=Count('id')
        )
        
        # Notificaciones por día (últimos 7 días)
        seven_days_ago = timezone.now() - timedelta(days=7)
        daily_stats = Notification.objects.filter(
            created_at__gte=seven_days_ago
        ).extra(
            {'day': "date(created_at)"}
        ).values('day').annotate(
            count=Count('id')
        ).order_by('day')
        
        stats = {
            'type_counts': type_counts,
            'read_stats': read_stats,
            'daily_stats': daily_stats,
            'total': read_stats['total_count']
        }
        
        return Response(stats)