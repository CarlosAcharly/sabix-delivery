from decimal import Decimal
from .models import PlatformSettings
from orders.models import Order

class PaymentService:
    @staticmethod
    def calculate_order_totals(order: Order):
        """
        Calcula cuánto gana cada quien y actualiza el pedido.
        """
        settings, _ = PlatformSettings.objects.get_or_create(id=1)
        
        # 1. Subtotal de los productos (ej. 35 pesos)
        product_amount = order.subtotal 
        
        # 2. Pago para el repartidor (ej. 20 pesos)
        delivery_amount = settings.delivery_fee_fixed
        
        # 3. Comisión de la plataforma (ej. 10% del subtotal de productos -> 3.50 pesos, 
        # en tu ejemplo eran 5, pero usaremos el 10% del subtotal)
        platform_fee = (product_amount * (settings.platform_fee_percentage / 100))
        
        # 4. Total que pagará el cliente
        total_to_pay = product_amount + delivery_amount + platform_fee
        
        # Actualizar el pedido con el desglose
        order.delivery_fee = delivery_amount
        order.total = total_to_pay
        order.restaurant_earnings = product_amount
        order.delivery_person_earnings = delivery_amount
        order.platform_earnings = platform_fee
        order.save()
        
        return {
            'product_amount': product_amount,
            'delivery_amount': delivery_amount,
            'platform_fee': platform_fee,
            'total': total_to_pay
        }