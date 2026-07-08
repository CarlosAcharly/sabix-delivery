from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator

class Category(models.Model):
    """
    Modelo de categoría de productos (global)
    Administrado por el admin de la plataforma
    """
    name = models.CharField(max_length=100, verbose_name=_('Nombre'))
    description = models.TextField(blank=True, null=True, verbose_name=_('Descripción'))
    icon = models.CharField(max_length=50, blank=True, null=True, verbose_name=_('Icono'))
    is_active = models.BooleanField(default=True, verbose_name=_('Activo'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'categories'
        verbose_name = _('Categoría')
        verbose_name_plural = _('Categorías')
        ordering = ['name']
    
    def __str__(self):
        return self.name

class RestaurantCategory(models.Model):
    """
    Modelo de categoría específica de un restaurante
    Cada restaurante puede tener sus propias categorías
    """
    restaurant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'user_type': 'restaurant'},
        related_name='restaurant_categories',
        verbose_name=_('Restaurante')
    )
    name = models.CharField(max_length=100, verbose_name=_('Nombre'))
    description = models.TextField(blank=True, null=True, verbose_name=_('Descripción'))
    is_active = models.BooleanField(default=True, verbose_name=_('Activo'))
    order = models.IntegerField(default=0, verbose_name=_('Orden'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'restaurant_categories'
        verbose_name = _('Categoría de Restaurante')
        verbose_name_plural = _('Categorías de Restaurantes')
        ordering = ['restaurant', 'order', 'name']
        unique_together = ['restaurant', 'name']  # Un restaurante no puede tener categorías con el mismo nombre
    
    def __str__(self):
        return f"{self.restaurant.restaurant_name} - {self.name}"

class Product(models.Model):
    """
    Modelo de producto
    Cada producto pertenece a un restaurante y puede tener una categoría
    """
    # Relaciones
    restaurant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'user_type': 'restaurant'},
        related_name='products',
        verbose_name=_('Restaurante')
    )
    category = models.ForeignKey(
        RestaurantCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products',
        verbose_name=_('Categoría')
    )
    global_category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products',
        verbose_name=_('Categoría Global')
    )
    
    # Información básica
    name = models.CharField(max_length=200, verbose_name=_('Nombre'))
    description = models.TextField(verbose_name=_('Descripción'))
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name=_('Precio')
    )
    discount_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        verbose_name=_('Precio con descuento')
    )
    
    # Imágenes
    image = models.ImageField(
        upload_to='products/',
        null=True,
        blank=True,
        verbose_name=_('Imagen')
    )
    image_alt = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name=_('Texto alternativo de imagen')
    )
    
    # Disponibilidad
    is_available = models.BooleanField(default=True, verbose_name=_('Disponible'))
    is_featured = models.BooleanField(default=False, verbose_name=_('Destacado'))
    stock = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name=_('Stock')
    )
    
    # Opciones adicionales
    preparation_time = models.IntegerField(
        default=15,
        help_text=_('Tiempo de preparación en minutos'),
        verbose_name=_('Tiempo de preparación')
    )
    is_vegetarian = models.BooleanField(default=False, verbose_name=_('Vegetariano'))
    is_vegan = models.BooleanField(default=False, verbose_name=_('Vegano'))
    is_gluten_free = models.BooleanField(default=False, verbose_name=_('Sin gluten'))
    
    # Metadatos
    order = models.IntegerField(default=0, verbose_name=_('Orden'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'products'
        verbose_name = _('Producto')
        verbose_name_plural = _('Productos')
        ordering = ['restaurant', 'category', 'order', 'name']
        unique_together = ['restaurant', 'name']  # Un restaurante no puede tener productos con el mismo nombre
    
    def __str__(self):
        return f"{self.restaurant.restaurant_name} - {self.name}"
    
    @property
    def final_price(self):
        """Retorna el precio final (con descuento si existe)"""
        return self.discount_price if self.discount_price else self.price
    
    @property
    def has_discount(self):
        """Verifica si el producto tiene descuento"""
        return self.discount_price is not None and self.discount_price < self.price

class ProductOption(models.Model):
    """
    Opciones personalizables para productos (ej: tamaño, sabor, extras)
    """
    OPTION_TYPES = (
        ('size', 'Tamaño'),
        ('flavor', 'Sabor'),
        ('extra', 'Extra'),
        ('custom', 'Personalizado'),
    )
    
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='options',
        verbose_name=_('Producto')
    )
    name = models.CharField(max_length=100, verbose_name=_('Nombre'))
    option_type = models.CharField(
        max_length=20,
        choices=OPTION_TYPES,
        default='custom',
        verbose_name=_('Tipo de opción')
    )
    is_required = models.BooleanField(default=False, verbose_name=_('Requerido'))
    max_choices = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        verbose_name=_('Máximo de elecciones')
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'product_options'
        verbose_name = _('Opción de Producto')
        verbose_name_plural = _('Opciones de Productos')
    
    def __str__(self):
        return f"{self.product.name} - {self.name}"

class ProductOptionChoice(models.Model):
    """
    Opciones disponibles dentro de una opción (ej: "Pequeño", "Mediano", "Grande")
    """
    option = models.ForeignKey(
        ProductOption,
        on_delete=models.CASCADE,
        related_name='choices',
        verbose_name=_('Opción')
    )
    value = models.CharField(max_length=100, verbose_name=_('Valor'))
    price_adjustment = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name=_('Ajuste de precio')
    )
    is_default = models.BooleanField(default=False, verbose_name=_('Por defecto'))
    order = models.IntegerField(default=0, verbose_name=_('Orden'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'product_option_choices'
        verbose_name = _('Opción de elección')
        verbose_name_plural = _('Opciones de elección')
        ordering = ['option', 'order', 'value']
        unique_together = ['option', 'value']
    
    def __str__(self):
        return f"{self.option.name} - {self.value}"