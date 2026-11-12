from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from decimal import Decimal
import uuid

class PlatformSettings(models.Model):
    """
    Configuración global de comisiones (solo una instancia)
    """
    platform_fee_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('10.00'),
        help_text=_('Porcentaje que se lleva la plataforma por pedido')
    )
    delivery_fee_fixed = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('20.00'),
        help_text=_('Pago base para el repartidor por pedido entregado')
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payments_platform_settings'
        verbose_name = _('Configuración de Plataforma')

    def __str__(self):
        return f"Configuración Global (Plataforma: {self.platform_fee_percentage}%, Repartidor: ${self.delivery_fee_fixed})"

    def save(self, *args, **kwargs):
        # Asegurar que solo haya una instancia
        self.id = 1
        super().save(*args, **kwargs)


class Payment(models.Model):
    """
    Transacción de pago simulada
    """
    STATUS_CHOICES = (
        ('pending', 'Pendiente'),
        ('completed', 'Completado'),
        ('failed', 'Fallido'),
        ('refunded', 'Reembolsado'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.OneToOneField(
        'orders.Order', 
        on_delete=models.CASCADE, 
        related_name='payment'
    )
    
    # Desglose del pago
    product_amount = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_amount = models.DecimalField(max_digits=10, decimal_places=2)
    platform_fee_amount = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Simulación de pasarela
    payment_method = models.CharField(max_length=50, default='simulated_card')
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payments_payment'

    def __str__(self):
        return f"Pago {self.id} - Pedido #{self.order.id} - ${self.total_amount} ({self.get_status_display()})"

class Order(models.Model):
    # ... tus campos existentes (subtotal, delivery_fee, total, etc.) ...

    # ✅ NUEVOS CAMPOS PARA DESGLOSE DE PAGOS
    delivery_person_earnings = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name=_('Ganancia del Repartidor')
    )
    restaurant_earnings = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name=_('Ganancia del Restaurante')
    )
    platform_earnings = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name=_('Ganancia de la Plataforma')
    )