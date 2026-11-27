from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase

from .models import DeliveryAssignment, DeliveryTracking, Order

User = get_user_model()


class ClientOrderDetailTests(APITestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(
            username='order-customer',
            password='test-password',
            user_type='client',
        )
        self.other_client = User.objects.create_user(
            username='other-order-customer',
            password='test-password',
            user_type='client',
        )
        self.restaurant = User.objects.create_user(
            username='order-restaurant',
            password='test-password',
            user_type='restaurant',
        )
        self.order = Order.objects.create(
            client=self.client_user,
            restaurant=self.restaurant,
            status='delivered',
            subtotal=Decimal('66.00'),
            delivery_fee=Decimal('20.00'),
            total=Decimal('86.00'),
            delivery_address='Test address',
        )

    def test_client_can_retrieve_own_order_detail(self):
        self.client.force_authenticate(self.client_user)

        response = self.client.get(
            reverse('client-order-detail', args=[self.order.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['id'], self.order.id)

    def test_client_cannot_retrieve_another_clients_order(self):
        self.client.force_authenticate(self.other_client)

        response = self.client.get(
            reverse('client-order-detail', args=[self.order.id])
        )

        self.assertEqual(response.status_code, 404)


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


class DeliveryLocationUpdateTests(APITestCase):
    def setUp(self):
        self.delivery_person = User.objects.create_user(
            username='tracking-courier',
            password='test-password',
            user_type='delivery',
        )
        self.client_user = User.objects.create_user(
            username='tracking-customer',
            password='test-password',
            user_type='client',
        )
        self.restaurant = User.objects.create_user(
            username='tracking-restaurant',
            password='test-password',
            user_type='restaurant',
        )
        self.order = Order.objects.create(
            client=self.client_user,
            restaurant=self.restaurant,
            delivery_person=self.delivery_person,
            status='in_delivery',
            subtotal=Decimal('100.00'),
            delivery_fee=Decimal('10.00'),
            total=Decimal('110.00'),
            delivery_address='Test address',
        )
        self.tracking = DeliveryTracking.objects.create(
            order=self.order,
            current_lat=Decimal('19.4000000'),
            current_lng=Decimal('-99.1000000'),
        )
        self.client.force_authenticate(self.delivery_person)

    def test_location_update_saves_tracking_and_dispatch_coordinates(self):
        response = self.client.post(
            reverse('delivery-location'),
            {
                'order_id': self.order.id,
                'lat': '19.4326000',
                'lng': '-99.1332000',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.delivery_person.refresh_from_db()
        self.tracking.refresh_from_db()
        self.assertEqual(
            self.delivery_person.current_location_lat,
            Decimal('19.4326000'),
        )
        self.assertEqual(
            self.delivery_person.current_location_lng,
            Decimal('-99.1332000'),
        )
        self.assertEqual(self.tracking.current_lat, Decimal('19.4326000'))
        self.assertEqual(self.tracking.current_lng, Decimal('-99.1332000'))

    def test_location_update_rejects_out_of_range_coordinates(self):
        response = self.client.post(
            reverse('delivery-location'),
            {
                'order_id': self.order.id,
                'lat': '91',
                'lng': '-99.1332000',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 400)

    def test_location_can_be_updated_before_order_assignment(self):
        response = self.client.post(
            reverse('delivery-location'),
            {'lat': '19.4326000', 'lng': '-99.1332000'},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.delivery_person.refresh_from_db()
        self.tracking.refresh_from_db()
        self.assertEqual(
            self.delivery_person.current_location_lat,
            Decimal('19.4326000'),
        )
        self.assertEqual(
            self.delivery_person.current_location_lng,
            Decimal('-99.1332000'),
        )
        self.assertEqual(self.tracking.current_lat, Decimal('19.4000000'))
        self.assertIsNone(response.data['tracking'])


class AutomaticDeliveryAssignmentTests(APITestCase):
    def setUp(self):
        self.restaurant = User.objects.create_user(
            username='auto-restaurant',
            password='test-password',
            user_type='restaurant',
            current_location_lat=Decimal('19.4326000'),
            current_location_lng=Decimal('-99.1332000'),
        )
        self.client_user = User.objects.create_user(
            username='auto-customer',
            password='test-password',
            user_type='client',
        )
        self.nearest_delivery_person = User.objects.create_user(
            username='nearest-courier',
            password='test-password',
            user_type='delivery',
            current_location_lat=Decimal('19.4330000'),
            current_location_lng=Decimal('-99.1332000'),
        )
        self.next_delivery_person = User.objects.create_user(
            username='next-courier',
            password='test-password',
            user_type='delivery',
            current_location_lat=Decimal('19.4350000'),
            current_location_lng=Decimal('-99.1332000'),
        )
        self.order = Order.objects.create(
            client=self.client_user,
            restaurant=self.restaurant,
            status='preparing',
            subtotal=Decimal('100.00'),
            delivery_fee=Decimal('10.00'),
            total=Decimal('110.00'),
            delivery_address='Test address',
        )

    def mark_order_ready(self):
        self.client.force_authenticate(self.restaurant)
        return self.client.patch(
            reverse('restaurant-order-detail', args=[self.order.id]),
            {'status': 'ready'},
            format='json',
        )

    def test_find_nearest_uses_saved_restaurant_coordinates(self):
        self.order.status = 'ready'
        self.order.save(update_fields=['status'])
        self.client.force_authenticate(self.restaurant)

        response = self.client.post(
            reverse('delivery-find-nearest'),
            {'order_id': self.order.id},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data['available_delivery_people'][0]['id'],
            self.nearest_delivery_person.id,
        )

    def test_auto_assign_without_available_drivers_returns_conflict(self):
        self.order.status = 'ready'
        self.order.save(update_fields=['status'])
        User.objects.filter(
            id__in=[self.nearest_delivery_person.id, self.next_delivery_person.id]
        ).update(is_available=False)
        self.client.force_authenticate(self.restaurant)

        response = self.client.post(
            reverse('delivery-auto-assign'),
            {'order_id': self.order.id},
            format='json',
        )

        self.assertEqual(response.status_code, 409)

    def test_ready_order_is_offered_to_nearest_active_driver(self):
        response = self.mark_order_ready()

        self.assertEqual(response.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'assigned')
        self.assertEqual(self.order.delivery_person, self.nearest_delivery_person)
        assignment = DeliveryAssignment.objects.get(order=self.order)
        self.assertEqual(assignment.status, 'pending')
        self.assertEqual(response.data['order']['status'], 'assigned')

    def test_auto_assign_retry_returns_existing_pending_assignment(self):
        self.mark_order_ready()
        assignment = DeliveryAssignment.objects.get(order=self.order)

        self.client.force_authenticate(self.restaurant)
        response = self.client.post(
            reverse('delivery-auto-assign'),
            {'order_id': self.order.id},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['assignment']['id'], assignment.id)
        self.assertEqual(DeliveryAssignment.objects.filter(order=self.order).count(), 1)

    def test_driver_acceptance_updates_the_assignment_and_order(self):
        self.mark_order_ready()

        self.client.force_authenticate(self.nearest_delivery_person)
        response = self.client.post(
            reverse('delivery-accept', args=[self.order.id]),
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.order.refresh_from_db()
        assignment = DeliveryAssignment.objects.get(
            order=self.order,
            delivery_person=self.nearest_delivery_person,
        )
        self.assertEqual(self.order.status, 'in_delivery')
        self.assertEqual(assignment.status, 'accepted')
        self.assertIsNotNone(assignment.responded_at)

    def test_inactive_nearest_driver_is_skipped(self):
        self.nearest_delivery_person.is_active = False
        self.nearest_delivery_person.save(update_fields=['is_active'])

        self.mark_order_ready()

        self.order.refresh_from_db()
        self.assertEqual(self.order.delivery_person, self.next_delivery_person)

    def test_rejection_offers_order_to_next_nearest_driver(self):
        self.mark_order_ready()

        self.client.force_authenticate(self.nearest_delivery_person)
        response = self.client.post(
            reverse('delivery-reject', args=[self.order.id]),
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'assigned')
        self.assertEqual(self.order.delivery_person, self.next_delivery_person)
        assignments = list(
            DeliveryAssignment.objects.filter(order=self.order).order_by('assigned_at')
        )
        self.assertEqual(len(assignments), 2)
        self.assertEqual(assignments[0].status, 'rejected')
        self.assertEqual(assignments[1].delivery_person, self.next_delivery_person)
        self.assertEqual(assignments[1].status, 'pending')

    def test_no_driver_remaining_returns_order_to_available_list(self):
        self.mark_order_ready()

        self.client.force_authenticate(self.nearest_delivery_person)
        self.client.post(
            reverse('delivery-reject', args=[self.order.id]),
            format='json',
        )
        self.client.force_authenticate(self.next_delivery_person)
        response = self.client.post(
            reverse('delivery-reject', args=[self.order.id]),
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'ready')
        self.assertIsNone(self.order.delivery_person)


class AdminDeliveryAssignmentListTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin',
            password='test-password',
            user_type='admin',
        )
        self.restaurant = User.objects.create_user(
            username='admin-list-restaurant',
            password='test-password',
            user_type='restaurant',
        )
        self.client_user = User.objects.create_user(
            username='admin-list-customer',
            password='test-password',
            user_type='client',
        )
        self.delivery_person = User.objects.create_user(
            username='admin-list-courier',
            password='test-password',
            user_type='delivery',
        )
        self.order = Order.objects.create(
            client=self.client_user,
            restaurant=self.restaurant,
            delivery_person=self.delivery_person,
            status='assigned',
            subtotal=Decimal('100.00'),
            delivery_fee=Decimal('10.00'),
            total=Decimal('110.00'),
            delivery_address='Test address',
        )
        DeliveryAssignment.objects.create(
            order=self.order,
            delivery_person=self.delivery_person,
            distance_km=Decimal('1.25'),
            estimated_time=3,
        )

    def test_admin_can_list_paginated_assignments(self):
        self.client.force_authenticate(self.admin)

        response = self.client.get(
            reverse('admin-assignments'),
            {'page': 1, 'page_size': 10},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['order_id'], self.order.id)

    def test_non_admin_cannot_list_assignments(self):
        self.client.force_authenticate(self.restaurant)

        response = self.client.get(reverse('admin-assignments'))

        self.assertEqual(response.status_code, 403)
