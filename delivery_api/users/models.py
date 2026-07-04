from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

class User(AbstractUser):
    # Tipos de usuario
    USER_TYPE_CHOICES = (
        ('client', 'Cliente'),
        ('delivery', 'Repartidor'),
        ('restaurant', 'Restaurante'),
        ('admin', 'Administrador'),
    )
    
    user_type = models.CharField(
        max_length=20,
        choices=USER_TYPE_CHOICES,
        default='client',
        verbose_name=_('Tipo de usuario')
    )
    
    # Campos comunes
    phone = models.CharField(max_length=20, blank=True, null=True)
    profile_image = models.ImageField(upload_to='profiles/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Campos específicos para cliente
    address = models.TextField(blank=True, null=True)
    preferred_payment_method = models.CharField(max_length=50, blank=True, null=True)
    
    # Campos específicos para repartidor
    vehicle_type = models.CharField(max_length=50, blank=True, null=True)
    vehicle_plate = models.CharField(max_length=20, blank=True, null=True)
    is_available = models.BooleanField(default=True)
    current_location_lat = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    current_location_lng = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    
    # Campos específicos para restaurante
    restaurant_name = models.CharField(max_length=200, blank=True, null=True)
    restaurant_description = models.TextField(blank=True, null=True)
    restaurant_address = models.TextField(blank=True, null=True)
    restaurant_phone = models.CharField(max_length=20, blank=True, null=True)
    is_restaurant_verified = models.BooleanField(default=False)
    
    # Relaciones
    parent_restaurant = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='employees',
        verbose_name=_('Restaurante padre')
    )
    
    class Meta:
        db_table = 'users'
        verbose_name = _('Usuario')
        verbose_name_plural = _('Usuarios')
        
    def __str__(self):
        return f"{self.get_full_name() or self.username} - {self.get_user_type_display()}"
    
    @property
    def is_restaurant_owner(self):
        return self.user_type == 'restaurant'
    
    @property
    def is_delivery_person(self):
        return self.user_type == 'delivery'
    
    @property
    def is_client(self):
        return self.user_type == 'client'
    
    @property
    def is_admin_user(self):
        return self.user_type == 'admin' or self.is_superuser