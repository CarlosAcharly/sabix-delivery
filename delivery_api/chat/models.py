from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


class Conversation(models.Model):
    """
    Conversación única por pedido
    Un pedido = una conversación
    """
    order = models.OneToOneField(
        'orders.Order',
        on_delete=models.CASCADE,
        related_name='conversation',
        verbose_name=_('Pedido')
    )
    is_active = models.BooleanField(default=True, verbose_name=_('Activa'))
    is_support_requested = models.BooleanField(
        default=False,
        verbose_name=_('Soporte solicitado')
    )
    support_requested_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Soporte solicitado en')
    )
    support_requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='support_requests_made',
        verbose_name=_('Solicitado por')
    )
    closed_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Cerrada en'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Creada'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Actualizada'))
    
    class Meta:
        db_table = 'chat_conversations'
        verbose_name = _('Conversación')
        verbose_name_plural = _('Conversaciones')
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"Chat Pedido #{self.order.id}"
    
    @property
    def last_message(self):
        return self.messages.filter(is_deleted=False).order_by('-created_at').first()


class ConversationParticipant(models.Model):
    """
    Participantes de una conversación
    """
    ROLE_CHOICES = (
        ('client', 'Cliente'),
        ('restaurant', 'Sucursal'),
        ('delivery', 'Repartidor'),
        ('support', 'Soporte'),
    )
    
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='participants',
        verbose_name=_('Conversación')
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='chat_participations',
        verbose_name=_('Usuario')
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        verbose_name=_('Rol')
    )
    is_active = models.BooleanField(default=True, verbose_name=_('Activo'))
    joined_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Se unió en'))
    left_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Salió en'))
    last_read_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Última lectura')
    )
    
    class Meta:
        db_table = 'chat_participants'
        verbose_name = _('Participante')
        verbose_name_plural = _('Participantes')
        unique_together = ['conversation', 'user']
        ordering = ['joined_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"


class Message(models.Model):
    """
    Mensajes dentro de una conversación
    """
    MESSAGE_TYPES = (
        ('text', 'Texto'),
        ('image', 'Imagen'),
        ('file', 'Archivo'),
        ('system', 'Sistema'),
        ('location', 'Ubicación'),
    )
    
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name=_('Conversación')
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='chat_messages',
        verbose_name=_('Remitente')
    )
    message_type = models.CharField(
        max_length=20,
        choices=MESSAGE_TYPES,
        default='text',
        verbose_name=_('Tipo de mensaje')
    )
    content = models.TextField(verbose_name=_('Contenido'))
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Metadatos')
    )
    reply_to = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='replies',
        verbose_name=_('Responder a')
    )
    is_edited = models.BooleanField(default=False, verbose_name=_('Editado'))
    edited_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Editado en'))
    is_deleted = models.BooleanField(default=False, verbose_name=_('Eliminado'))
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Eliminado en'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Creado'))
    
    class Meta:
        db_table = 'chat_messages'
        verbose_name = _('Mensaje')
        verbose_name_plural = _('Mensajes')
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['conversation', '-created_at']),
            models.Index(fields=['sender', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.sender.username}: {self.content[:50]}"


class MessageRead(models.Model):
    """
    Registro de lectura de mensajes
    """
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name='reads',
        verbose_name=_('Mensaje')
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='message_reads',
        verbose_name=_('Usuario')
    )
    read_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Leído en'))
    
    class Meta:
        db_table = 'chat_message_reads'
        verbose_name = _('Lectura de mensaje')
        verbose_name_plural = _('Lecturas de mensajes')
        unique_together = ['message', 'user']
        ordering = ['-read_at']


class SupportRequest(models.Model):
    """
    Solicitudes de soporte dentro de una conversación
    """
    STATUS_CHOICES = (
        ('pending', 'Pendiente'),
        ('in_progress', 'En proceso'),
        ('resolved', 'Resuelto'),
        ('closed', 'Cerrado'),
    )
    
    PRIORITY_CHOICES = (
        ('low', 'Baja'),
        ('medium', 'Media'),
        ('high', 'Alta'),
        ('urgent', 'Urgente'),
    )
    
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='support_requests',
        verbose_name=_('Conversación')
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='support_requests',
        verbose_name=_('Solicitado por')
    )
    reason = models.TextField(verbose_name=_('Motivo'))
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='medium',
        verbose_name=_('Prioridad')
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name=_('Estado')
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_support_requests',
        verbose_name=_('Asignado a')
    )
    resolution_notes = models.TextField(blank=True, verbose_name=_('Notas de resolución'))
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Resuelto en'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Creado'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Actualizado'))
    
    class Meta:
        db_table = 'chat_support_requests'
        verbose_name = _('Solicitud de soporte')
        verbose_name_plural = _('Solicitudes de soporte')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Soporte #{self.id} - Pedido #{self.conversation.order.id} - {self.get_status_display()}"
    
    def resolve(self, user, notes=''):
        self.status = 'resolved'
        self.resolved_at = timezone.now()
        self.resolution_notes = notes
        self.save()