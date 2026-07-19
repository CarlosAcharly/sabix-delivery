from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from orders.models import Order, OrderItem
from .models import Notification

User = get_user_model()

@receiver(post_save, sender=Order)
def create_order_notification(sender, instance, created, **kwargs):
    """
    Crea notificaciones automáticas cuando cambia el estado de un pedido
    """
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
                'items_count': instance.items.count(),
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
    
    else:
        # Verificar cambios de estado
        if instance.status == 'confirmed':
            # Notificar al cliente: Pedido confirmado
            Notification.objects.create(
                user=instance.client,
                type='order_confirmed',
                title='¡Pedido confirmado! 🍕',
                message=f'Tu pedido #{instance.id} ha sido confirmado por {instance.restaurant.restaurant_name}',
                data={
                    'order_id': instance.id,
                    'restaurant_name': instance.restaurant.restaurant_name,
                    'status': instance.status
                },
                priority=1
            )
        
        elif instance.status == 'preparing':
            Notification.objects.create(
                user=instance.client,
                type='order_preparing',
                title='Tu pedido se está preparando 👨‍🍳',
                message=f'El restaurante está preparando tu pedido #{instance.id}',
                data={
                    'order_id': instance.id,
                    'status': instance.status
                },
                priority=1
            )
        
        elif instance.status == 'ready':
            Notification.objects.create(
                user=instance.client,
                type='order_ready',
                title='¡Pedido listo para entregar! 🎯',
                message=f'Tu pedido #{instance.id} está listo y espera al repartidor',
                data={
                    'order_id': instance.id,
                    'status': instance.status
                },
                priority=1
            )
            
            # Notificar a repartidores disponibles
            # Aquí iría lógica para notificar a repartidores
            from users.models import User
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
        
        elif instance.status == 'in_delivery':
            Notification.objects.create(
                user=instance.client,
                type='order_in_delivery',
                title='Tu pedido está en camino 🚀',
                message=f'El repartidor está llevando tu pedido #{instance.id}',
                data={
                    'order_id': instance.id,
                    'delivery_person': instance.delivery_person.get_full_name() if instance.delivery_person else None,
                    'status': instance.status
                },
                priority=2
            )
        
        elif instance.status == 'delivered':
            Notification.objects.create(
                user=instance.client,
                type='order_delivered',
                title='¡Pedido entregado! ✅',
                message=f'Tu pedido #{instance.id} ha sido entregado exitosamente',
                data={
                    'order_id': instance.id,
                    'status': instance.status
                },
                priority=2
            )
            
            # Notificar al repartidor
            if instance.delivery_person:
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
        
        elif instance.status in ['cancelled', 'rejected']:
            Notification.objects.create(
                user=instance.client,
                type='order_cancelled',
                title='Pedido cancelado ❌',
                message=f'Tu pedido #{instance.id} ha sido cancelado',
                data={
                    'order_id': instance.id,
                    'status': instance.status
                },
                priority=1
            )
            
            if instance.status == 'rejected':
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