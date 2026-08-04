from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from orders.models import Order, OrderItem
from .models import Notification
from .push_service import PushNotificationService  # ✅ Agregar esta importación

import logging

logger = logging.getLogger(__name__)

User = get_user_model()


@receiver(post_save, sender=Order)
def create_order_notification(sender, instance, created, **kwargs):
    """
    Crea notificaciones automáticas cuando cambia el estado de un pedido
    """
    try:
        if created:
            # Notificar al restaurante: Nuevo pedido
            Notification.objects.create(
                user=instance.restaurant,
                type='order_new',
                title='¡Nuevo pedido! 📦',
                message=f'Cliente {instance.client.get_full_name()} realizó un pedido de ${instance.total}',
                data={
                    'order_id': instance.id,
                    'client_name': instance.client.get_full_name(),
                    'total': str(instance.total),
                    'items_count': instance.items.count() if hasattr(instance, 'items') else 0,
                    'status': instance.status
                },
                priority=1
            )
            
            # Notificar al cliente: Pedido creado
            Notification.objects.create(
                user=instance.client,
                type='system',
                title='Pedido creado ✅',
                message=f'Tu pedido #{instance.id} ha sido creado exitosamente',
                data={
                    'order_id': instance.id,
                    'status': instance.status
                },
                priority=0
            )
            
            logger.info(f"📨 Notificaciones creadas para nuevo pedido #{instance.id}")
        
        else:
            # Verificar cambios de estado
            status_handlers = {
                'confirmed': {
                    'type': 'order_confirmed',
                    'title': '¡Pedido confirmado! 🍕',
                    'message': f'Tu pedido #{instance.id} ha sido confirmado por {instance.restaurant.restaurant_name}',
                    'priority': 1,
                    'user': instance.client,
                    'data': {
                        'order_id': instance.id,
                        'restaurant_name': instance.restaurant.restaurant_name,
                        'status': instance.status
                    }
                },
                'preparing': {
                    'type': 'order_preparing',
                    'title': 'Tu pedido se está preparando 👨‍🍳',
                    'message': f'El restaurante está preparando tu pedido #{instance.id}',
                    'priority': 1,
                    'user': instance.client,
                    'data': {
                        'order_id': instance.id,
                        'status': instance.status
                    }
                },
                'ready': {
                    'type': 'order_ready',
                    'title': '¡Pedido listo para entregar! 🎯',
                    'message': f'Tu pedido #{instance.id} está listo y espera al repartidor',
                    'priority': 1,
                    'user': instance.client,
                    'data': {
                        'order_id': instance.id,
                        'status': instance.status
                    }
                },
                'in_delivery': {
                    'type': 'order_in_delivery',
                    'title': 'Tu pedido está en camino 🚀',
                    'message': f'El repartidor está llevando tu pedido #{instance.id}',
                    'priority': 2,
                    'user': instance.client,
                    'data': {
                        'order_id': instance.id,
                        'delivery_person': instance.delivery_person.get_full_name() if instance.delivery_person else None,
                        'status': instance.status
                    }
                },
                'delivered': {
                    'type': 'order_delivered',
                    'title': '¡Pedido entregado! ✅',
                    'message': f'Tu pedido #{instance.id} ha sido entregado exitosamente',
                    'priority': 2,
                    'user': instance.client,
                    'data': {
                        'order_id': instance.id,
                        'status': instance.status
                    }
                },
                'cancelled': {
                    'type': 'order_cancelled',
                    'title': 'Pedido cancelado ❌',
                    'message': f'Tu pedido #{instance.id} ha sido cancelado',
                    'priority': 1,
                    'user': instance.client,
                    'data': {
                        'order_id': instance.id,
                        'status': instance.status
                    }
                },
                'rejected': {
                    'type': 'order_rejected',
                    'title': 'Pedido rechazado',
                    'message': f'Tu pedido #{instance.id} ha sido rechazado por el restaurante',
                    'priority': 1,
                    'user': instance.client,
                    'data': {
                        'order_id': instance.id,
                        'status': instance.status
                    }
                }
            }
            
            if instance.status in status_handlers:
                handler = status_handlers[instance.status]
                
                # Notificar al cliente
                Notification.objects.create(
                    user=handler['user'],
                    type=handler['type'],
                    title=handler['title'],
                    message=handler['message'],
                    data=handler['data'],
                    priority=handler['priority']
                )
                
                logger.info(f"📨 Notificación {instance.status} creada para pedido #{instance.id}")
                
                # Notificaciones adicionales según estado
                if instance.status == 'ready':
                    # Notificar a repartidores disponibles
                    available_deliveries = User.objects.filter(
                        user_type='delivery',
                        is_active=True,
                        is_available=True
                    )
                    for delivery in available_deliveries:
                        Notification.objects.create(
                            user=delivery,
                            type='order_ready',
                            title='Pedido disponible para entregar 🛵',
                            message=f'Pedido #{instance.id} disponible en {instance.restaurant.restaurant_name}',
                            data={
                                'order_id': instance.id,
                                'restaurant_name': instance.restaurant.restaurant_name,
                                'restaurant_address': instance.restaurant.restaurant_address,
                                'status': instance.status
                            },
                            priority=1
                        )
                    logger.info(f"📨 Notificaciones enviadas a {available_deliveries.count()} repartidores")
                
                elif instance.status == 'delivered' and instance.delivery_person:
                    # Notificar al repartidor
                    Notification.objects.create(
                        user=instance.delivery_person,
                        type='order_delivered',
                        title='Pedido entregado ✅',
                        message=f'Has entregado el pedido #{instance.id}',
                        data={
                            'order_id': instance.id,
                            'status': instance.status
                        },
                        priority=1
                    )
                    
                elif instance.status == 'rejected':
                    # Notificar al restaurante
                    Notification.objects.create(
                        user=instance.restaurant,
                        type='order_rejected',
                        title='Pedido rechazado',
                        message=f'Has rechazado el pedido #{instance.id}',
                        data={
                            'order_id': instance.id,
                            'status': instance.status
                        },
                        priority=1
                    )
                    
    except Exception as e:
        logger.error(f"❌ Error creando notificaciones para pedido #{instance.id}: {e}")

# =============================================
# INTEGRACIÓN CON PUSH NOTIFICATIONS
# =============================================

from .push_service import PushNotificationService

@receiver(post_save, sender=Order)
def create_order_notification(sender, instance, created, **kwargs):
    """
    Crea notificaciones automáticas cuando cambia el estado de un pedido
    """
    # ... código existente ...
    
    # Agregar push notifications después de crear notificaciones en BD
    if created:
        # Notificar push al restaurante
        PushNotificationService.send_push_notification(
            user_id=instance.restaurant.id,
            title='¡Nuevo pedido! 📦',
            body=f'Cliente {instance.client.get_full_name()} realizó un pedido de ${instance.total}',
            data={
                'type': 'order_new',
                'order_id': instance.id,
                'screen': 'restaurant_orders',
            }
        )