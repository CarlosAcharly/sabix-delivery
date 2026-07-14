from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

class Order(models.Model):
    """
    Modelo principal de pedidos
    """
    # =============================================
    # ESTADOS DEL PEDIDO
    # =============================================
    STATUS_CHOICES = (
        ('pending', 'Pendiente'),
        ('confirmed', 'Confirmado'),
        ('preparing', 'En preparación'),
        ('ready', 'Listo para entregar'),
        ('in_delivery', 'En camino'),
        ('delivered', 'Entregado'),
        ('cancelled', 'Cancelado'),
        ('rejected', 'Rechazado'),
    )
    
    # =============================================
    # RELACIONES
    # =============================================
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='orders_as_client',
        limit_choices_to={'user_type': 'client'},
        verbose_name=_('Cliente')
    )
    restaurant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='orders_as_restaurant',
        limit_choices_to={'user_type': 'restaurant'},
        verbose_name=_('Restaurante')
    )
    delivery_person = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders_as_delivery',
        limit_choices_to={'user_type': 'delivery'},
        verbose_name=_('Repartidor')
    )
    
    # =============================================
    # INFORMACIÓN DEL PEDIDO
    # =============================================
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name=_('Estado')
    )
    
    # Totales
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_('Subtotal')
    )
    delivery_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name=_('Costo de envío')
    )
    total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_('Total')
    )
    
    # =============================================
    # DIRECCIÓN DE ENTREGA
    # =============================================
    delivery_address = models.TextField(verbose_name=_('Dirección de entrega'))
    delivery_lat = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
        verbose_name=_('Latitud')
    )
    delivery_lng = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
        verbose_name=_('Longitud')
    )
    delivery_notes = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Notas de entrega')
    )
    
    # =============================================
    # PAGO
    # =============================================
    PAYMENT_METHODS = (
        ('cash', 'Efectivo'),
        ('card', 'Tarjeta'),
        ('online', 'Pago en línea'),
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHODS,
        default='cash',
        verbose_name=_('Método de pago')
    )
    is_paid = models.BooleanField(default=False, verbose_name=_('Pagado'))
    payment_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_('ID de pago')
    )
    
    # =============================================
    # TIEMPOS
    # =============================================
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Creado'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Actualizado'))
    
    confirmed_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Confirmado'))
    preparing_at = models.DateTimeField(null=True, blank=True, verbose_name=_('En preparación'))
    ready_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Listo'))
    in_delivery_at = models.DateTimeField(null=True, blank=True, verbose_name=_('En camino'))
    delivered_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Entregado'))
    cancelled_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Cancelado'))
    
    estimated_delivery_time = models.IntegerField(
        default=30,
        help_text=_('Tiempo estimado en minutos'),
        verbose_name=_('Tiempo estimado de entrega')
    )
    
    # =============================================
    # INFORMACIÓN ADICIONAL
    # =============================================
    notes = models.TextField(blank=True, null=True, verbose_name=_('Notas'))
    client_rating = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name=_('Calificación del cliente')
    )
    client_comment = models.TextField(blank=True, null=True, verbose_name=_('Comentario del cliente'))
    
    class Meta:
        db_table = 'orders'
        verbose_name = _('Pedido')
        verbose_name_plural = _('Pedidos')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['client', 'status']),
            models.Index(fields=['restaurant', 'status']),
            models.Index(fields=['delivery_person', 'status']),
        ]
    
    def __str__(self):
        return f"Pedido #{self.id} - {self.client.username} - {self.get_status_display()}"
    
    # =============================================
    # MÉTODOS DE NEGOCIO
    # =============================================
    
    def calculate_total(self):
        """Calcula el total del pedido"""
        items_total = self.items.aggregate(
            total=models.Sum('total')
        )['total'] or Decimal('0.00')
        
        self.subtotal = items_total
        self.total = items_total + self.delivery_fee
        return self.total
    
    def update_status(self, new_status):
        """Actualiza el estado del pedido y las marcas de tiempo"""
        self.status = new_status
        
        # Actualizar timestamps según el estado
        if new_status == 'confirmed' and not self.confirmed_at:
            self.confirmed_at = models.functions.Now()
        elif new_status == 'preparing' and not self.preparing_at:
            self.preparing_at = models.functions.Now()
        elif new_status == 'ready' and not self.ready_at:
            self.ready_at = models.functions.Now()
        elif new_status == 'in_delivery' and not self.in_delivery_at:
            self.in_delivery_at = models.functions.Now()
        elif new_status == 'delivered' and not self.delivered_at:
            self.delivered_at = models.functions.Now()
        elif new_status in ['cancelled', 'rejected'] and not self.cancelled_at:
            self.cancelled_at = models.functions.Now()
        
        self.save()
    
    def can_cancel(self):
        """Verifica si el pedido puede ser cancelado"""
        return self.status in ['pending', 'confirmed']
    
    def can_accept(self):
        """Verifica si el pedido puede ser aceptado"""
        return self.status == 'pending'
    
    def can_reject(self):
        """Verifica si el pedido puede ser rechazado"""
        return self.status == 'pending'
    
    def can_prepare(self):
        """Verifica si el pedido puede ser preparado"""
        return self.status == 'confirmed'
    
    def can_ready(self):
        """Verifica si el pedido puede marcarse como listo"""
        return self.status == 'preparing'
    
    def can_deliver(self):
        """Verifica si el pedido puede ser entregado"""
        return self.status == 'in_delivery'
    
    def can_assign_delivery(self):
        """Verifica si se puede asignar un repartidor"""
        return self.status == 'ready'
    
    @property
    def status_display(self):
        """Retorna el nombre legible del estado"""
        return dict(self.STATUS_CHOICES).get(self.status, self.status)
    
    @property
    def total_items(self):
        """Retorna la cantidad total de items en el pedido"""
        return self.items.aggregate(total=models.Sum('quantity'))['total'] or 0
    
    @property
    def is_completed(self):
        """Verifica si el pedido está completado"""
        return self.status in ['delivered', 'cancelled', 'rejected']
    
    @property
    def is_active(self):
        """Verifica si el pedido está activo"""
        return self.status not in ['delivered', 'cancelled', 'rejected']


