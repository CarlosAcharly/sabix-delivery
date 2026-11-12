from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from .models import Payment, PlatformSettings
from .services import PaymentService
from .serializers import PaymentSerializer, PlatformSettingsSerializer
from orders.models import Order

class ProcessPaymentView(APIView):
    """
    Simula el procesamiento de pago de un pedido
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, order_id):
        order = get_object_or_404(Order, id=order_id, client=request.user)
        
        if hasattr(order, 'payment') and order.payment.status == 'completed':
            return Response({'error': 'El pedido ya está pagado'}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Calcular montos (esto actualiza el order.total)
        totals = PaymentService.calculate_order_totals(order)
        
        # 2. Simular creación de pago en la pasarela (aquí iría Stripe/MercadoPago)
        # Simulamos que fue un éxito
        payment, created = Payment.objects.update_or_create(
            order=order,
            defaults={
                'product_amount': totals['product_amount'],
                'delivery_amount': totals['delivery_amount'],
                'platform_fee_amount': totals['platform_fee'],
                'total_amount': totals['total'],
                'status': 'completed',
                'transaction_id': f"sim_txn_{order.id}"
            }
        )
        
        order.is_paid = True
        order.save()
        
        return Response({
            'message': 'Pago procesado exitosamente (Simulación)',
            'payment': PaymentSerializer(payment).data
        }, status=status.HTTP_200_OK)


class PlatformSettingsView(APIView):
    """
    Permite al Admin ver y editar las comisiones
    """
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        settings, _ = PlatformSettings.objects.get_or_create(id=1)
        return Response(PlatformSettingsSerializer(settings).data)

    def put(self, request):
        settings, _ = PlatformSettings.objects.get_or_create(id=1)
        serializer = PlatformSettingsSerializer(settings, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)