from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    Conversation, ConversationParticipant, 
    Message, MessageRead, SupportRequest
)

User = get_user_model()


# =============================================
# SERIALIZERS DE PARTICIPANTES
# =============================================

class ParticipantUserSerializer(serializers.ModelSerializer):
    """Serializer para el usuario dentro de un participante"""
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'full_name', 'user_type', 'profile_image', 'phone']
    
    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username


class ConversationParticipantSerializer(serializers.ModelSerializer):
    """Serializer para participantes de la conversación"""
    user = ParticipantUserSerializer(read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    unread_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ConversationParticipant
        fields = [
            'id', 'user', 'role', 'role_display', 'is_active',
            'joined_at', 'left_at', 'last_read_at', 'unread_count'
        ]
    
    def get_unread_count(self, obj):
        if not obj.last_read_at:
            return obj.conversation.messages.filter(is_deleted=False).count()
        return obj.conversation.messages.filter(
            is_deleted=False,
            created_at__gt=obj.last_read_at
        ).exclude(sender=obj.user).count()


# =============================================
# SERIALIZERS DE MENSAJES
# =============================================

class MessageReplySerializer(serializers.ModelSerializer):
    """Serializer ligero para mensajes respondidos"""
    sender_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = ['id', 'sender_name', 'content', 'message_type', 'created_at']
    
    def get_sender_name(self, obj):
        return obj.sender.get_full_name() or obj.sender.username


class MessageSerializer(serializers.ModelSerializer):
    """Serializer completo para mensajes"""
    sender = ParticipantUserSerializer(read_only=True)
    reply_to = MessageReplySerializer(read_only=True)
    is_mine = serializers.SerializerMethodField()
    is_read = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = [
            'id', 'conversation', 'sender', 'message_type', 'content',
            'metadata', 'reply_to', 'is_edited', 'edited_at',
            'is_deleted', 'created_at', 'is_mine', 'is_read'
        ]
        read_only_fields = ['sender', 'is_edited', 'edited_at', 'is_deleted']
    
    def get_is_mine(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.sender_id == request.user.id
        return False
    
    def get_is_read(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.reads.filter(user=request.user).exists()
        return False


class MessageCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear mensajes"""
    content = serializers.CharField(required=True, allow_blank=False)
    message_type = serializers.ChoiceField(
        choices=Message.MESSAGE_TYPES,
        default='text'
    )
    reply_to_id = serializers.IntegerField(required=False, allow_null=True)
    
    class Meta:
        model = Message
        fields = ['content', 'message_type', 'metadata', 'reply_to_id']
    
    def validate_reply_to_id(self, value):
        if value:
            try:
                Message.objects.get(id=value)
            except Message.DoesNotExist:
                raise serializers.ValidationError('El mensaje a responder no existe')
        return value
    
    def create(self, validated_data):
        request = self.context.get('request')
        conversation = self.context.get('conversation')
        
        reply_to_id = validated_data.pop('reply_to_id', None)
        reply_to = None
        if reply_to_id:
            try:
                reply_to = Message.objects.get(id=reply_to_id, conversation=conversation)
            except Message.DoesNotExist:
                pass
        
        message = Message.objects.create(
            conversation=conversation,
            sender=request.user,
            reply_to=reply_to,
            **validated_data
        )
        
        # Marcar como leído por el propio emisor
        MessageRead.objects.create(message=message, user=request.user)
        
        # Actualizar last_read_at del participante
        ConversationParticipant.objects.filter(
            conversation=conversation,
            user=request.user
        ).update(last_read_at=timezone.now())
        
        # Actualizar updated_at de la conversación
        conversation.save(update_fields=['updated_at'])
        
        return message


# =============================================
# SERIALIZERS DE CONVERSACIONES
# =============================================

class ConversationListSerializer(serializers.ModelSerializer):
    """Serializer ligero para listar conversaciones"""
    order_id = serializers.IntegerField(source='order.id', read_only=True)
    order_status = serializers.CharField(source='order.status', read_only=True)
    order_status_display = serializers.CharField(source='order.get_status_display', read_only=True)
    client_name = serializers.SerializerMethodField()
    restaurant_name = serializers.SerializerMethodField()
    delivery_person_name = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    participant_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = [
            'id', 'order_id', 'order_status', 'order_status_display',
            'client_name', 'restaurant_name', 'delivery_person_name',
            'is_active', 'is_support_requested', 'support_requested_at',
            'last_message', 'unread_count', 'participant_count',
            'created_at', 'updated_at'
        ]
    
    def get_client_name(self, obj):
        return obj.order.client.get_full_name() or obj.order.client.username
    
    def get_restaurant_name(self, obj):
        return obj.order.restaurant.restaurant_name or obj.order.restaurant.username
    
    def get_delivery_person_name(self, obj):
        if obj.order.delivery_person:
            return obj.order.delivery_person.get_full_name() or obj.order.delivery_person.username
        return None
    
    def get_last_message(self, obj):
        last = obj.last_message
        if last:
            return {
                'id': last.id,
                'content': last.content[:100],
                'sender_name': last.sender.get_full_name() or last.sender.username,
                'message_type': last.message_type,
                'created_at': last.created_at.isoformat(),
            }
        return None
    
    def get_unread_count(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return 0
        
        participant = obj.participants.filter(user=request.user).first()
        if not participant:
            return 0
        
        if not participant.last_read_at:
            return obj.messages.filter(is_deleted=False).exclude(sender=request.user).count()
        
        return obj.messages.filter(
            is_deleted=False,
            created_at__gt=participant.last_read_at
        ).exclude(sender=request.user).count()
    
    def get_participant_count(self, obj):
        return obj.participants.filter(is_active=True).count()


class ConversationDetailSerializer(serializers.ModelSerializer):
    """Serializer completo para detalle de conversación"""
    order_id = serializers.IntegerField(source='order.id', read_only=True)
    order_status = serializers.CharField(source='order.status', read_only=True)
    order_status_display = serializers.CharField(source='order.get_status_display', read_only=True)
    order_total = serializers.DecimalField(
        source='order.total',
        max_digits=10,
        decimal_places=2,
        read_only=True
    )
    client = ParticipantUserSerializer(source='order.client', read_only=True)
    restaurant = ParticipantUserSerializer(source='order.restaurant', read_only=True)
    delivery_person = ParticipantUserSerializer(source='order.delivery_person', read_only=True)
    participants = ConversationParticipantSerializer(many=True, read_only=True)
    support_requests = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = [
            'id', 'order_id', 'order_status', 'order_status_display', 'order_total',
            'client', 'restaurant', 'delivery_person',
            'is_active', 'is_support_requested', 'support_requested_at',
            'support_requested_by', 'closed_at', 'participants', 'support_requests',
            'created_at', 'updated_at'
        ]
    
    def get_support_requests(self, obj):
        requests = obj.support_requests.filter(status__in=['pending', 'in_progress'])
        return SupportRequestListSerializer(requests, many=True).data


# =============================================
# SERIALIZERS DE SOLICITUDES DE SOPORTE
# =============================================

class SupportRequestListSerializer(serializers.ModelSerializer):
    """Serializer ligero para solicitudes de soporte"""
    requested_by_name = serializers.SerializerMethodField()
    assigned_to_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    order_id = serializers.IntegerField(source='conversation.order.id', read_only=True)
    
    class Meta:
        model = SupportRequest
        fields = [
            'id', 'conversation', 'order_id', 'requested_by', 'requested_by_name',
            'reason', 'priority', 'priority_display', 'status', 'status_display',
            'assigned_to', 'assigned_to_name', 'resolution_notes',
            'resolved_at', 'created_at', 'updated_at'
        ]
    
    def get_requested_by_name(self, obj):
        return obj.requested_by.get_full_name() or obj.requested_by.username
    
    def get_assigned_to_name(self, obj):
        if obj.assigned_to:
            return obj.assigned_to.get_full_name() or obj.assigned_to.username
        return None


class SupportRequestCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear solicitudes de soporte"""
    reason = serializers.CharField(required=True, allow_blank=False)
    priority = serializers.ChoiceField(
        choices=SupportRequest.PRIORITY_CHOICES,
        default='medium'
    )
    
    class Meta:
        model = SupportRequest
        fields = ['reason', 'priority']
    
    def create(self, validated_data):
        request = self.context.get('request')
        conversation = self.context.get('conversation')
        
        # Verificar que no haya una solicitud pendiente
        if conversation.support_requests.filter(status__in=['pending', 'in_progress']).exists():
            raise serializers.ValidationError(
                'Ya existe una solicitud de soporte activa para este pedido'
            )
        
        support_request = SupportRequest.objects.create(
            conversation=conversation,
            requested_by=request.user,
            **validated_data
        )
        
        # Marcar la conversación
        conversation.is_support_requested = True
        conversation.support_requested_at = timezone.now()
        conversation.support_requested_by = request.user
        conversation.save()
        
        return support_request


# =============================================
# SERIALIZERS DE ADMINISTRACIÓN
# =============================================

class AdminSupportRequestSerializer(serializers.ModelSerializer):
    """Serializer para que los admins gestionen solicitudes"""
    class Meta:
        model = SupportRequest
        fields = ['status', 'assigned_to', 'resolution_notes', 'priority']
    
    def validate_status(self, value):
        if value not in ['pending', 'in_progress', 'resolved', 'closed']:
            raise serializers.ValidationError('Estado no válido')
        return value
    
    def update(self, instance, validated_data):
        new_status = validated_data.get('status')
        
        # Si se resuelve, marcar la conversación como resuelta
        if new_status in ['resolved', 'closed'] and instance.status != new_status:
            instance.resolved_at = timezone.now()
            instance.conversation.is_support_requested = False
            instance.conversation.save()
        
        return super().update(instance, validated_data)