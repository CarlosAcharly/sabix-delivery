from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Count, Max
from django.utils import timezone
from django.shortcuts import get_object_or_404
from .models import (
    Conversation, ConversationParticipant,
    Message, MessageRead, SupportRequest
)
from .serializers import (
    ConversationListSerializer, ConversationDetailSerializer,
    MessageSerializer, MessageCreateSerializer,
    SupportRequestListSerializer, SupportRequestCreateSerializer,
    AdminSupportRequestSerializer,
)
from .permissions import (
    IsConversationParticipant, CanAccessOrderChat,
    CanSendMessage, IsSupportAdmin
)
from .services import ChatNotificationService


# =============================================
# CONVERSACIONES
# =============================================

class ConversationListView(generics.ListAPIView):
    """
    Listar conversaciones del usuario autenticado
    """
    serializer_class = ConversationListSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        
        # Admin puede ver todas las conversaciones con soporte solicitado
        if user.user_type == 'admin' or user.is_superuser:
            # Solo las que tienen soporte solicitado o asignado
            return Conversation.objects.filter(
                Q(is_support_requested=True) |
                Q(support_requests__assigned_to=user)
            ).distinct().order_by('-updated_at')
        
        # Otros usuarios: solo sus conversaciones como participantes
        return Conversation.objects.filter(
            participants__user=user,
            participants__is_active=True
        ).distinct().order_by('-updated_at')


class ConversationDetailView(generics.RetrieveAPIView):
    """
    Ver detalle de una conversación
    """
    serializer_class = ConversationDetailSerializer
    permission_classes = [IsAuthenticated, CanAccessOrderChat]
    lookup_field = 'id'
    
    def get_queryset(self):
        return Conversation.objects.all()


class ConversationByOrderView(generics.RetrieveAPIView):
    """
    Obtener conversación por ID de pedido
    """
    serializer_class = ConversationDetailSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'order_id'
    
    def get_queryset(self):
        return Conversation.objects.filter(
            order_id=self.kwargs['order_id']
        )
    
    def get_object(self):
        conversation = get_object_or_404(
            Conversation,
            order_id=self.kwargs['order_id']
        )
        # Verificar permisos
        self.check_object_permissions(self.request, conversation)
        return conversation


# =============================================
# MENSAJES
# =============================================

class MessageListView(generics.ListAPIView):
    """
    Listar mensajes de una conversación
    """
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated, IsConversationParticipant]
    
    def get_queryset(self):
        conversation_id = self.kwargs['conversation_id']
        conversation = get_object_or_404(Conversation, id=conversation_id)
        
        # Verificar permisos
        self.check_object_permissions(self.request, conversation)
        
        # Marcar mensajes como leídos
        self._mark_messages_as_read(conversation)
        
        # Devolver mensajes (con paginación)
        return Message.objects.filter(
            conversation_id=conversation_id,
            is_deleted=False
        ).select_related('sender', 'reply_to').order_by('created_at')
    
    def _mark_messages_as_read(self, conversation):
        """Marcar todos los mensajes como leídos para el usuario actual"""
        user = self.request.user
        
        # Actualizar last_read_at del participante
        ConversationParticipant.objects.filter(
            conversation=conversation,
            user=user
        ).update(last_read_at=timezone.now())
        
        # Crear registros de lectura para mensajes no leídos
        unread_messages = Message.objects.filter(
            conversation=conversation,
            is_deleted=False
        ).exclude(
            reads__user=user
        ).exclude(sender=user)
        
        for message in unread_messages:
            MessageRead.objects.get_or_create(message=message, user=user)


