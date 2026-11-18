from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase

from .models import Order

User = get_user_model()


class ManualDeliveryAssignmentTests(APITestCase):
    def setUp(self):
        self.restaurant = User.objects.create_user(
            username='restaurant',
            password='test-password',
            user_type='restaurant',
        )
        self.client_user = User.objects.create_user(
            username='customer',
            password='test-password',
            user_type='client',
        )
        self.delivery_person = User.objects.create_user(
            username='courier',
            password='test-password',
            user_type='delivery',
        )
        self.other_delivery_person = User.objects.create_user(
            username='other-courier',
            password='test-password',
            user_type='delivery',
        )
        self.order = Order.objects.create(
            client=self.client_user,
            restaurant=self.restaurant,
            status='ready',
            subtotal=Decimal('100.00'),
            delivery_fee=Decimal('10.00'),
            total=Decimal('110.00'),
            delivery_address='Test address',
        )

    def assign_order(self):
        self.client.force_authenticate(self.restaurant)
        return self.client.post(
            reverse('delivery-assign'),
            {
                'order_id': self.order.id,
                'delivery_person_id': self.delivery_person.id,
            },
            format='json',
        )

    def test_manual_assignment_waits_for_driver_acceptance(self):
        response = self.assign_order()

        self.assertEqual(response.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'assigned')
        self.assertEqual(self.order.delivery_person, self.delivery_person)

        self.client.force_authenticate(self.other_delivery_person)
        response = self.client.post(
            reverse('delivery-accept', args=[self.order.id]),
            format='json',
        )
        self.assertEqual(response.status_code, 404)

        self.client.force_authenticate(self.delivery_person)
        response = self.client.post(
            reverse('delivery-accept', args=[self.order.id]),
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'in_delivery')

    def test_assigned_order_is_visible_and_can_be_rejected(self):
        self.assign_order()

        self.client.force_authenticate(self.delivery_person)
        response = self.client.get(reverse('delivery-orders'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual([order['id'] for order in response.data], [self.order.id])

        response = self.client.post(
            reverse('delivery-reject', args=[self.order.id]),
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'ready')
        self.assertIsNone(self.order.delivery_person)

        response = self.client.get(reverse('delivery-available'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual([order['id'] for order in response.data], [self.order.id])
