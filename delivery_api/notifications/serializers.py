from rest_framework import serializers
from .models import Notification, NotificationPreference, DeviceToken

class NotificationSerializer(serializers.ModelSerializer):
    """Serializer para notificaciones"""
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    time_ago = serializers.CharField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Notification
        fields = [
            'id', 'user', 'order', 'type', 'type_display',
            'title', 'message', 'data', 'is_read', 'is_archived',
            'priority', 'priority_display', 'created_at', 'read_at',
            'expires_at', 'time_ago', 'is_expired'
        ]
        read_only_fields = ['user', 'created_at', 'read_at']

class NotificationCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear notificaciones"""
    
    class Meta:
        model = Notification
        fields = [
            'user', 'order', 'type', 'title', 'message',
            'data', 'priority', 'expires_at'
        ]
    
    def create(self, validated_data):
        # Asegurar que el usuario no se pueda modificar manualmente
        if 'user' not in validated_data:
            validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """Serializer para preferencias de notificaciones"""
    
    class Meta:
        model = NotificationPreference
        fields = [
            'push_enabled', 'email_enabled', 'sms_enabled', 'in_app_enabled',
            'order_notifications', 'promotion_notifications', 'system_notifications',
            'quiet_hours_start', 'quiet_hours_end'
        ]
    
    def validate(self, data):
        # Validar horas silenciosas
        if data.get('quiet_hours_start') and data.get('quiet_hours_end'):
            if data['quiet_hours_start'] == data['quiet_hours_end']:
                raise serializers.ValidationError({
                    'quiet_hours_start': 'Las horas de inicio y fin no pueden ser iguales'
                })
        return data

class DeviceTokenSerializer(serializers.ModelSerializer):
    """Serializer para tokens de dispositivos"""
    
    class Meta:
        model = DeviceToken
        fields = [
            'id', 'token', 'device_type', 'device_name',
            'is_active', 'last_used', 'created_at'
        ]
        read_only_fields = ['user', 'last_used', 'created_at']
    
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class UnreadCountSerializer(serializers.Serializer):
    """Serializer para contar notificaciones no leídas"""
    count = serializers.IntegerField()