class MessageCreateView(generics.CreateAPIView):
    """
    Enviar un mensaje en una conversación
    """
    serializer_class = MessageCreateSerializer
    permission_classes = [IsAuthenticated, IsConversationParticipant, CanSendMessage]
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        conversation_id = self.kwargs['conversation_id']
        conversation = get_object_or_404(Conversation, id=conversation_id)
        context['conversation'] = conversation
        return context
    
    def perform_create(self, serializer):
        conversation_id = self.kwargs['conversation_id']
        conversation = get_object_or_404(Conversation, id=conversation_id)
        
        # Verificar permisos
        self.check_object_permissions(self.request, conversation)
        
        # Crear mensaje
        message = serializer.save()
        
        # Notificar a los demás participantes
        ChatNotificationService.notify_new_message(
            conversation=conversation,
            message=MessageSerializer(message, context={'request': self.request}).data,
            exclude_user=self.request.user
        )
        
        return message
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = self.perform_create(serializer)
        
        return Response(
            MessageSerializer(message, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )


class MessageReplyView(APIView):
    """
    Responder a un mensaje específico
    """
    permission_classes = [IsAuthenticated, IsConversationParticipant]
    
    def post(self, request, conversation_id, message_id):
        conversation = get_object_or_404(Conversation, id=conversation_id)
        self.check_object_permissions(request, conversation)
        
        try:
            parent_message = Message.objects.get(id=message_id, conversation=conversation)
        except Message.DoesNotExist:
            return Response(
                {'error': 'Mensaje no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        content = request.data.get('content')
        if not content:
            return Response(
                {'error': 'El contenido es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        message = Message.objects.create(
            conversation=conversation,
            sender=request.user,
            content=content,
            message_type=request.data.get('message_type', 'text'),
            metadata=request.data.get('metadata', {}),
            reply_to=parent_message
        )
        
        # Marcar como leído
        MessageRead.objects.create(message=message, user=request.user)
        
        # Notificar
        ChatNotificationService.notify_new_message(
            conversation=conversation,
            message=MessageSerializer(message, context={'request': request}).data,
            exclude_user=request.user
        )
        
        return Response(
            MessageSerializer(message, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )


class MarkMessageReadView(APIView):
    """
    Marcar un mensaje como leído
    """
    permission_classes = [IsAuthenticated, IsConversationParticipant]
    
    def post(self, request, conversation_id, message_id):
        conversation = get_object_or_404(Conversation, id=conversation_id)
        self.check_object_permissions(request, conversation)
        
        try:
            message = Message.objects.get(id=message_id, conversation=conversation)
        except Message.DoesNotExist:
            return Response(
                {'error': 'Mensaje no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        MessageRead.objects.get_or_create(message=message, user=request.user)
        
        return Response({'message': 'Marcado como leído'}, status=status.HTTP_200_OK)


class MessageDeleteView(APIView):
    """
    Eliminar un mensaje (soft delete)
    """
    permission_classes = [IsAuthenticated, IsConversationParticipant]
    
    def delete(self, request, conversation_id, message_id):
        conversation = get_object_or_404(Conversation, id=conversation_id)
        self.check_object_permissions(request, conversation)
        
        try:
            message = Message.objects.get(
                id=message_id,
                conversation=conversation,
                sender=request.user  # Solo el emisor puede eliminar
            )
        except Message.DoesNotExist:
            return Response(
                {'error': 'Mensaje no encontrado o no puedes eliminarlo'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        message.is_deleted = True
        message.deleted_at = timezone.now()
        message.save()
        
        return Response({'message': 'Mensaje eliminado'}, status=status.HTTP_200_OK)


class UnreadCountView(APIView):
    """
    Obtener el número de mensajes no leídos de una conversación
    """
    permission_classes = [IsAuthenticated, IsConversationParticipant]
    
    def get(self, request, conversation_id):
        conversation = get_object_or_404(Conversation, id=conversation_id)
        self.check_object_permissions(request, conversation)
        
        participant = conversation.participants.get(user=request.user)
        
        if not participant.last_read_at:
            count = conversation.messages.filter(
                is_deleted=False
            ).exclude(sender=request.user).count()
        else:
            count = conversation.messages.filter(
                is_deleted=False,
                created_at__gt=participant.last_read_at
            ).exclude(sender=request.user).count()
        
        return Response({'count': count})


class TotalUnreadCountView(APIView):
    """
    Obtener el total de mensajes no leídos del usuario en todas sus conversaciones
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Obtener todas las conversaciones del usuario
        conversations = Conversation.objects.filter(
            participants__user=user,
            participants__is_active=True
        )
        
        total = 0
        for conversation in conversations:
            participant = conversation.participants.get(user=user)
            
            if not participant.last_read_at:
                count = conversation.messages.filter(
                    is_deleted=False
                ).exclude(sender=user).count()
            else:
                count = conversation.messages.filter(
                    is_deleted=False,
                    created_at__gt=participant.last_read_at
                ).exclude(sender=user).count()
            
            total += count
        
        return Response({'total_unread': total})


# =============================================
# SOPORTE
# =============================================

class RequestSupportView(APIView):
    """
    Solicitar soporte en una conversación
    """
    permission_classes = [IsAuthenticated, IsConversationParticipant]
    
    def post(self, request, conversation_id):
        conversation = get_object_or_404(Conversation, id=conversation_id)
        self.check_object_permissions(request, conversation)
        
        # Verificar que la conversación esté activa
        if not conversation.is_active:
            return Response(
                {'error': 'No se puede solicitar soporte en una conversación cerrada'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = SupportRequestCreateSerializer(
            data=request.data,
            context={'request': request, 'conversation': conversation}
        )
        serializer.is_valid(raise_exception=True)
        support_request = serializer.save()
        
        # Mensaje de sistema
        Message.objects.create(
            conversation=conversation,
            sender=request.user,
            message_type='system',
            content=f"Soporte solicitado: {support_request.reason}",
            metadata={'system': True, 'event': 'support_requested', 'support_id': support_request.id}
        )
        
        # Notificar a los admins
        ChatNotificationService.notify_new_message(
            conversation=conversation,
            message="🆘 Se ha solicitado soporte en este pedido",
            exclude_user=request.user
        )
        
        return Response(
            SupportRequestListSerializer(support_request).data,
            status=status.HTTP_201_CREATED
        )


class CloseConversationView(APIView):
    """
    Cerrar una conversación
    """
    permission_classes = [IsAuthenticated, IsConversationParticipant]
    
    def post(self, request, conversation_id):
        conversation = get_object_or_404(Conversation, id=conversation_id)
        self.check_object_permissions(request, conversation)
        
        conversation.is_active = False
        conversation.closed_at = timezone.now()
        conversation.save()
        
        return Response(
            {'message': 'Conversación cerrada'},
            status=status.HTTP_200_OK
        )


# =============================================
# ADMINISTRACIÓN DE SOPORTE# =============================================

class AdminSupportRequestListView(generics.ListAPIView):
    """
    Listar todas las solicitudes de soporte (solo admin)
    """
    serializer_class = SupportRequestListSerializer
    permission_classes = [IsAuthenticated, IsSupportAdmin]
    
    def get_queryset(self):
        queryset = SupportRequest.objects.all()
        
        # Filtros
        status_filter = self.request.query_params.get('status')
        priority_filter = self.request.query_params.get('priority')
        assigned_filter = self.request.query_params.get('assigned')
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if priority_filter:
            queryset = queryset.filter(priority=priority_filter)
        if assigned_filter == 'me':
            queryset = queryset.filter(assigned_to=self.request.user)
        elif assigned_filter == 'unassigned':
            queryset = queryset.filter(assigned_to__isnull=True)
        
        return queryset.order_by('-created_at')


class AdminSupportRequestDetailView(generics.RetrieveUpdateAPIView):
    """
    Ver y actualizar una solicitud de soporte (solo admin)
    """
    queryset = SupportRequest.objects.all()
    serializer_class = AdminSupportRequestSerializer
    permission_classes = [IsAuthenticated, IsSupportAdmin]
    lookup_field = 'id'
    
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        
        # Si se asigna, agregar al admin como participante
        assigned_to = serializer.validated_data.get('assigned_to')
        if assigned_to and assigned_to != instance.assigned_to:
            ConversationParticipant.objects.get_or_create(
                conversation=instance.conversation,
                user=assigned_to,
                defaults={
                    'role': 'support',
                    'is_active': True,
                }
            )
            
            # Mensaje de sistema
            Message.objects.create(
                conversation=instance.conversation,
                sender=assigned_to,
                message_type='system',
                content=f"{assigned_to.get_full_name() or assigned_to.username} (Soporte) se ha unido al chat.",
                metadata={'system': True, 'event': 'support_joined'}
            )
            
            # Notificar
            ChatNotificationService.notify_support_joined(
                conversation=instance.conversation,
                support_user=assigned_to
            )
        
        serializer.save()
        
        return Response(serializer.data)


class AdminJoinConversationView(APIView):
    """
    Unirse a una conversación (solo admin con solicitud asignada)
    """
    permission_classes = [IsAuthenticated, IsSupportAdmin]
    
    def post(self, request, conversation_id):
        conversation = get_object_or_404(Conversation, id=conversation_id)
        
        # Verificar que el admin esté asignado a una solicitud
        if not conversation.support_requests.filter(
            assigned_to=request.user,
            status__in=['pending', 'in_progress']
        ).exists():
            return Response(
                {'error': 'No tienes una solicitud asignada en esta conversación'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Agregar como participante
        participant, created = ConversationParticipant.objects.get_or_create(
            conversation=conversation,
            user=request.user,
            defaults={
                'role': 'support',
                'is_active': True,
            }
        )
        
        if created:
            # Mensaje de sistema
            Message.objects.create(
                conversation=conversation,
                sender=request.user,
                message_type='system',
                content=f"{request.user.get_full_name() or request.user.username} (Soporte) se ha unido al chat.",
                metadata={'system': True, 'event': 'support_joined'}
            )
            
            ChatNotificationService.notify_support_joined(
                conversation=conversation,
                support_user=request.user
            )
        
        return Response(
            ConversationDetailSerializer(conversation, context={'request': request}).data,
            status=status.HTTP_200_OK
        )


class AdminConversationListView(generics.ListAPIView):
    """
    Listar todas las conversaciones (solo admin)
    """
    serializer_class = ConversationListSerializer
    permission_classes = [IsAuthenticated, IsSupportAdmin]
    
    def get_queryset(self):
        queryset = Conversation.objects.all()
        
        # Filtros
        has_support = self.request.query_params.get('has_support')
        is_active = self.request.query_params.get('is_active')
        
        if has_support == 'true':
            queryset = queryset.filter(is_support_requested=True)
        if is_active == 'true':
            queryset = queryset.filter(is_active=True)
        elif is_active == 'false':
            queryset = queryset.filter(is_active=False)
        
        return queryset.order_by('-updated_at')