from rest_framework import permissions

class IsRestaurantUser(permissions.BasePermission):
    """
    Permiso para usuarios tipo restaurante
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type == 'restaurant'

class IsAdminUser(permissions.BasePermission):
    """
    Permiso para usuarios administradores
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and (request.user.user_type == 'admin' or request.user.is_superuser)

class IsClientUser(permissions.BasePermission):
    """
    Permiso para usuarios tipo cliente
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type == 'client'

class IsDeliveryUser(permissions.BasePermission):
    """
    Permiso para usuarios tipo repartidor
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type == 'delivery'