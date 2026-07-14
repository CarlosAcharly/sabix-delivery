from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Sum, Count
from django.utils import timezone
from datetime import timedelta
from .models import Order, OrderItem, DeliveryTracking
from .serializers import (
    OrderListSerializer, OrderDetailSerializer, OrderCreateSerializer,
    OrderUpdateStatusSerializer, OrderAssignDeliverySerializer,
    DeliveryLocationSerializer
)
from users.permissions import IsClientUser, IsRestaurantUser, IsDeliveryUser, IsAdminUser

# =============================================
# VISTAS PARA CLIENTES
# =============================================

class ClientOrderListCreateView(generics.ListCreateAPIView):
    """
    Vista para clientes: Listar y crear pedidos
    """
    permission_classes = [IsAuthenticated, IsClientUser]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return OrderCreateSerializer
        return OrderListSerializer
    
    def get_queryset(self):
        return Order.objects.filter(client=self.request.user).order_by('-created_at')
    
    def perform_create(self, serializer):
        serializer.save()

class ClientOrderDetailView(generics.RetrieveAPIView):
    """
    Vista para clientes: Ver detalle de pedido
    """
    serializer_class = OrderDetailSerializer
    permission_classes = [IsAuthenticated, IsClientUser]
    
    def get_queryset(self):
        return Order.objects.filter(client=self.request.user)

