from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from orders.models import Order
from .models import Conversation, ConversationParticipant, Message
from .services import ChatNotificationService


@receiver(post_save, sender=Order)
def create_conversation_for_order(sender, instance, created, **kwargs):
    """
    Crear automáticamente una conversación cuando se crea un pedido
    """
    if not created:
        return
    
    # Crear la conversación
    conversation = Conversation.objects.create(order=instance)
    
    # Agregar participantes automáticamente
    ConversationParticipant.objects.create(
        conversation=conversation,
        user=instance.client,
        role='client'
    )
    
    ConversationParticipant.objects.create(
        conversation=conversation,
        user=instance.restaurant,
        role='restaurant'
    )
    
    # Mensaje de sistema de bienvenida
    Message.objects.create(
        conversation=conversation,
        sender=instance.client,  # Sistema usa el cliente como sender
        message_type='system',
        content=f"Chat del pedido #{instance.id} creado. Aquí puedes comunicarte con el restaurante y el repartidor.",
        metadata={'system': True, 'event': 'conversation_created'}
    )
    
    print(f"✅ Conversación creada para pedido #{instance.id}")


@receiver(post_save, sender=Order)
def add_delivery_person_to_conversation(sender, instance, **kwargs):
    """
    Agregar repartidor a la conversación cuando se le asigna el pedido
    """
    if not instance.delivery_person:
        return
    
    try:
        conversation = instance.conversation
    except Conversation.DoesNotExist:
        return
    
    # Verificar si el repartidor ya es participante
    participant, created = ConversationParticipant.objects.get_or_create(
        conversation=conversation,
        user=instance.delivery_person,
        defaults={
            'role': 'delivery',
            'is_active': True,
        }
    )
    
    # Si es nuevo, crear mensaje de sistema y notificar
    if created:
        # Mensaje de sistema
        Message.objects.create(
            conversation=conversation,
            sender=instance.delivery_person,
            message_type='system',
            content=f"{instance.delivery_person.get_full_name() or instance.delivery_person.username} se ha unido al chat como repartidor.",
            metadata={'system': True, 'event': 'delivery_joined'}
        )
        
        # Notificar a los otros participantes
        ChatNotificationService.notify_new_message(
            conversation=conversation,
            message="El repartidor se ha unido al chat del pedido",
            exclude_user=instance.delivery_person
        )
        
        print(f"✅ Repartidor {instance.delivery_person.username} agregado al chat del pedido #{instance.id}")


@receiver(post_save, sender=Order)
def close_conversation_on_order_completion(sender, instance, **kwargs):
    """
    Cerrar la conversación cuando el pedido se completa
    """
    if instance.status in ['delivered', 'cancelled', 'rejected']:
        try:
            conversation = instance.conversation
            if conversation.is_active:
                conversation.is_active = False
                conversation.closed_at = timezone.now()
                conversation.save()
                
                # Mensaje de sistema
                Message.objects.create(
                    conversation=conversation,
                    sender=instance.client,
                    message_type='system',
                    content=f"El pedido ha sido {instance.get_status_display().lower()}. El chat se ha cerrado.",
                    metadata={'system': True, 'event': 'conversation_closed'}
                )
                
                print(f"🔒 Conversación cerrada para pedido #{instance.id}")
        except Conversation.DoesNotExist:
            pass