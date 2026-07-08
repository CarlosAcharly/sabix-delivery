from rest_framework import serializers
from django.db.models import Avg, Count
from .models import (
    Category, RestaurantCategory, Product, 
    ProductOption, ProductOptionChoice
)
from users.serializers import UserSerializer

# =============================================
# SERIALIZERS DE CATEGORÍAS
# =============================================

class CategorySerializer(serializers.ModelSerializer):
    """Serializer para categorías globales (admin)"""
    product_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = [
            'id', 'name', 'description', 'icon', 
            'is_active', 'product_count', 'created_at'
        ]
        read_only_fields = ['created_at']
    
    def get_product_count(self, obj):
        return obj.products.filter(is_available=True).count()

class RestaurantCategorySerializer(serializers.ModelSerializer):
    """Serializer para categorías de restaurantes"""
    product_count = serializers.SerializerMethodField()
    
    class Meta:
        model = RestaurantCategory
        fields = [
            'id', 'restaurant', 'name', 'description', 
            'is_active', 'order', 'product_count', 'created_at'
        ]
        read_only_fields = ['restaurant', 'created_at']
    
    def get_product_count(self, obj):
        return obj.products.filter(is_available=True).count()

# =============================================
# SERIALIZERS DE PRODUCTOS
# =============================================

class ProductOptionChoiceSerializer(serializers.ModelSerializer):
    """Serializer para opciones de elección"""
    class Meta:
        model = ProductOptionChoice
        fields = ['id', 'value', 'price_adjustment', 'is_default', 'order']

class ProductOptionSerializer(serializers.ModelSerializer):
    """Serializer para opciones de producto"""
    choices = ProductOptionChoiceSerializer(many=True, read_only=True)
    
    class Meta:
        model = ProductOption
        fields = [
            'id', 'name', 'option_type', 'is_required', 
            'max_choices', 'choices', 'created_at'
        ]

class ProductSerializer(serializers.ModelSerializer):
    """Serializer principal para productos"""
    restaurant_name = serializers.SerializerMethodField()
    category_name = serializers.SerializerMethodField()
    global_category_name = serializers.SerializerMethodField()
    final_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    has_discount = serializers.BooleanField(read_only=True)
    options = ProductOptionSerializer(many=True, read_only=True)
    average_rating = serializers.SerializerMethodField()
    total_reviews = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'restaurant', 'restaurant_name', 'category', 'category_name',
            'global_category', 'global_category_name', 'name', 'description',
            'price', 'discount_price', 'final_price', 'has_discount',
            'image', 'image_alt', 'is_available', 'is_featured', 'stock',
            'preparation_time', 'is_vegetarian', 'is_vegan', 'is_gluten_free',
            'order', 'options', 'average_rating', 'total_reviews', 
            'created_at', 'updated_at'
        ]
        read_only_fields = ['restaurant', 'created_at', 'updated_at']
    
    def get_restaurant_name(self, obj):
        return obj.restaurant.restaurant_name if obj.restaurant else None
    
    def get_category_name(self, obj):
        return obj.category.name if obj.category else None
    
    def get_global_category_name(self, obj):
        return obj.global_category.name if obj.global_category else None
    
    def get_average_rating(self, obj):
        # Aquí calcularías el rating promedio (lo implementaremos después)
        return None
    
    def get_total_reviews(self, obj):
        # Aquí contarías las reviews (lo implementaremos después)
        return 0

class ProductCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear/actualizar productos (restaurante)"""
    
    class Meta:
        model = Product
        fields = [
            'name', 'description', 'price', 'discount_price',
            'category', 'global_category', 'image', 'image_alt',
            'is_available', 'is_featured', 'stock', 'preparation_time',
            'is_vegetarian', 'is_vegan', 'is_gluten_free', 'order'
        ]
    
    def validate(self, data):
        # Validar que el precio con descuento sea menor que el precio normal
        if data.get('discount_price') and data.get('price'):
            if data['discount_price'] >= data['price']:
                raise serializers.ValidationError({
                    'discount_price': 'El precio con descuento debe ser menor que el precio normal.'
                })
        return data
    
    def create(self, validated_data):
        # Asignar el restaurante automáticamente
        validated_data['restaurant'] = self.context['request'].user
        return super().create(validated_data)

class ProductListSerializer(serializers.ModelSerializer):
    """Serializer ligero para listar productos"""
    restaurant_name = serializers.SerializerMethodField()
    category_name = serializers.SerializerMethodField()
    final_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'price', 'discount_price', 
            'final_price', 'image', 'image_url', 'is_available', 
            'is_featured', 'restaurant_name', 'category_name',
            'average_rating', 'created_at'
        ]
    
    def get_restaurant_name(self, obj):
        return obj.restaurant.restaurant_name if obj.restaurant else None
    
    def get_category_name(self, obj):
        return obj.category.name if obj.category else None
    
    def get_image_url(self, obj):
        if obj.image and hasattr(obj.image, 'url'):
            return obj.image.url
        return None
    
    def get_average_rating(self, obj):
        # Aquí calcularías el rating promedio
        return None