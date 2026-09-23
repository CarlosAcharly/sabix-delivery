from rest_framework import permissions
from .models import Conversation, ConversationParticipant


class IsConversationParticipant(permissions.BasePermission):
    """
    Permite acceso solo si el usuario es participante activo de la conversación
    """
    message = "No eres participante de esta conversación"
    
    def has_permission(self, request, view):
        return request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Obtener la conversación del objeto
        if isinstance(obj, Conversation):
            conversation = obj
        elif hasattr(obj, 'conversation'):
            conversation = obj.conversation
        else:
            return False
        
        user = request.user
        
        # Admin/Soporte: solo si está asignado a una solicitud de soporte activa
        if user.user_type == 'admin' or user.is_superuser:
            return conversation.support_requests.filter(
                assigned_to=user,
                status__in=['pending', 'in_progress']
            ).exists()
        
        # Verificar si es participante activo
        return conversation.participants.filter(
            user=user,
            is_active=True
        ).exists()


class CanAccessOrderChat(permissions.BasePermission):
    """
    Verifica si el usuario puede acceder al chat de un pedido
    según su rol y relación con el pedido
    """
    message = "No tienes acceso a este chat"
    
    def has_permission(self, request, view):
        return request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        user = request.user
        
        # Obtener la conversación
        if isinstance(obj, Conversation):
            conversation = obj
        elif hasattr(obj, 'conversation'):
            conversation = obj.conversation
        else:
            return False
        
        order = conversation.order
        
        # Cliente: dueño del pedido
        if user.user_type == 'client':
            return order.client_id == user.id
        
        # Sucursal: dueña del restaurante
        if user.user_type == 'restaurant':
            return order.restaurant_id == user.id
        
        # Repartidor: asignado al pedido
        if user.user_type == 'delivery':
            return order.delivery_person_id == user.id
        
        # Admin: acceso controlado
        if user.user_type == 'admin' or user.is_superuser:
            return conversation.support_requests.filter(
                assigned_to=user,
                status__in=['pending', 'in_progress']
            ).exists()
        
        return False


class CanSendMessage(permissions.BasePermission):
    """
    Permite enviar mensajes solo si la conversación está activa
    y el usuario es participante
    """
    message = "No puedes enviar mensajes en esta conversación"
    
    def has_object_permission(self, request, view, obj):
        if not isinstance(obj, Conversation):
            return False
        
        # La conversación debe estar activa
        if not obj.is_active:
            return False
        
        # El usuario debe ser participante activo
        return obj.participants.filter(
            user=request.user,
            is_active=True
        ).exists()


class IsSupportAdmin(permissions.BasePermission):
    """
    Permite acceso solo a administradores de soporte
    """
    message = "Solo administradores pueden realizar esta acción"
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.user_type == 'admin' or 
            request.user.is_superuser
        )