class OrderItem(models.Model):
    """
    Items dentro de un pedido
    """
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name=_('Pedido')
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE,
        related_name='order_items',
        verbose_name=_('Producto')
    )
    
    # Información del producto al momento del pedido (precio congelado)
    product_name = models.CharField(max_length=200, verbose_name=_('Nombre del producto'))
    product_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_('Precio unitario')
    )
    
    quantity = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        verbose_name=_('Cantidad')
    )
    total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_('Total')
    )
    
    # Opciones seleccionadas (JSON)
    selected_options = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Opciones seleccionadas')
    )
    
    # Notas del item
    notes = models.TextField(blank=True, null=True, verbose_name=_('Notas'))
    
    class Meta:
        db_table = 'order_items'
        verbose_name = _('Item del pedido')
        verbose_name_plural = _('Items del pedido')
    
    def __str__(self):
        return f"{self.product_name} x{self.quantity} - Pedido #{self.order.id}"
    
    def save(self, *args, **kwargs):
        """Calcula el total antes de guardar"""
        self.total = self.product_price * self.quantity
        super().save(*args, **kwargs)


class DeliveryTracking(models.Model):
    """
    Seguimiento de entregas en tiempo real
    """
    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name='tracking',
        verbose_name=_('Pedido')
    )
    
    # Ubicación actual
    current_lat = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        verbose_name=_('Latitud actual')
    )
    current_lng = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        verbose_name=_('Longitud actual')
    )
    
    # Historial de ubicaciones (JSON)
    location_history = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_('Historial de ubicaciones')
    )
    
    # Última actualización
    last_update = models.DateTimeField(auto_now=True, verbose_name=_('Última actualización'))
    
    class Meta:
        db_table = 'delivery_tracking'
        verbose_name = _('Seguimiento de entrega')
        verbose_name_plural = _('Seguimientos de entregas')
    
    def __str__(self):
        return f"Seguimiento Pedido #{self.order.id}"
    
    def update_location(self, lat, lng):
        """Actualiza la ubicación y agrega al historial"""
        self.current_lat = lat
        self.current_lng = lng
        
        # Agregar al historial
        from django.utils import timezone
        history_entry = {
            'lat': str(lat),
            'lng': str(lng),
            'timestamp': timezone.now().isoformat()
        }
        
        # Mantener solo los últimos 100 registros
        history = self.location_history or []
        history.append(history_entry)
        if len(history) > 100:
            history = history[-100:]
        self.location_history = history
        
        self.save()