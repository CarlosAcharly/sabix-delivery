from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator

class Notification(models.Model):
    """
    Modelo principal de notificaciones
    """
    # =============================================
    # TIPOS DE NOTIFICACIÓN
    # =============================================
    TYPE_CHOICES = (
        # Pedidos
        ('order_new', 'Nuevo pedido'),
        ('order_confirmed', 'Pedido confirmado'),
        ('order_preparing', 'Pedido en preparación'),
        ('order_ready', 'Pedido listo para entregar'),
        ('order_in_delivery', 'Pedido en camino'),
        ('order_delivered', 'Pedido entregado'),
        ('order_cancelled', 'Pedido cancelado'),
        ('order_rejected', 'Pedido rechazado'),
        ('order_rated', 'Pedido calificado'),
        
        # Promociones
        ('promotion', 'Promoción especial'),
        ('discount', 'Descuento disponible'),
        
        # Sistema
        ('system', 'Notificación del sistema'),
        ('reminder', 'Recordatorio'),
        ('update', 'Actualización de la plataforma'),
        
        # Usuarios
        ('welcome', 'Bienvenida'),
        ('verification', 'Verificación de cuenta'),
        ('password_changed', 'Contraseña cambiada'),
    )
    
    # =============================================
    # PRIORIDADES
    # =============================================
    PRIORITY_CHOICES = (
        (0, 'Normal'),
        (1, 'Alta'),
        (2, 'Urgente'),
    )
    
    # =============================================
    # RELACIONES
    # =============================================
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name=_('Usuario')
    )
    order = models.ForeignKey(
        'orders.Order',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications',
        verbose_name=_('Pedido')
    )
    
    # =============================================
    # CONTENIDO
    # =============================================
    type = models.CharField(
        max_length=50,
        choices=TYPE_CHOICES,
        verbose_name=_('Tipo')
    )
    title = models.CharField(max_length=200, verbose_name=_('Título'))
    message = models.TextField(verbose_name=_('Mensaje'))
    data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Datos adicionales'),
        help_text=_('Datos estructurados para la notificación')
    )
    
    # =============================================
    # ESTADO
    # =============================================
    is_read = models.BooleanField(default=False, verbose_name=_('Leída'))
    is_archived = models.BooleanField(default=False, verbose_name=_('Archivada'))
    priority = models.IntegerField(
        choices=PRIORITY_CHOICES,
        default=0,
        verbose_name=_('Prioridad')
    )
    
    # =============================================
    # TIEMPOS
    # =============================================
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Creada'))
    read_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Leída en'))
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Expira en'),
        help_text=_('Fecha de expiración de la notificación')
    )
    
    class Meta:
        db_table = 'notifications'
        verbose_name = _('Notificación')
        verbose_name_plural = _('Notificaciones')
        ordering = ['-priority', '-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['type']),
        ]
    
    def __str__(self):
        return f"{self.get_type_display()}: {self.title}"
    
    # =============================================
    # MÉTODOS
    # =============================================
    
    def mark_as_read(self):
        """Marca la notificación como leída"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()
    
    def mark_as_unread(self):
        """Marca la notificación como no leída"""
        if self.is_read:
            self.is_read = False
            self.read_at = None
            self.save()
    
    def archive(self):
        """Archiva la notificación"""
        self.is_archived = True
        self.save()
    
    @property
    def is_expired(self):
        """Verifica si la notificación ha expirado"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    @property
    def time_ago(self):
        """Retorna el tiempo transcurrido desde la creación"""
        from django.utils.timesince import timesince
        return timesince(self.created_at)


class NotificationPreference(models.Model):
    """
    Preferencias de notificaciones por usuario
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_preferences',
        verbose_name=_('Usuario')
    )
    
    # =============================================
    # CANALES HABILITADOS
    # =============================================
    push_enabled = models.BooleanField(default=True, verbose_name=_('Notificaciones push'))
    email_enabled = models.BooleanField(default=True, verbose_name=_('Notificaciones por email'))
    sms_enabled = models.BooleanField(default=False, verbose_name=_('Notificaciones por SMS'))
    in_app_enabled = models.BooleanField(default=True, verbose_name=_('Notificaciones en app'))
    
    # =============================================
    # TIPOS DE NOTIFICACIONES HABILITADOS
    # =============================================
    order_notifications = models.BooleanField(default=True, verbose_name=_('Notificaciones de pedidos'))
    promotion_notifications = models.BooleanField(default=True, verbose_name=_('Notificaciones de promociones'))
    system_notifications = models.BooleanField(default=True, verbose_name=_('Notificaciones del sistema'))
    
    # =============================================
    # CONFIGURACIONES AVANZADAS
    # =============================================
    quiet_hours_start = models.TimeField(
        null=True,
        blank=True,
        verbose_name=_('Inicio de horas silenciosas')
    )
    quiet_hours_end = models.TimeField(
        null=True,
        blank=True,
        verbose_name=_('Fin de horas silenciosas')
    )
    
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Actualizado'))
    
    class Meta:
        db_table = 'notification_preferences'
        verbose_name = _('Preferencia de notificaciones')
        verbose_name_plural = _('Preferencias de notificaciones')
    
    def __str__(self):
        return f"Preferencias de {self.user.username}"
    
    def is_quiet_hours(self):
        """Verifica si está en horas silenciosas"""
        if not self.quiet_hours_start or not self.quiet_hours_end:
            return False
        
        now = timezone.now().time()
        if self.quiet_hours_start < self.quiet_hours_end:
            return self.quiet_hours_start <= now <= self.quiet_hours_end
        else:
            return now >= self.quiet_hours_start or now <= self.quiet_hours_end


class DeviceToken(models.Model):
    """
    Tokens de dispositivos para notificaciones push
    """
    DEVICE_TYPES = (
        ('android', 'Android'),
        ('ios', 'iOS'),
        ('web', 'Web'),
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='device_tokens',
        verbose_name=_('Usuario')
    )
    token = models.CharField(
        max_length=255,
        unique=True,
        verbose_name=_('Token')
    )
    device_type = models.CharField(
        max_length=20,
        choices=DEVICE_TYPES,
        verbose_name=_('Tipo de dispositivo')
    )
    device_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_('Nombre del dispositivo')
    )
    is_active = models.BooleanField(default=True, verbose_name=_('Activo'))
    last_used = models.DateTimeField(auto_now=True, verbose_name=_('Último uso'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Creado'))
    
    class Meta:
        db_table = 'device_tokens'
        verbose_name = _('Token de dispositivo')
        verbose_name_plural = _('Tokens de dispositivos')
        unique_together = ['user', 'token']
    
    def __str__(self):
        return f"{self.device_type} - {self.user.username}"