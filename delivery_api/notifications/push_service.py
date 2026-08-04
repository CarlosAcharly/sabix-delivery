"""
Servicio de notificaciones push con Firebase Cloud Messaging
"""
import logging
from typing import List, Optional, Dict, Any
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import FCMDeviceToken

try:
    from firebase_admin import messaging
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
except Exception:
    FIREBASE_AVAILABLE = False

logger = logging.getLogger(__name__)

User = get_user_model()


class PushNotificationService:
    """
    Servicio para enviar notificaciones push usando FCM
    """
    
    @staticmethod
    def register_device(user_id: int, token: str, device_type: str, device_name: str = None) -> Dict[str, Any]:
        """
        Registrar un dispositivo para recibir notificaciones push
        """
        try:
            user = User.objects.get(id=user_id)
            
            # Desactivar token antiguo si existe
            FCMDeviceToken.objects.filter(user=user, token=token).update(is_active=False)
            
            # Crear o actualizar token
            device_token, created = FCMDeviceToken.objects.update_or_create(
                user=user,
                token=token,
                defaults={
                    'device_type': device_type,
                    'device_name': device_name,
                    'is_active': True,
                    'last_used': timezone.now(),
                }
            )
            
            return {
                'success': True,
                'token_id': device_token.id,
                'created': created,
                'message': 'Dispositivo registrado exitosamente'
            }
        except User.DoesNotExist:
            return {'success': False, 'error': 'Usuario no encontrado'}
        except Exception as e:
            logger.error(f"Error registrando dispositivo: {e}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def unregister_device(user_id: int, token: str) -> Dict[str, Any]:
        """
        Desregistrar un dispositivo
        """
        try:
            device = FCMDeviceToken.objects.get(user_id=user_id, token=token)
            device.is_active = False
            device.save()
            return {'success': True, 'message': 'Dispositivo desregistrado'}
        except FCMDeviceToken.DoesNotExist:
            return {'success': False, 'error': 'Dispositivo no encontrado'}
    
    @staticmethod
    def send_push_notification(
        user_id: int,
        title: str,
        body: str,
        data: Dict[str, Any] = None,
        android_channel_id: str = "delivery_notifications",
        sound: str = "default",
        badge: int = 1,
    ) -> Dict[str, Any]:
        """
        Enviar notificación push a un usuario específico
        """
        if not FIREBASE_AVAILABLE:
            logger.warning("Firebase no está disponible. Notificación push no enviada.")
            return {'success': False, 'error': 'Firebase no disponible'}
        
        try:
            # Obtener tokens activos del usuario
            tokens = FCMDeviceToken.objects.filter(
                user_id=user_id,
                is_active=True
            ).values_list('token', flat=True)
            
            if not tokens:
                return {'success': False, 'error': 'No hay dispositivos registrados'}
            
            # Construir mensaje
            message = messaging.MulticastMessage(
                tokens=list(tokens),
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                data=data or {},
                android=messaging.AndroidConfig(
                    priority='high',
                    notification=messaging.AndroidNotification(
                        channel_id=android_channel_id,
                        sound=sound,
                        badge=badge,
                        click_action="FLUTTER_NOTIFICATION_CLICK",
                    ),
                ),
                apns=messaging.APNSConfig(
                    headers={
                        "apns-priority": "10",
                    },
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            alert=messaging.ApsAlert(
                                title=title,
                                body=body,
                            ),
                            sound=sound,
                            badge=badge,
                            content_available=True,
                        ),
                    ),
                ),
            )
            
            # Enviar mensaje
            response = messaging.send_each_for_multicast(message)
            
            # Procesar resultados
            success_count = response.success_count
            failure_count = response.failure_count
            
            # Desactivar tokens fallidos
            for idx, result in enumerate(response.responses):
                if not result.success:
                    token = tokens[idx]
                    FCMDeviceToken.objects.filter(token=token).update(is_active=False)
                    logger.warning(f"Token FCM desactivado: {token[:20]}...")
            
            return {
                'success': success_count > 0,
                'success_count': success_count,
                'failure_count': failure_count,
                'total': len(tokens),
                'message': f'Notificación enviada a {success_count} dispositivos'
            }
            
        except Exception as e:
            logger.error(f"Error enviando notificación push: {e}")
            return {'success': False, 'error': str(e)}