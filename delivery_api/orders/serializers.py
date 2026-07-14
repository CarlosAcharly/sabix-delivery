from rest_framework import serializers
from django.db import transaction
from decimal import Decimal
from .models import Order, OrderItem, DeliveryTracking
from products.models import Product
from products.serializers import ProductSerializer

# =============================================
# SERIALIZERS DE ORDER ITEMS
# =============================================

class OrderItemSerializer(serializers.ModelSerializer):
    """Serializer para items del pedido"""
    product_name = serializers.CharField(read_only=True)
    product_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = OrderItem
        fields = [
            'id', 'product', 'product_name', 'product_price',
            'quantity', 'total', 'selected_options', 'notes'
        ]
        read_only_fields = ['product_name', 'product_price', 'total']

class OrderItemCreateSerializer(serializers.Serializer):
    """Serializer para crear items del pedido"""
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1, default=1)
    selected_options = serializers.DictField(required=False, default=dict)
    notes = serializers.CharField(required=False, allow_blank=True)

# =============================================
# SERIALIZERS DE ORDENES
# =============================================

class OrderListSerializer(serializers.ModelSerializer):
    """Serializer ligero para listar pedidos"""
    client_name = serializers.SerializerMethodField()
    restaurant_name = serializers.SerializerMethodField()
    delivery_person_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    total_items = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'client', 'client_name', 'restaurant', 'restaurant_name',
            'delivery_person', 'delivery_person_name', 'status', 'status_display',
            'total', 'delivery_fee', 'created_at', 'updated_at',
            'estimated_delivery_time', 'is_paid', 'total_items'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_client_name(self, obj):
        return obj.client.get_full_name() or obj.client.username
    
    def get_restaurant_name(self, obj):
        return obj.restaurant.restaurant_name or obj.restaurant.username
    
    def get_delivery_person_name(self, obj):
        if obj.delivery_person:
            return obj.delivery_person.get_full_name() or obj.delivery_person.username
        return None

class OrderDetailSerializer(serializers.ModelSerializer):
    """Serializer detallado para pedidos"""
    items = OrderItemSerializer(many=True, read_only=True)
    client_name = serializers.SerializerMethodField()
    restaurant_name = serializers.SerializerMethodField()
    delivery_person_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    tracking = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id', 'client', 'client_name', 'restaurant', 'restaurant_name',
            'delivery_person', 'delivery_person_name', 'status', 'status_display',
            'subtotal', 'delivery_fee', 'total',
            'delivery_address', 'delivery_lat', 'delivery_lng', 'delivery_notes',
            'payment_method', 'is_paid', 'payment_id',
            'created_at', 'updated_at', 'confirmed_at', 'preparing_at',
            'ready_at', 'in_delivery_at', 'delivered_at', 'cancelled_at',
            'estimated_delivery_time', 'notes', 'items', 'tracking',
            'client_rating', 'client_comment'
        ]
        read_only_fields = [
            'created_at', 'updated_at', 'confirmed_at', 'preparing_at',
            'ready_at', 'in_delivery_at', 'delivered_at', 'cancelled_at'
        ]
    
    def get_client_name(self, obj):
        return obj.client.get_full_name() or obj.client.username
    
    def get_restaurant_name(self, obj):
        return obj.restaurant.restaurant_name or obj.restaurant.username
    
    def get_delivery_person_name(self, obj):
        if obj.delivery_person:
            return obj.delivery_person.get_full_name() or obj.delivery_person.username
        return None
    
    def get_tracking(self, obj):
        if hasattr(obj, 'tracking'):
            return {
                'current_lat': str(obj.tracking.current_lat),
                'current_lng': str(obj.tracking.current_lng),
                'last_update': obj.tracking.last_update,
                'location_history': obj.tracking.location_history[-10:]  # Últimos 10 registros
            }
        return None

class OrderCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear pedidos"""
    items = serializers.ListField(
        child=OrderItemCreateSerializer(),
        write_only=True,
        min_length=1
    )
    
    class Meta:
        model = Order
        fields = [
            'restaurant', 'delivery_address', 'delivery_lat', 'delivery_lng',
            'delivery_notes', 'payment_method', 'notes', 'items'
        ]
    
    @transaction.atomic
    def create(self, validated_data):
        items_data = validated_data.pop('items')
        client = self.context['request'].user
        
        # Crear el pedido
        order = Order.objects.create(
            client=client,
            restaurant_id=validated_data['restaurant'],
            delivery_address=validated_data['delivery_address'],
            delivery_lat=validated_data.get('delivery_lat'),
            delivery_lng=validated_data.get('delivery_lng'),
            delivery_notes=validated_data.get('delivery_notes', ''),
            payment_method=validated_data.get('payment_method', 'cash'),
            notes=validated_data.get('notes', ''),
            delivery_fee=Decimal('0.00'),  # Se calculará después
            subtotal=Decimal('0.00'),
            total=Decimal('0.00'),
            status='pending'
        )
        
        # Crear los items
        subtotal = Decimal('0.00')
        for item_data in items_data:
            try:
                product = Product.objects.get(
                    id=item_data['product_id'],
                    restaurant_id=order.restaurant_id,
                    is_available=True
                )
            except Product.DoesNotExist:
                raise serializers.ValidationError(
                    f"Producto {item_data['product_id']} no disponible o no pertenece al restaurante"
                )
            
            # Calcular precio final con opciones
            price = product.final_price
            selected_options = item_data.get('selected_options', {})
            
            # Ajustar precio por opciones seleccionadas
            # Aquí puedes agregar lógica para calcular ajustes de precio
            # según las opciones seleccionadas
            
            item = OrderItem.objects.create(
                order=order,
                product=product,
                product_name=product.name,
                product_price=price,
                quantity=item_data['quantity'],
                selected_options=selected_options,
                notes=item_data.get('notes', '')
            )
            
            subtotal += item.total
        
        # Actualizar el pedido con los totales
        order.subtotal = subtotal
        # Calcular delivery_fee según lógica de negocio
        order.delivery_fee = Decimal('0.00')  # Por ahora sin costo de envío
        order.total = subtotal + order.delivery_fee
        order.save()
        
        # Crear tracking
        DeliveryTracking.objects.create(
            order=order,
            current_lat=validated_data.get('delivery_lat', 0),
            current_lng=validated_data.get('delivery_lng', 0)
        )
        
        return order

class OrderUpdateStatusSerializer(serializers.Serializer):
    """Serializer para actualizar estado del pedido"""
    status = serializers.ChoiceField(choices=Order.STATUS_CHOICES)
    
    def validate(self, data):
        status = data.get('status')
        order = self.context.get('order')
        
        if not order:
            raise serializers.ValidationError("Pedido no encontrado")
        
        # Validar transiciones de estado
        valid_transitions = {
            'pending': ['confirmed', 'cancelled', 'rejected'],
            'confirmed': ['preparing', 'cancelled'],
            'preparing': ['ready'],
            'ready': ['in_delivery'],
            'in_delivery': ['delivered'],
        }
        
        current_status = order.status
        allowed_next = valid_transitions.get(current_status, [])
        
        if status not in allowed_next:
            raise serializers.ValidationError(
                f"No se puede cambiar de '{current_status}' a '{status}'"
            )
        
        return data

class OrderAssignDeliverySerializer(serializers.Serializer):
    """Serializer para asignar repartidor a un pedido"""
    delivery_person_id = serializers.IntegerField()
    
    def validate(self, data):
        order = self.context.get('order')
        if order.status != 'ready':
            raise serializers.ValidationError("El pedido debe estar 'Listo para entregar'")
        return data

class DeliveryLocationSerializer(serializers.Serializer):
    """Serializer para actualizar ubicación del repartidor"""
    lat = serializers.DecimalField(max_digits=10, decimal_places=7)
    lng = serializers.DecimalField(max_digits=10, decimal_places=7)
    order_id = serializers.IntegerField()