from django.urls import path
from .views import (
    # Cliente
    ClientOrderListCreateView,
    ClientOrderDetailView,
    ClientOrderCancelView,
    
    # Restaurante
    RestaurantOrderListView,
    RestaurantOrderDetailView,
    
    # Repartidor
    AvailableOrdersView,
    DeliveryOrderDetailView,
    AcceptDeliveryView,
    UpdateDeliveryLocationView,
    MarkOrderDeliveredView,
    
    # Administrador
    AdminOrderListView,
    AdminOrderDetailView,
    AdminOrderStatsView,
)

urlpatterns = [
    # =============================================
    # ENDPOINTS PARA CLIENTES
    # =============================================
    path('client/orders/', ClientOrderListCreateView.as_view(), name='client-orders'),
    path('client/orders/<int:pk>/', ClientOrderDetailView.as_view(), name='client-order-detail'),
    path('client/orders/<int:order_id>/cancel/', ClientOrderCancelView.as_view(), name='client-order-cancel'),
    
    # =============================================
    # ENDPOINTS PARA RESTAURANTES
    # =============================================
    path('restaurant/orders/', RestaurantOrderListView.as_view(), name='restaurant-orders'),
    path('restaurant/orders/<int:pk>/', RestaurantOrderDetailView.as_view(), name='restaurant-order-detail'),
    
    # =============================================
    # ENDPOINTS PARA REPARTIDORES
    # =============================================
    path('delivery/available/', AvailableOrdersView.as_view(), name='delivery-available'),
    path('delivery/orders/<int:pk>/', DeliveryOrderDetailView.as_view(), name='delivery-order-detail'),
    path('delivery/orders/<int:order_id>/accept/', AcceptDeliveryView.as_view(), name='delivery-accept'),
    path('delivery/location/', UpdateDeliveryLocationView.as_view(), name='delivery-location'),
    path('delivery/orders/<int:order_id>/deliver/', MarkOrderDeliveredView.as_view(), name='delivery-deliver'),
    
    # =============================================
    # ENDPOINTS PARA ADMINISTRADORES
    # =============================================
    path('admin/orders/', AdminOrderListView.as_view(), name='admin-orders'),
    path('admin/orders/<int:pk>/', AdminOrderDetailView.as_view(), name='admin-order-detail'),
    path('admin/stats/', AdminOrderStatsView.as_view(), name='admin-order-stats'),
]