class ClientOrderCancelView(APIView):
    """
    Vista para clientes: Cancelar pedido
    """
    permission_classes = [IsAuthenticated, IsClientUser]
    
    def post(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id, client=request.user)
        except Order.DoesNotExist:
            return Response(
                {'error': 'Pedido no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if not order.can_cancel():
            return Response(
                {'error': f'No se puede cancelar el pedido. Estado actual: {order.get_status_display()}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        order.update_status('cancelled')
        
        return Response({
            'message': 'Pedido cancelado exitosamente',
            'order': OrderDetailSerializer(order).data
        })

# =============================================
# VISTAS PARA RESTAURANTES
# =============================================

class RestaurantOrderListView(generics.ListAPIView):
    """
    Vista para restaurantes: Listar pedidos del restaurante
    """
    serializer_class = OrderListSerializer
    permission_classes = [IsAuthenticated, IsRestaurantUser]
    
    def get_queryset(self):
        queryset = Order.objects.filter(restaurant=self.request.user)
        
        # Filtros
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset.order_by('-created_at')

class RestaurantOrderDetailView(generics.RetrieveUpdateAPIView):
    """
    Vista para restaurantes: Ver y actualizar pedido
    """
    permission_classes = [IsAuthenticated, IsRestaurantUser]
    
    def get_serializer_class(self):
        if self.request.method == 'GET':
            return OrderDetailSerializer
        return OrderUpdateStatusSerializer
    
    def get_queryset(self):
        return Order.objects.filter(restaurant=self.request.user)
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['order'] = self.get_object()
        return context
    
    def update(self, request, *args, **kwargs):
        order = self.get_object()
        serializer = self.get_serializer(data=request.data, context={'order': order})
        serializer.is_valid(raise_exception=True)
        
        new_status = serializer.validated_data['status']
        order.update_status(new_status)
        
        return Response({
            'message': f'Estado actualizado a {order.get_status_display()}',
            'order': OrderDetailSerializer(order).data
        })

# =============================================
# VISTAS PARA REPARTIDORES
# =============================================

class AvailableOrdersView(generics.ListAPIView):
    """
    Vista para repartidores: Ver pedidos disponibles para entregar
    """
    serializer_class = OrderListSerializer
    permission_classes = [IsAuthenticated, IsDeliveryUser]
    
    def get_queryset(self):
        return Order.objects.filter(
            status='ready',
            delivery_person__isnull=True
        ).order_by('-created_at')

class DeliveryOrderDetailView(generics.RetrieveAPIView):
    """
    Vista para repartidores: Ver detalle de pedido asignado
    """
    serializer_class = OrderDetailSerializer
    permission_classes = [IsAuthenticated, IsDeliveryUser]
    
    def get_queryset(self):
        return Order.objects.filter(delivery_person=self.request.user)

class AcceptDeliveryView(APIView):
    """
    Vista para repartidores: Aceptar pedido para entregar
    """
    permission_classes = [IsAuthenticated, IsDeliveryUser]
    
    def post(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id, status='ready', delivery_person__isnull=True)
        except Order.DoesNotExist:
            return Response(
                {'error': 'Pedido no disponible'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Asignar repartidor
        order.delivery_person = request.user
        order.update_status('in_delivery')
        
        return Response({
            'message': 'Pedido aceptado para entrega',
            'order': OrderDetailSerializer(order).data
        })

class UpdateDeliveryLocationView(APIView):
    """
    Vista para repartidores: Actualizar ubicación en tiempo real
    """
    permission_classes = [IsAuthenticated, IsDeliveryUser]
    
    def post(self, request):
        serializer = DeliveryLocationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        order_id = serializer.validated_data['order_id']
        lat = serializer.validated_data['lat']
        lng = serializer.validated_data['lng']
        
        try:
            order = Order.objects.get(
                id=order_id,
                delivery_person=request.user,
                status='in_delivery'
            )
        except Order.DoesNotExist:
            return Response(
                {'error': 'Pedido no encontrado o no asignado'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Actualizar tracking
        if hasattr(order, 'tracking'):
            order.tracking.update_location(lat, lng)
        else:
            DeliveryTracking.objects.create(
                order=order,
                current_lat=lat,
                current_lng=lng
            )
        
        return Response({
            'message': 'Ubicación actualizada',
            'tracking': {
                'current_lat': str(lat),
                'current_lng': str(lng),
                'last_update': timezone.now()
            }
        })

class MarkOrderDeliveredView(APIView):
    """
    Vista para repartidores: Marcar pedido como entregado
    """
    permission_classes = [IsAuthenticated, IsDeliveryUser]
    
    def post(self, request, order_id):
        try:
            order = Order.objects.get(
                id=order_id,
                delivery_person=request.user,
                status='in_delivery'
            )
        except Order.DoesNotExist:
            return Response(
                {'error': 'Pedido no encontrado o no asignado'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        order.update_status('delivered')
        
        return Response({
            'message': 'Pedido entregado exitosamente',
            'order': OrderDetailSerializer(order).data
        })

# =============================================
# VISTAS PARA ADMINISTRADORES
# =============================================

class AdminOrderListView(generics.ListAPIView):
    """
    Vista para administradores: Listar todos los pedidos
    """
    serializer_class = OrderListSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get_queryset(self):
        queryset = Order.objects.all()
        
        # Filtros
        status = self.request.query_params.get('status')
        restaurant = self.request.query_params.get('restaurant')
        client = self.request.query_params.get('client')
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        
        if status:
            queryset = queryset.filter(status=status)
        if restaurant:
            queryset = queryset.filter(restaurant_id=restaurant)
        if client:
            queryset = queryset.filter(client_id=client)
        if date_from:
            queryset = queryset.filter(created_at__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__lte=date_to)
        
        return queryset.order_by('-created_at')

class AdminOrderDetailView(generics.RetrieveUpdateAPIView):
    """
    Vista para administradores: Ver y actualizar pedido
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get_serializer_class(self):
        if self.request.method == 'GET':
            return OrderDetailSerializer
        return OrderUpdateStatusSerializer
    
    def get_queryset(self):
        return Order.objects.all()
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['order'] = self.get_object()
        return context

class AdminOrderStatsView(APIView):
    """
    Vista para administradores: Estadísticas de pedidos
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get(self, request):
        # Totales por estado
        status_counts = Order.objects.values('status').annotate(
            count=Count('id')
        )
        
        # Pedidos por día (últimos 7 días)
        seven_days_ago = timezone.now() - timedelta(days=7)
        orders_by_day = Order.objects.filter(
            created_at__gte=seven_days_ago
        ).extra(
            {'day': "date(created_at)"}
        ).values('day').annotate(
            count=Count('id'),
            total_revenue=Sum('total')
        ).order_by('day')
        
        # Estadísticas de entregas
        total_deliveries = Order.objects.filter(status='delivered').count()
        total_revenue = Order.objects.filter(
            status__in=['delivered', 'in_delivery', 'ready']
        ).aggregate(total=Sum('total'))['total'] or 0
        
        # Tiempo promedio de entrega (en minutos)
        delivered_orders = Order.objects.filter(
            status='delivered',
            delivered_at__isnull=False,
            created_at__isnull=False
        )
        avg_delivery_time = 0
        if delivered_orders.exists():
            total_minutes = 0
            for order in delivered_orders[:100]:  # Últimos 100 pedidos
                delta = order.delivered_at - order.created_at
                total_minutes += delta.total_seconds() / 60
            avg_delivery_time = total_minutes / delivered_orders.count()
        
        stats = {
            'status_counts': status_counts,
            'orders_by_day': list(orders_by_day),
            'total_orders': Order.objects.count(),
            'total_deliveries': total_deliveries,
            'total_revenue': float(total_revenue),
            'avg_delivery_time': round(avg_delivery_time, 2),
            'pending_orders': Order.objects.filter(status='pending').count(),
            'in_progress': Order.objects.filter(
                status__in=['confirmed', 'preparing', 'ready', 'in_delivery']
            ).count()
        }
        
        return Response(stats)