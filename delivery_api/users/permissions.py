from rest_framework import permissions

class IsRestaurantUser(permissions.BasePermission):
    """
    Permiso para usuarios tipo restaurante
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type == 'restaurant'
    
    def has_object_permission(self, request, view, obj):
        """
        Verifica si el usuario tiene permiso sobre un objeto específico
        """
        # Admin tiene permiso sobre todo
        if request.user.is_admin_user:
            return True
        
        # Restaurante solo sobre sus propios objetos
        if hasattr(obj, 'restaurant'):
            return obj.restaurant.id == request.user.id
        if hasattr(obj, 'user'):
            return obj.user.id == request.user.id
        if hasattr(obj, 'id') and obj.id == request.user.id:
            return True
        
        return False

class IsAdminUser(permissions.BasePermission):
    """
    Permiso para usuarios administradores
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and (request.user.user_type == 'admin' or request.user.is_superuser)
    
    def has_object_permission(self, request, view, obj):
        """
        Admin tiene permisos sobre cualquier objeto
        """
        return True

class IsClientUser(permissions.BasePermission):
    """
    Permiso para usuarios tipo cliente
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type == 'client'
    
    def has_object_permission(self, request, view, obj):
        """
        Cliente solo sobre sus propios objetos
        """
        if hasattr(obj, 'user'):
            return obj.user.id == request.user.id
        if hasattr(obj, 'id') and obj.id == request.user.id:
            return True
        return False

class IsDeliveryUser(permissions.BasePermission):
    """
    Permiso para usuarios tipo repartidor
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type == 'delivery'
    
    def has_object_permission(self, request, view, obj):
        """
        Repartidor solo sobre sus propios objetos
        """
        if hasattr(obj, 'delivery_person'):
            return obj.delivery_person.id == request.user.id
        if hasattr(obj, 'user'):
            return obj.user.id == request.user.id
        if hasattr(obj, 'id') and obj.id == request.user.id:
            return True
        return False

class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Permiso para dueño del recurso o administrador
    """
    def has_object_permission(self, request, view, obj):
        # Admin tiene permiso total
        if request.user.is_admin_user:
            return True
        
        # Verificar si el usuario es el dueño del objeto
        if hasattr(obj, 'user') and hasattr(obj.user, 'id'):
            return obj.user.id == request.user.id
        if hasattr(obj, 'restaurant') and hasattr(obj.restaurant, 'id'):
            return obj.restaurant.id == request.user.id
        if hasattr(obj, 'id') and obj.id == request.user.id:
            return True
        
        # Verificar si el objeto tiene un campo 'owner' o similar
        if hasattr(obj, 'owner') and hasattr(obj.owner, 'id'):
            return obj.owner.id == request.user.id
        
        return False

class IsAppUserType(permissions.BasePermission):
    """
    Permiso para verificar el tipo de usuario para una app específica
    """
    def __init__(self, allowed_types):
        self.allowed_types = allowed_types if isinstance(allowed_types, list) else [allowed_types]
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type in self.allowed_types

# =============================================
# PERMISOS COMBINADOS
# =============================================

class IsRestaurantOrAdmin(permissions.BasePermission):
    """
    Permiso para restaurantes o administradores
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.user_type == 'restaurant' or 
            request.user.user_type == 'admin' or 
            request.user.is_superuser
        )
    
    def has_object_permission(self, request, view, obj):
        if request.user.is_admin_user:
            return True
        if hasattr(obj, 'restaurant'):
            return obj.restaurant.id == request.user.id
        return False

class IsDeliveryOrAdmin(permissions.BasePermission):
    """
    Permiso para repartidores o administradores
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.user_type == 'delivery' or 
            request.user.user_type == 'admin' or 
            request.user.is_superuser
        )
    
    def has_object_permission(self, request, view, obj):
        if request.user.is_admin_user:
            return True
        if hasattr(obj, 'delivery_person'):
            return obj.delivery_person.id == request.user.id
        return False

class IsClientOrAdmin(permissions.BasePermission):
    """
    Permiso para clientes o administradores
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.user_type == 'client' or 
            request.user.user_type == 'admin' or 
            request.user.is_superuser
        )
    
    def has_object_permission(self, request, view, obj):
        if request.user.is_admin_user:
            return True
        if hasattr(obj, 'user'):
            return obj.user.id == request.user.id
        return False