from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.utils import timezone
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
    Enviar notificación masiva a todos los usuarios (solo admin)
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def post(self, request):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        title = request.data.get('title')
        message = request.data.get('message')
        notification_type = request.data.get('type', 'system')
        data = request.data.get('data', {})
        
        if not title or not message:
            return Response(
                {'error': 'Título y mensaje son requeridos'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Crear notificaciones para todos los usuarios
        users = User.objects.filter(is_active=True)
        notifications = []
        
        for user in users:
            notification = Notification(
                user=user,
                type=notification_type,
                title=title,
                message=message,
                data=data,
                priority=0
            )
            notifications.append(notification)
        
        # Crear en lote
        Notification.objects.bulk_create(notifications)
        
        # Enviar notificaciones en tiempo real (WebSockets)
        # Aquí iría la lógica para enviar push notifications
        
        return Response({
            'message': f'Notificación enviada a {users.count()} usuarios',
            'count': users.count()
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