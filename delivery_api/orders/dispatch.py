from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import transaction
from geopy.distance import geodesic

from .models import DeliveryAssignment, Order

User = get_user_model()


@transaction.atomic
def assign_nearest_delivery_person(
    order: Order,
    restaurant_lat=None,
    restaurant_lng=None,
    allow_assigned=False,
):
    """Assign the closest eligible delivery person and keep the offer pending."""
    order = Order.objects.select_for_update().get(pk=order.pk)
    allowed_statuses = ['ready', 'assigned'] if allow_assigned else ['ready']
    if order.status not in allowed_statuses or order.delivery_person_id is not None:
        return None

    restaurant = order.restaurant
    if restaurant_lat is None:
        restaurant_lat = restaurant.current_location_lat
    if restaurant_lng is None:
        restaurant_lng = restaurant.current_location_lng
    if restaurant_lat is None or restaurant_lng is None:
        return None

    try:
        restaurant_location = (float(restaurant_lat), float(restaurant_lng))
        restaurant_lat_value = Decimal(str(restaurant_lat))
        restaurant_lng_value = Decimal(str(restaurant_lng))
        if not -90 <= restaurant_location[0] <= 90 or not -180 <= restaurant_location[1] <= 180:
            return None
    except (TypeError, ValueError):
        return None

    previous_delivery_ids = order.assignments.values_list('delivery_person_id', flat=True)
    available_delivery_people = User.objects.filter(
        user_type='delivery',
        is_active=True,
        is_available=True,
        current_location_lat__isnull=False,
        current_location_lng__isnull=False,
    ).exclude(
        id__in=previous_delivery_ids,
    ).exclude(
        orders_as_delivery__status__in=['assigned', 'in_delivery'],
    ).distinct()

    nearest_delivery_person = None
    nearest_distance = None
    for delivery_person in available_delivery_people:
        delivery_person = User.objects.select_for_update().get(pk=delivery_person.pk)
        if not delivery_person.is_active or not delivery_person.is_available:
            continue
        if Order.objects.filter(
            delivery_person=delivery_person,
            status__in=['assigned', 'in_delivery'],
        ).exists():
            continue

        try:
            distance = geodesic(
                restaurant_location,
                (
                    float(delivery_person.current_location_lat),
                    float(delivery_person.current_location_lng),
                ),
            ).kilometers
        except (ValueError, TypeError):
            continue

        if nearest_distance is None or distance < nearest_distance:
            nearest_delivery_person = delivery_person
            nearest_distance = distance

    if nearest_delivery_person is None:
        return None

    order.delivery_person = nearest_delivery_person
    order.status = 'assigned'
    order.save(update_fields=['delivery_person', 'status', 'updated_at'])

    return DeliveryAssignment.objects.create(
        order=order,
        delivery_person=nearest_delivery_person,
        distance_km=Decimal(str(nearest_distance)).quantize(Decimal('0.01')),
        estimated_time=round(nearest_distance * 2),
        restaurant_lat=restaurant_lat_value,
        restaurant_lng=restaurant_lng_value,
    )
